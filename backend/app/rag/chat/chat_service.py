from http import HTTPStatus  # HTTP状态码
import logging  # 日志记录

from typing import Generator, List, Optional
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text, delete
from sqlmodel import Session, select, func

from app.api.routes.models import (
    RequiredConfigStatus,
    OptionalConfigStatus,
    NeedMigrationStatus,
)
from app.models import (
    User,
    ChatVisibility,
    Chat as DBChat,
    ChatMessage as DBChatMessage,
    KnowledgeBase as DBKnowledgeBase,
    RerankerModel as DBRerankerModel,
    ChatEngine,
)
from app.models.recommend_question import RecommendQuestion
from app.rag.chat.retrieve.retrieve_flow import RetrieveFlow, SourceDocument
from app.rag.chat.stream_protocol import ChatEvent
from app.rag.retrievers.knowledge_graph.schema import (
    KnowledgeGraphRetrievalResult,
    StoredKnowledgeGraph,
    RetrievedSubGraph,
)
from app.rag.knowledge_base.index_store import get_kb_tidb_graph_store
from app.repositories import knowledge_base_repo

from app.rag.chat.config import (
    ChatEngineConfig,
)
from app.rag.types import (
    ChatEventType,
    ChatMessageSate,
)
from app.repositories import chat_engine_repo
from app.repositories.embedding_model import embedding_model_repo
from app.repositories.llm import llm_repo
from app.site_settings import SiteSetting
from llama_index.core.prompts.rich import RichPromptTemplate

logger = logging.getLogger(__name__)


class ChatResult(BaseModel):
    """聊天结果数据模型"""

    chat_id: UUID  # 聊天会话ID
    message_id: int  # 消息ID
    content: str  # 消息内容
    trace: Optional[str] = None  # 追踪链接
    sources: Optional[List[SourceDocument]] = []  # 来源文档


def get_final_chat_result(
    generator: Generator[ChatEvent | str, None, None],
) -> ChatResult:
    """
    从聊天事件流中提取最终结果
    参数：
        generator: 聊天事件生成器，包含文本片段、来源文档等事件
    返回：
        ChatResult: 结构化的最终聊天结果
    处理流程：
        1. 遍历事件流
        2. 根据事件类型收集不同数据
        3. 遇到错误事件时抛出异常
        4. 返回整合后的结果对象
    """
    trace, sources, content = None, [], ""
    chat_id, message_id = None, None

    # 遍历事件流
    for m in generator:
        if not isinstance(m, ChatEvent):
            continue

        # 处理不同事件类型
        if m.event_type == ChatEventType.MESSAGE_ANNOTATIONS_PART:
            if m.payload.state == ChatMessageSate.SOURCE_NODES:
                sources = m.payload.context  # 收集来源文档
        elif m.event_type == ChatEventType.TEXT_PART:
            content += m.payload  # 拼接消息内容
        elif m.event_type == ChatEventType.DATA_PART:
            chat_id = m.payload.chat.id  # 获取聊天ID
            message_id = m.payload.assistant_message.id  # 获取消息ID
            trace = m.payload.assistant_message.trace_url  # 获取追踪链接
        elif m.event_type == ChatEventType.ERROR_PART:
            raise HTTPException(  # 抛出异常
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=m.payload,
            )

    return ChatResult(
        chat_id=chat_id,
        message_id=message_id,
        trace=trace,
        sources=sources,
        content=content,
    )


def user_can_view_chat(chat: DBChat, user: Optional[User]) -> bool:
    """
    检查用户是否具有查看聊天记录的权限
    权限规则：
        - 匿名聊天（无用户ID）或公开可见聊天：所有用户可查看
        - 非公开聊天：仅聊天所有者或超级管理员可查看
    参数：
        chat: 聊天记录对象
        user: 当前用户对象（可为None表示未登录用户）
    """
    # 匿名或公开聊天：所有人可见
    # 非匿名聊天：仅所有者或超级用户可见
    return (
        not chat.user_id
        or chat.visibility == ChatVisibility.PUBLIC
        or (user and (user.is_superuser or chat.user_id == user.id))
    )


def user_can_edit_chat(chat: DBChat, user: Optional[User]) -> bool:
    """
    检查用户是否具有编辑聊天记录的权限
    权限规则：
        - 超级管理员可编辑所有聊天
        - 普通用户只能编辑自己创建的聊天
    参数：
        chat: 聊天记录对象
        user: 当前用户对象
    """
    return user and (user.is_superuser or chat.user_id == user.id)


