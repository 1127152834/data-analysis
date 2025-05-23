from typing import List, Optional

from litellm.rerank_api.main import rerank
from llama_index.core.bridge.pydantic import Field
from llama_index.core.callbacks import CBEventType, EventPayload
from llama_index.core.instrumentation import get_dispatcher
from llama_index.core.instrumentation.events.rerank import (
    ReRankEndEvent,
    ReRankStartEvent,
)
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle, MetadataMode

dispatcher = get_dispatcher(__name__)


class LiteLLMReranker(BaseNodePostprocessor):
    model: str = Field(description="Reranker model name.")
    top_n: int = Field(description="Top N nodes to return.")
    api_base: Optional[str] = Field(description="Reranker API base url.", default=None)
    api_key: Optional[str] = Field(description="Reranker API key.")

    def __init__(
        self,
        top_n: int = 2,
        model: str = "rerank_models-english-v2.0",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        super().__init__(top_n=top_n, model=model, api_base=api_base, api_key=api_key)

    @classmethod
    def class_name(cls) -> str:
        return "LiteLLMRerank"

    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        dispatcher.event(
            ReRankStartEvent(
                query=query_bundle, nodes=nodes, top_n=self.top_n, model_name=self.model
            )
        )

        if query_bundle is None:
            raise ValueError("Missing query bundle in extra info.")
        if len(nodes) == 0:
            return []

        with self.callback_manager.event(
            CBEventType.RERANKING,
            payload={
                EventPayload.NODES: nodes,
                EventPayload.MODEL_NAME: self.model,
                EventPayload.QUERY_STR: query_bundle.query_str,
                EventPayload.TOP_K: self.top_n,
            },
        ) as event:
            texts = [
                node.node.get_content(metadata_mode=MetadataMode.EMBED)
                for node in nodes
            ]
            results = rerank(
                model=self.model,
                query=query_bundle.query_str,
                documents=texts,
                top_n=self.top_n,
                api_base=self.api_base,
                api_key=self.api_key,
            )

            new_nodes = []
            for result in results.results:
                new_node_with_score = NodeWithScore(
                    node=nodes[result["index"]].node, score=result["relevance_score"]
                )
                new_nodes.append(new_node_with_score)
            event.on_end(payload={EventPayload.NODES: new_nodes})

        dispatcher.event(ReRankEndEvent(nodes=new_nodes))
        return new_nodes
