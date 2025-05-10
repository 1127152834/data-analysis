import logging
from uuid import UUID
from typing import List, Optional, Annotated
from http import HTTPStatus

from pydantic import (
    BaseModel,
    field_validator,
)
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from fastapi_pagination import Params, Page
from llama_index.core.base.llms.types import ChatMessage, MessageRole

from app.api.deps import SessionDep, OptionalUserDep, CurrentUserDep
from app.rag.chat.chat_flow import ChatFlow
from app.rag.retrievers.knowledge_graph.schema import KnowledgeGraphRetrievalResult
from app.repositories import chat_repo
from app.models import Chat, ChatUpdate

from app.rag.chat.chat_service import get_final_chat_result
from app.models import Chat, ChatUpdate, ChatFilters
from app.rag.chat.chat_service import (
    user_can_view_chat,
    user_can_edit_chat,
    get_chat_message_subgraph,
    get_chat_message_recommend_questions,
    remove_chat_message_recommend_questions,
)
from app.exceptions import InternalServerError

"""
聊天API路由模块

提供与聊天功能相关的所有API端点，包括创建聊天、获取聊天历史、
更新和删除聊天、获取推荐问题等功能。这是系统与前端交互的主要接口。
"""

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    """
    聊天请求模型

    定义了创建新聊天或继续已有聊天的请求数据结构
    """

    messages: List[ChatMessage]  # 聊天消息列表，包含用户和助手的消息
    chat_engine: str = "default"  # 使用的聊天引擎名称，默认为"default"
    chat_id: Optional[UUID] = None  # 聊天ID，如果是继续已有聊天则提供
    stream: bool = True  # 是否使用流式响应，默认为是

    @field_validator("messages")
    @classmethod
    def check_messages(cls, messages: List[ChatMessage]) -> List[ChatMessage]:
        """
        验证聊天消息的有效性

        确保消息列表不为空，每条消息的角色和内容有效，
        并且最后一条消息必须来自用户

        参数:
            messages: 要验证的聊天消息列表

        返回:
            验证通过的消息列表

        异常:
            ValueError: 如果消息无效
        """
        if not messages:
            raise ValueError("messages cannot be empty")
        for m in messages:
            if m.role not in [MessageRole.USER, MessageRole.ASSISTANT]:
                raise ValueError("role must be either 'user' or 'assistant'")
            if not m.content:
                raise ValueError("message content cannot be empty")
            if len(m.content) > 10000:
                raise ValueError("message content cannot exceed 1000 characters")
        if messages[-1].role != MessageRole.USER:
            raise ValueError("last message must be from user")
        return messages


@router.post("/chats")
def chats(
    request: Request,
    session: SessionDep,
    user: OptionalUserDep,
    chat_request: ChatRequest,
):
    """
    创建新聊天或继续已有聊天

    处理用户的聊天请求，创建新的聊天会话或继续已有会话，
    并返回系统的回复。支持流式响应和非流式响应。

    参数:
        request: FastAPI请求对象，用于获取来源和浏览器ID
        session: 数据库会话依赖
        user: 可选的当前用户依赖，允许匿名用户
        chat_request: 聊天请求数据

    返回:
        流式响应或完整的聊天结果

    异常:
        HTTPException: 如果请求处理过程中发生错误
        InternalServerError: 如果发生内部服务器错误
    """
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    browser_id = request.state.browser_id

    try:
        # 创建聊天流程对象
        chat_flow = ChatFlow(
            db_session=session,
            user=user,
            browser_id=browser_id,
            origin=origin,
            chat_id=chat_request.chat_id,
            chat_messages=chat_request.messages,
            engine_name=chat_request.chat_engine,
        )

        # 根据请求类型返回流式响应或非流式响应
        if chat_request.stream:
            return StreamingResponse(
                chat_flow.chat(),
                media_type="text/event-stream",
                headers={
                    "X-Content-Type-Options": "nosniff",
                },
            )
        else:
            return get_final_chat_result(chat_flow.chat())
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(e)
        raise InternalServerError()


@router.get("/chats")
def list_chats(
    request: Request,
    session: SessionDep,
    user: OptionalUserDep,
    filters: Annotated[ChatFilters, Query()],
    params: Params = Depends(),
) -> Page[Chat]:
    """
    获取聊天会话列表

    根据提供的过滤条件获取用户可查看的聊天会话列表，
    支持分页和筛选。

    参数:
        request: FastAPI请求对象，用于获取浏览器ID
        session: 数据库会话依赖
        user: 可选的当前用户依赖，允许匿名用户
        filters: 聊天过滤条件
        params: 分页参数

    返回:
        Chat分页对象，包含符合条件的聊天会话列表
    """
    browser_id = request.state.browser_id
    return chat_repo.paginate(session, user, browser_id, filters, params)


@router.get("/chats/{chat_id}")
def get_chat(session: SessionDep, user: OptionalUserDep, chat_id: UUID):
    """
    获取单个聊天会话详情

    根据聊天ID获取聊天会话的详细信息，包括所有消息。

    参数:
        session: 数据库会话依赖
        user: 可选的当前用户依赖，允许匿名用户
        chat_id: 要获取的聊天会话ID

    返回:
        包含聊天会话和消息的字典

    异常:
        HTTPException: 如果用户无权访问该聊天会话
    """
    chat = chat_repo.must_get(session, chat_id)

    # 检查用户是否有权查看该聊天
    if not user_can_view_chat(chat, user):
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Access denied")

    return {
        "chat": chat,
        "messages": chat_repo.get_messages(session, chat),
    }


