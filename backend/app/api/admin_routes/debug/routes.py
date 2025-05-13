from fastapi import APIRouter
import logging
from sqlmodel import select, Session

from app.api.deps import SessionDep, CurrentSuperuserDep
from app.models.chat_engine import ChatEngine

router = APIRouter()
logger = logging.getLogger("knowledge_base")


@router.get("/admin/debug/chat-engines/{engine_id}/raw")
def get_raw_chat_engine(session: SessionDep, user: CurrentSuperuserDep, engine_id: int):
    """Debug endpoint to inspect raw chat engine data"""
    engine = session.exec(select(ChatEngine).where(ChatEngine.id == engine_id)).first()
    if not engine:
        return {"error": f"Chat engine {engine_id} not found"}

    # Get info about the engine_options structure
    knowledge_base = engine.engine_options.get("knowledge_base", {})
    linked_kb = knowledge_base.get("linked_knowledge_base", {})
    linked_kbs = knowledge_base.get("linked_knowledge_bases", [])

    logger.debug(f"Chat engine {engine_id} knowledge base config: {knowledge_base}")

    return {
        "id": engine.id,
        "name": engine.name,
        "engine_options": engine.engine_options,
        "knowledge_base_config": {
            "linked_knowledge_base": linked_kb,
            "linked_knowledge_bases": linked_kbs,
        },
    }


@router.get("/admin/debug/chat-engines")
def list_all_chat_engines(session: SessionDep, user: CurrentSuperuserDep):
    """Debug endpoint to inspect all chat engines and their knowledge base references"""
    engines = session.exec(
        select(ChatEngine).where(ChatEngine.deleted_at == None)
    ).all()

    result = []
    for engine in engines:
        kb_config = engine.engine_options.get("knowledge_base", {})

        # Extract linked knowledge base information
        linked_kb = kb_config.get("linked_knowledge_base")
        linked_kb_id = linked_kb.get("id") if linked_kb else None

        linked_kbs = kb_config.get("linked_knowledge_bases", [])
        linked_kb_ids = [kb.get("id") for kb in linked_kbs if kb.get("id")]

        result.append(
            {
                "id": engine.id,
                "name": engine.name,
                "knowledge_base_config": {
                    "linked_knowledge_base_id": linked_kb_id,
                    "linked_knowledge_bases_ids": linked_kb_ids,
                },
            }
        )

    return result


@router.get("/admin/debug/knowledge-bases/{kb_id}/linked-engines")
def list_linked_engines_for_kb(
    session: SessionDep, user: CurrentSuperuserDep, kb_id: int
):
    """Debug endpoint to inspect what chat engines reference a specific knowledge base"""
    from app.repositories.knowledge_base import knowledge_base_repo

    # Get the linked chat engines using our repository method
    engines = knowledge_base_repo.list_linked_chat_engines(session, kb_id)

    # Extract relevant details from each chat engine
    result = []
    for engine in engines:
        # Get knowledge base config
        kb_config = engine.engine_options.get("knowledge_base", {})

        # Extract linked_knowledge_base info
        linked_kb = kb_config.get("linked_knowledge_base", {})
        linked_kb_id = linked_kb.get("id") if linked_kb else None

        # Extract linked_knowledge_bases array
        linked_kbs = kb_config.get("linked_knowledge_bases", [])
        linked_kb_ids = [kb.get("id") for kb in linked_kbs if kb.get("id")]

        # Check if our target kb_id is in either place
        in_legacy = linked_kb_id == kb_id
        in_array = kb_id in linked_kb_ids

        result.append(
            {
                "id": engine.id,
                "name": engine.name,
                "references_kb": in_legacy or in_array,
                "kb_references": {
                    "in_legacy_field": in_legacy,
                    "in_array": in_array,
                    "linked_knowledge_base_id": linked_kb_id,
                    "linked_knowledge_bases_ids": linked_kb_ids,
                },
            }
        )

    return result
