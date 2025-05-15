from http import HTTPStatus  # HTTP状态码
import logging  # 日志记录
import json  # 用于JSON处理

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
from app.rag.chat.stream_protocol import ChatEvent, ChatStreamMessagePayload
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
from app.repositories import chat_repo
from app.repositories.embedding_model import embedding_model_repo
from app.repositories.llm import llm_repo
from app.site_settings import SiteSetting
from llama_index.core.prompts.rich import RichPromptTemplate
from llama_index.core.base.llms.types import ChatMessage

# 导入AutoFlowAgent替代原有的agent
from app.autoflow.autoflow_agent import AutoFlowAgent

import starlette.concurrency

from app.utils.async_utils import AsyncToSyncAdapter

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
    从生成器中获取最终的聊天结果
    
    从事件生成器中提取最终的聊天结果，包括内容、来源信息等。
    
    参数:
        generator: 聊天事件生成器
        
    返回:
        ChatResult: 最终的聊天结果
    """
    content = ""
    sources = []
    trace = ""
    chat_id = None
    message_id = None

    # 提取事件中的信息
    for event in generator:
        if isinstance(event, str):
            # 直接处理字符串事件
            content += event
            continue

        # 处理不同类型的事件
        try:
            if event.event_type == ChatEventType.TEXT_PART:
                # 提取文本内容
                if isinstance(event.payload, ChatStreamMessagePayload):
                    content += event.payload.message
                # 处理JSON字符串
                elif isinstance(event.payload, str):
                    try:
                        payload = json.loads(event.payload)
                        if "message" in payload:
                            content += payload["message"]
                        elif "chat_id" in payload and "message_id" in payload:
                            # 这里处理原本ID_PART的情况
                            chat_id = payload["chat_id"]
                            message_id = payload["message_id"]
                        else:
                            content += event.payload
                    except:
                        content += str(event.payload)
                else:
                    # 其他情况
                    content += str(event.payload)
            elif event.event_type == ChatEventType.DATA_PART:
                # 提取数据部分
                try:
                    payload = json.loads(event.payload)
                    if "sources" in payload:
                        for source in payload["sources"]:
                            doc = SourceDocument(
                                page_content=source.get("text", ""),
                                metadata=source.get("metadata", {}),
                            )
                            sources.append(doc)
                    elif "chat" in payload and "assistant_message" in payload:
                        # 处理原来包含ID和trace信息的数据部分
                        chat_id = payload["chat"].get("id")
                        message_id = payload["assistant_message"].get("id")
                        trace = payload["assistant_message"].get("trace_url")
                except Exception as e:
                    logger.warning(f"解析DATA_PART事件失败: {str(e)}")
            elif event.event_type == ChatEventType.MESSAGE_ANNOTATIONS_PART:
                # 提取注释部分，可能包含源文档
                if hasattr(event.payload, "state") and event.payload.state == ChatMessageSate.SOURCE_NODES:
                    if hasattr(event.payload, "context"):
                        sources = event.payload.context
            elif event.event_type == ChatEventType.ERROR_PART:
                # 处理错误
                logger.error(f"收到错误事件: {event.payload}")
                raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail=str(event.payload),
            )
        except Exception as e:
            logger.warning(f"处理事件失败: {str(e)}")
    
    # 确保chat_id和message_id已设置
    if not chat_id or not message_id:
        # 如果ID信息不存在，使用临时值
        logger.warning("聊天结果中缺少必要的ID信息，使用临时值")
        if not chat_id:
            import uuid
            chat_id = uuid.uuid4()
        if not message_id:
            message_id = 0
    
    # 返回最终结果
    return ChatResult(
        chat_id=chat_id,
        message_id=message_id,
        content=content,
        trace=trace,
        sources=sources,
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

# Agent模式相关函数

def create_agent_chat_flow(
    db_session: Session,
    user: Optional[User],
    browser_id: str,
    origin: str,
    chat_messages: List[ChatMessage],
    engine_name: str = "default",
    chat_id: Optional[UUID] = None,
) -> AutoFlowAgent:
    """
    创建Agent聊天流
    
    参数:
        db_session: 数据库会话
        user: 用户对象
        browser_id: 浏览器ID
        origin: 请求来源
        chat_messages: 聊天消息列表
        engine_name: 引擎名称，默认为"default"
        chat_id: 聊天ID，可选
        
    返回:
        AutoFlowAgent: 初始化好的Agent对象
    """
    logger.info(f"【创建Agent】开始创建Agent聊天流, engine_name={engine_name}, chat_id={chat_id}")
    
    # 加载引擎配置
    engine_config = ChatEngineConfig.load_from_db(db_session, engine_name)
    logger.info(f"【创建Agent】引擎配置加载完成, 引擎名称={engine_config.get_db_chat_engine().name}")
    
    # 解析聊天消息，获取用户问题和聊天历史
    user_question = chat_messages[-1].content
    chat_history = [{"role": m.role, "content": m.content} for m in chat_messages[:-1]]
    logger.info(f"【创建Agent】用户问题: {user_question[:50]}..., 聊天历史长度: {len(chat_history)}")
    
    # 创建AutoFlowAgent实例
    logger.info(f"【创建Agent】创建AutoFlowAgent实例, agent_enabled={engine_config.agent.enabled}")
    agent = AutoFlowAgent(db_session=db_session, engine_config=engine_config)
    
    # 如果存在chat_id，获取已有的聊天对象
    db_chat_obj = None
    if chat_id:
        logger.info(f"【创建Agent】尝试获取已有的聊天对象: chat_id={chat_id}")
        db_chat_obj = chat_repo.get(db_session, chat_id)
        if not db_chat_obj:
            # 如果找不到对应ID的聊天，抛出异常
            logger.error(f"【创建Agent错误】找不到对应ID的聊天: {chat_id}")
            from app.exceptions import ChatNotFound
            raise ChatNotFound(chat_id)
        logger.info(f"【创建Agent】已获取聊天对象: {db_chat_obj.id}, title={db_chat_obj.title}")
    else:
        # 创建新的聊天对象
        logger.info("【创建Agent】创建新的聊天对象")
        from app.models import Chat as DBChat, ChatVisibility
        db_chat_obj = chat_repo.create(
            db_session,
            DBChat(
                title=user_question[:100],  # 使用问题前100个字符作为标题
                engine_id=engine_config.get_db_chat_engine().id,  # 设置引擎ID
                engine_options=engine_config.screenshot(),  # 保存引擎配置快照
                user_id=user.id if user else None,  # 设置用户ID
                browser_id=browser_id,  # 设置浏览器ID
                origin=origin,  # 设置请求来源
                visibility=(
                    ChatVisibility.PUBLIC  # 如果是匿名用户，设为公开
                    if not user
                    else ChatVisibility.PRIVATE  # 如果是登录用户，设为私有
                ),
            ),
        )
        logger.info(f"【创建Agent】聊天对象创建成功: {db_chat_obj.id}, title={db_chat_obj.title}")
    
    # 加载知识库索引
    logger.info("【创建Agent】开始加载知识库索引")
    knowledge_bases = engine_config.get_knowledge_bases(db_session)
    if knowledge_bases:
        logger.info(f"【创建Agent】找到{len(knowledge_bases)}个知识库")
        try:
            from app.rag.knowledge_base.index_store import get_kb_tidb_vector_store
            vector_index = get_kb_tidb_vector_store(db_session, knowledge_bases[0])
            kg_index = None  # 暂时设为None，简化实现
            logger.info(f"【创建Agent】成功加载知识库索引: vector_index={vector_index is not None}, kg_index={kg_index is not None}")
            agent.set_indices(vector_index, kg_index)
        except Exception as e:
            logger.error(f"【创建Agent错误】加载知识库索引失败: {str(e)}", exc_info=True)
    else:
        logger.warning("【创建Agent】没有找到知识库，不加载索引")
    
    # 保存db_chat_obj到agent实例
    agent.db_chat_obj = db_chat_obj
    logger.info("【创建Agent】Agent创建完成")
    
    return agent

def is_agent_mode_enabled(engine_config: ChatEngineConfig) -> bool:
    """
    检查是否启用了Agent模式
    
    参数:
        engine_config: 聊天引擎配置
        
    返回:
        bool: 是否启用Agent模式
    """
    # 从配置中读取是否启用Agent模式
    enabled = engine_config.agent.enabled
    logger.info(f"【Agent模式】检查是否启用Agent模式: agent.enabled = {enabled}")
    # 打印完整的agent配置，帮助排查问题
    logger.info(f"【Agent模式】Agent完整配置: {engine_config.agent.model_dump()}")
    return enabled

def chat(
    db_session: Session,
    user: Optional[User],
    browser_id: str,
    origin: str,
    chat_messages: List[ChatMessage],
    engine_name: str = "default",
    chat_id: Optional[UUID] = None,
) -> Generator[ChatEvent | str, None, None]:
    """
    处理聊天请求，根据配置决定使用原有流程或Agent模式
    
    参数:
        db_session: 数据库会话
        user: 用户对象
        browser_id: 浏览器ID
        origin: 请求来源
        chat_messages: 聊天消息列表
        engine_name: 引擎名称，默认为"default"
        chat_id: 聊天ID，可选
        
    返回:
        Generator[ChatEvent, None, None]: 聊天事件生成器
    """
    # 加载引擎配置
    logger.info(f"【聊天服务】==== 聊天服务开始处理请求 ====")
    logger.info(f"【聊天服务】参数: engine_name={engine_name}, chat_id={chat_id}, browser_id={browser_id}, user={(user.email if user else 'None')}")
    
    try:
        engine_config = ChatEngineConfig.load_from_db(db_session, engine_name)
        logger.info(f"【聊天服务】引擎配置加载成功: {engine_config.get_db_chat_engine().name}")
        
        # 检查是否使用Agent模式
        agent_enabled = is_agent_mode_enabled(engine_config)
        logger.info(f"【聊天服务】模式检查结果: agent_enabled={agent_enabled}")
        
        # 创建AutoFlowAgent实例
        if agent_enabled:
            logger.info(f"【聊天服务】=== 使用Agent工作流模式 (engine: {engine_name}) ===")
        else:
            logger.info(f"【聊天服务】=== 使用传统模式，但仍通过AutoFlowAgent实现 (engine: {engine_name}) ===")
            
        # 解析聊天消息
        user_question = chat_messages[-1].content
        chat_history = [{"role": m.role, "content": m.content} for m in chat_messages[:-1]]
        logger.info(f"【聊天服务】用户问题: {user_question[:50]}..., 聊天历史长度: {len(chat_history)}")
        
        # 创建AutoFlowAgent实例
        logger.info("【聊天服务】开始创建Agent实例")
        agent = create_agent_chat_flow(
            db_session=db_session,
            user=user,
            browser_id=browser_id,
            origin=origin,
            chat_messages=chat_messages,
            engine_name=engine_name,
            chat_id=chat_id,
        )
        logger.info("【聊天服务】Agent实例创建完成")
        
        # 使用同步包装器处理异步生成器
        logger.info("【聊天服务】开始调用stream_chat方法")
        async_gen = agent.stream_chat(
            query=user_question, 
            chat_history=chat_history,
            db_chat_obj=agent.db_chat_obj
        )
        logger.info("【聊天服务】stream_chat方法调用完成，开始包装异步生成器")
            
        # 将异步生成器包装为同步生成器
        adapter = AsyncToSyncAdapter(async_gen)
        logger.info("【聊天服务】异步生成器已包装为同步生成器，开始迭代")
        
        event_count = 0
        for event in adapter:
            event_count += 1
            logger.info(f"【聊天服务】生成事件 #{event_count}: {type(event).__name__}")
            
            # 转换非ChatEvent对象为ChatEvent
            if not isinstance(event, ChatEvent) and not isinstance(event, str):
                logger.warning(f"【聊天服务】接收到非ChatEvent对象：{type(event).__name__}，进行转换")
                # 检查是否有answer属性（ResponseEvent）
                if hasattr(event, 'answer') and getattr(event, 'answer'):
                    logger.info(f"【聊天服务】转换ResponseEvent为ChatEvent.TEXT_PART，内容: {getattr(event, 'answer')[:50]}...")
                    # 转换为文本事件
                    event = ChatEvent(
                        event_type=ChatEventType.TEXT_PART,
                        payload={"message": getattr(event, 'answer')}
                    )
                else:
                    # 尝试将对象转换为JSON字符串
                    try:
                        import json
                        from pydantic import BaseModel
                        
                        # 如果是Pydantic模型，使用model_dump
                        if isinstance(event, BaseModel):
                            event_dict = event.model_dump()
                        else:
                            # 否则尝试直接转换为字典
                            event_dict = {
                                "event_type": type(event).__name__,
                                "data": {k: v for k, v in event.__dict__.items() if not k.startswith('_')}
                            }
                            
                        event = ChatEvent(
                            event_type=ChatEventType.DATA_PART,
                            payload=json.dumps(event_dict)
                        )
                        logger.info(f"【聊天服务】成功将事件转换为ChatEvent.DATA_PART")
                    except Exception as e:
                        logger.error(f"【聊天服务】转换事件失败: {str(e)}")
                        # 如果转换失败，跳过此事件
                        continue
            
            yield event
            
        logger.info(f"【聊天服务】事件生成完成，共生成 {event_count} 个事件")
        logger.info("【聊天服务】==== 聊天服务处理请求完成 ====")
        
    except Exception as e:
        logger.error(f"【聊天服务】处理聊天请求时出错: {str(e)}", exc_info=True)
        # 生成错误事件
        yield ChatEvent(
            event_type=ChatEventType.ERROR_PART,
            payload=f"处理聊天请求时出错: {str(e)}"
        )

class ChatService:
    def __init__(
        self,
        db_session: Session,
        user: User,
        browser_id: str,
        origin: str,
        chat_messages: List[ChatMessage],
        engine_name: str = "default",
        chat_id: Optional[UUID] = None,
    ):
        self.db_session = db_session
        self.user = user
        self.browser_id = browser_id
        self.origin = origin
        self.chat_messages = chat_messages
        self.engine_name = engine_name
        self.chat_id = chat_id
        
        self.engine_config = ChatEngineConfig.load_from_db(db_session, engine_name)
        logger.info(f"【ChatService】========== ChatService初始化 ==========")
        logger.info(f"【ChatService】引擎名称: {engine_name}, 聊天ID: {chat_id}")
        logger.info(f"【ChatService】Agent配置: enabled={self.engine_config.agent.enabled}, tools={self.engine_config.agent.enabled_tools}")
        logger.info(f"【ChatService】知识图谱配置: enabled={self.engine_config.knowledge_graph.enabled}")
        logger.info(f"【ChatService】数据库配置: enabled={self.engine_config.database.enabled}")
        logger.info(f"【ChatService】========== 配置加载完成 ==========")
        
    def process_message(self, *args, **kwargs):
        # 添加日志记录处理开始
        logger.info(f"【ChatService】========== 开始处理消息 ==========")
        logger.info(f"【ChatService】Agent模式配置状态: enabled={self.engine_config.agent.enabled}, tools={self.engine_config.agent.enabled_tools}")
        
        # 查找模式判断的位置并添加日志
        if self.engine_config.agent.enabled:
            logger.info("【ChatService】======> 将使用Agent模式处理消息")
        else:
            logger.info("【ChatService】======> 将使用传统工作流模式处理消息")
        
        # ... existing code ...
    
    def _process_with_agent(self, *args, **kwargs):
        # 如果有这个方法，添加详细日志
        logger.info(f"【ChatService】========== 使用Agent模式处理 ==========")
        logger.info(f"【ChatService】用户问题: {self.user_question}")
        
        try:
            # 记录Agent初始化
            logger.info(f"【ChatService】开始初始化AutoFlowAgent...")
            agent = AutoFlowAgent(
                db_session=self.db_session,
                user=self.user,
                browser_id=self.browser_id,
                origin=self.origin,
                chat_messages=self.chat_messages,
                engine_name=self.engine_name,
                chat_id=self.chat_id,
            )
            logger.info(f"【ChatService】AutoFlowAgent初始化成功，已加载工具: {[tool.metadata.name for tool in agent.tools]}")
            
            # ... 执行Agent逻辑 ...
            logger.info(f"【ChatService】开始执行Agent处理...")
            
            # ... existing code ...
            
        except Exception as e:
            logger.error(f"【ChatService】Agent模式处理失败: {e}", exc_info=True)
            logger.warning(f"【ChatService】回退到传统工作流模式...")
            # 可能有回退逻辑
            
        # ... existing code ...
        
        logger.info(f"【ChatService】========== Agent处理完成 ==========")
        
    def _generate_response(self, *args, **kwargs):
        # 如果有这个方法，添加日志标记开始
        logger.info(f"【ChatService】========== 开始生成响应 ==========")
        logger.info(f"【ChatService】当前模式: {'Agent模式' if self.engine_config.agent.enabled else '传统工作流模式'}")
        
        # ... existing code ...
        
        # 在关键判断位置添加日志
        if self.engine_config.agent.enabled:
            logger.info("【ChatService】使用Agent模式生成响应...")
            # Agent相关代码...
        else:
            logger.info("【ChatService】使用传统工作流生成响应...")
            # 传统工作流代码...
        
        # ... existing code ...
        
        logger.info(f"【ChatService】========== 响应生成完成 ==========")