@router.put("/chats/{chat_id}")
def update_chat(
    session: SessionDep, user: CurrentUserDep, chat_id: UUID, chat_update: ChatUpdate
):
    """
    更新聊天会话

    更新指定聊天会话的信息，如标题和可见性设置。

    参数:
        session: 数据库会话依赖
        user: 当前用户依赖，必须已登录
        chat_id: 要更新的聊天会话ID
        chat_update: 聊天更新数据

    返回:
        更新后的聊天会话对象

    异常:
        HTTPException: 如果用户无权编辑该聊天会话
        InternalServerError: 如果发生内部服务器错误
    """
    try:
        chat = chat_repo.must_get(session, chat_id)

        # 检查用户是否有权编辑该聊天
        if not user_can_edit_chat(chat, user):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="Access denied"
            )

        return chat_repo.update(session, chat, chat_update)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(e, exc_info=True)
        raise InternalServerError()


@router.delete("/chats/{chat_id}")
def delete_chat(session: SessionDep, user: CurrentUserDep, chat_id: UUID):
    """
    删除聊天会话

    将指定的聊天会话标记为已删除（软删除）。

    参数:
        session: 数据库会话依赖
        user: 当前用户依赖，必须已登录
        chat_id: 要删除的聊天会话ID

    返回:
        删除操作的结果

    异常:
        HTTPException: 如果用户无权删除该聊天会话
        InternalServerError: 如果发生内部服务器错误
    """
    try:
        chat = chat_repo.must_get(session, chat_id)

        # 检查用户是否有权编辑该聊天
        if not user_can_edit_chat(chat, user):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="Access denied"
            )

        return chat_repo.delete(session, chat)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(e, exc_info=True)
        raise InternalServerError()


@router.get(
    "/chat-messages/{chat_message_id}/subgraph",
    response_model=KnowledgeGraphRetrievalResult,
)
def get_chat_subgraph(session: SessionDep, user: OptionalUserDep, chat_message_id: int):
    """
    获取聊天消息的知识图谱子图

    获取与特定聊天消息相关的知识图谱子图数据，用于可视化展示。

    参数:
        session: 数据库会话依赖
        user: 可选的当前用户依赖，允许匿名用户
        chat_message_id: 聊天消息ID

    返回:
        知识图谱检索结果对象

    异常:
        HTTPException: 如果用户无权访问该聊天消息
        InternalServerError: 如果发生内部服务器错误
    """
    try:
        chat_message = chat_repo.must_get_message(session, chat_message_id)

        # 检查用户是否有权查看该聊天
        if not user_can_view_chat(chat_message.chat, user):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="Access denied"
            )

        result = get_chat_message_subgraph(session, chat_message)
        return result.model_dump(exclude_none=True)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(e, exc_info=True)
        raise InternalServerError()


@router.get("/chat-messages/{chat_message_id}/recommended-questions")
def get_recommended_questions(
    session: SessionDep, user: OptionalUserDep, chat_message_id: int
) -> List[str]:
    """
    获取推荐问题

    获取基于特定聊天消息内容生成的推荐后续问题列表。

    参数:
        session: 数据库会话依赖
        user: 可选的当前用户依赖，允许匿名用户
        chat_message_id: 聊天消息ID

    返回:
        推荐问题字符串列表

    异常:
        HTTPException: 如果用户无权访问该聊天消息
        InternalServerError: 如果发生内部服务器错误
    """
    try:
        chat_message = chat_repo.must_get_message(session, chat_message_id)

        # 检查用户是否有权查看该聊天
        if not user_can_view_chat(chat_message.chat, user):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="Access denied"
            )

        return get_chat_message_recommend_questions(session, chat_message)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(e, exc_info=True)
        raise InternalServerError()


@router.post("/chat-messages/{chat_message_id}/recommended-questions")
def refresh_recommended_questions(
    session: SessionDep, user: OptionalUserDep, chat_message_id: int
) -> List[str]:
    """
    刷新推荐问题

    删除并重新生成特定聊天消息的推荐后续问题。

    参数:
        session: 数据库会话依赖
        user: 可选的当前用户依赖，允许匿名用户
        chat_message_id: 聊天消息ID

    返回:
        新生成的推荐问题字符串列表

    异常:
        HTTPException: 如果用户无权访问该聊天消息
        InternalServerError: 如果发生内部服务器错误
    """
    try:
        chat_message = chat_repo.must_get_message(session, chat_message_id)

        # 检查用户是否有权查看该聊天
        if not user_can_view_chat(chat_message.chat, user):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="Access denied"
            )

        # 删除现有推荐问题
        remove_chat_message_recommend_questions(session, chat_message_id)

        # 重新生成推荐问题
        return get_chat_message_recommend_questions(session, chat_message)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(e, exc_info=True)
        raise InternalServerError()