def get_graph_data_from_chat_message(
    db_session: Session,
    chat_message: DBChatMessage,
    engine_config: ChatEngineConfig,
) -> Optional[KnowledgeGraphRetrievalResult]:
    """
    从聊天消息中解析知识图谱数据
    功能：
        1. 处理旧版本数据格式兼容
        2. 解析存储的知识图谱结构
        3. 根据知识库ID获取实际图谱数据
        4. 支持多知识库关联图谱的合并
    特殊处理：
        - 对动态生成的knowledge_base_ids进行关联查询
        - 使用写锁保证数据一致性
    """
    if not chat_message.graph_data:
        return None

    graph_data = chat_message.graph_data

    # 处理旧版本数据格式
    if "version" not in graph_data:
        kb = engine_config.get_knowledge_bases(db_session)[0]
        graph_store = get_kb_tidb_graph_store(db_session, kb)
        return graph_store.get_subgraph_by_relationship_ids(graph_data["relationships"])

    # 验证并处理存储的知识图谱
    stored_kg = StoredKnowledgeGraph.model_validate(graph_data)

    # 处理单知识库情况
    if stored_kg.knowledge_base_id:
        kb = knowledge_base_repo.must_get(db_session, stored_kg.knowledge_base_id)
        graph_store = get_kb_tidb_graph_store(db_session, kb)
        return graph_store.get_subgraph_by_relationship_ids(
            ids=stored_kg.relationships, query=stored_kg.query
        )

    # 处理多知识库情况
    elif stored_kg.knowledge_base_ids:
        kg_store_map = {}
        knowledge_base_set = set()
        relationship_set = set()
        entity_set = set()
        subgraphs = []

        # 遍历所有相关知识库
        for kb_id in stored_kg.knowledge_base_ids:
            kb = knowledge_base_repo.must_get(db_session, kb_id)
            knowledge_base_set.add(kb.to_descriptor())
            kg_store_map[kb_id] = get_kb_tidb_graph_store(db_session, kb)

        # 处理每个子图
        for stored_subgraph in stored_kg.subgraphs:
            kg_store = kg_store_map.get(stored_subgraph.knowledge_base_id)
            if kg_store:
                subgraph = kg_store.get_subgraph_by_relationship_ids(
                    stored_subgraph.relationships, stored_kg.query
                )
            relationship_set.update(subgraph.relationships)
            entity_set.update(subgraph.entities)
            subgraphs.append(RetrievedSubGraph(**subgraph.model_dump()))

        return KnowledgeGraphRetrievalResult(
            query=stored_kg.query,
            knowledge_bases=list(knowledge_base_set),
            relationships=list(relationship_set),
            entities=list(entity_set),
            subgraphs=subgraphs,
        )


def get_chat_message_subgraph(
    db_session: Session, chat_message: DBChatMessage
) -> KnowledgeGraphRetrievalResult:
    chat_engine: ChatEngine = chat_message.chat.engine
    engine_name = chat_engine.name
    engine_config = ChatEngineConfig.load_from_db(db_session, chat_engine.name)

    # Try to get subgraph from `chat_message.graph_data`.
    try:
        knowledge_graph = get_graph_data_from_chat_message(
            db_session, chat_message, engine_config
        )
        if knowledge_graph is not None:
            return knowledge_graph
    except Exception as e:
        logger.error(
            f"Failed to get subgraph from chat_message.graph_data: {e}", exc_info=True
        )

    # Try to get subgraph based on the chat message content.
    # Notice: it use current chat engine config, not the snapshot stored in chat_message.
    retriever = RetrieveFlow(
        db_session=db_session,
        engine_name=engine_name,
        engine_config=engine_config,
    )
    knowledge_graph, _ = retriever.search_knowledge_graph(chat_message.content)
    return knowledge_graph


def check_rag_required_config(session: Session) -> RequiredConfigStatus:
    """
    检查RAG系统必需的核心配置状态
    检查项：
        - 是否配置默认LLM
        - 是否配置默认嵌入模型
        - 是否配置默认聊天引擎
        - 是否存在至少一个知识库
    返回值：
        RequiredConfigStatus: 各配置项的状态集合
    """
    has_default_llm = llm_repo.has_default(session)
    has_default_embedding_model = embedding_model_repo.has_default(session)
    has_default_chat_engine = chat_engine_repo.has_default(session)
    has_knowledge_base = session.scalar(select(func.count(DBKnowledgeBase.id))) > 0

    return RequiredConfigStatus(
        default_llm=has_default_llm,
        default_embedding_model=has_default_embedding_model,
        default_chat_engine=has_default_chat_engine,
        knowledge_base=has_knowledge_base,
    )


def check_rag_optional_config(session: Session) -> OptionalConfigStatus:
    """
    检查RAG系统的可选增强配置
    检查项：
        - Langfuse监控是否配置
        - 是否配置重排模型
    用途：
        用于展示系统增强功能可用状态
    """
    langfuse = bool(
        SiteSetting.langfuse_host
        and SiteSetting.langfuse_secret_key
        and SiteSetting.langfuse_public_key
    )
    default_reranker = session.scalar(select(func.count(DBRerankerModel.id))) > 0
    return OptionalConfigStatus(
        langfuse=langfuse,
        default_reranker=default_reranker,
    )


def check_rag_config_need_migration(session: Session) -> NeedMigrationStatus:
    """
    检查需要迁移的配置项
    当前检测：
        - 使用旧版知识库配置的聊天引擎
    实现方式：
        通过SQL查询检测engine_options字段格式
    用途：
        用于系统升级时的配置迁移提示
    """
    chat_engines_without_kb_configured = session.exec(
        select(ChatEngine.id)
        .where(ChatEngine.deleted_at == None)
        .where(
            text(
                "JSON_EXTRACT(engine_options, '$.knowledge_base.linked_knowledge_bases') IS NULL AND "
                "JSON_EXTRACT(engine_options, '$.knowledge_base.linked_knowledge_base') IS NULL"
            )
        )
    )

    return NeedMigrationStatus(
        chat_engines_without_kb_configured=chat_engines_without_kb_configured,
    )


def remove_chat_message_recommend_questions(
    db_session: Session,
    chat_message_id: int,
) -> None:
    """
    删除指定聊天消息的推荐问题
    操作：
        执行数据库删除操作
    使用场景：
        - 消息内容更新时清除旧推荐
        - 用户手动刷新推荐问题
    """
    delete_stmt = delete(RecommendQuestion).where(
        RecommendQuestion.chat_message_id == chat_message_id
    )
    db_session.exec(delete_stmt)
    db_session.commit()


def get_chat_message_recommend_questions(
    db_session: Session,
    chat_message: DBChatMessage,
    engine_name: str = "default",
) -> List[str]:
    """
    生成/获取聊天消息的推荐问题列表
    处理流程：
        1. 检查数据库缓存
        2. 无缓存时调用LLM生成
        3. 验证生成结果格式
        4. 格式异常时重新生成
        5. 存储结果到数据库
    质量保证：
        - 使用with_for_update防止并发写入
        - 过滤空行和格式错误内容
        - 限制单个问题最大长度（500字符）
    """
    # 初始化配置和模型
    chat_engine_config = ChatEngineConfig.load_from_db(db_session, engine_name)
    llm = chat_engine_config.get_llama_llm(db_session)

    # 检查数据库缓存
    questions = db_session.exec(
        select(RecommendQuestion.questions)
        .where(RecommendQuestion.chat_message_id == chat_message.id)
        .with_for_update()  # 使用写锁防止并发问题
    ).first()

    if questions:
        return questions

    # 生成推荐问题
    prompt_template = RichPromptTemplate(
        chat_engine_config.llm.further_questions_prompt
    )
    recommend_questions = llm.predict(
        prompt_template,
        chat_message_content=chat_message.content,
    )

    # 处理生成结果
    recommend_question_list = [
        q.strip() for q in recommend_questions.splitlines() if q.strip()
    ]

    # 校验生成质量
    if (
        any(c in recommend_questions for c in ("##", "**"))
        or max(len(q) for q in recommend_question_list) > 500
    ):
        # 重新生成格式错误的问题
        recommend_questions = llm.predict(
            prompt_template,
            chat_message_content=f"请生成问题列表。之前生成有误，请重试。\n{chat_message.content}",
        )

    # 存储到数据库
    db_session.add(
        RecommendQuestion(
            chat_message_id=chat_message.id,
            questions=recommend_question_list,
        )
    )
    db_session.commit()

    return recommend_question_list
