"""
Knowledge Agent — RAG chat pipeline behind POST /query and /query/stream.

embed → pgvector retrieve → rerank → relevance grade → LLM answer + citations.
Org-scoped chunks only. Optional Redis cache (QueryCacheService) on repeat queries.
"""

import json
import time
import uuid
from collections.abc import AsyncGenerator
from typing_extensions import TypedDict, cast

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db.tables import QueryLog
from app.models.internal.domain import (
    CitationRaw,
    GradedRagChunkItem,
    RagChunkItem,
    as_graded_chunks,
)
from app.models.http.schemas import (
    Citation,
    QueryResponse,
    RetrievalCandidate,
    RetrievalTrace,
)
from app.models.http.stream import (
    RetrievalTraceJson,
    StreamDoneEvent,
    citation_to_json,
)
from app.core.feature_flags import flags
from app.services.confidence_service import ConfidenceService
from app.services.document_access_service import DocumentAccessService
from app.services.embedding_service import EmbeddingService
from app.services.escalation_service import EscalationService
from app.services.grading_service import GradingService
from app.services.llm_service import LLMService
from app.services.query_expansion_service import QueryExpansionService
from app.services.rerank_service import RerankService
from app.services.citation_parser import parse_knowledge_answer
from app.services.rag_context import format_rag_context
from app.services.vector_service import VectorService


class KnowledgeState(TypedDict, total=False):
    query: str
    parsed_query: str
    chunk_items: list[GradedRagChunkItem]
    context: str
    answer: str
    citations: list[CitationRaw]


# LangGraph node partial returns use the same shape as state updates.
KnowledgeStateUpdate = KnowledgeState


class KnowledgeAgent:
    """LangGraph RAG orchestrator — called only from query router, not from Slack."""

    def __init__(self) -> None:
        self.embedder = EmbeddingService()
        self.llm = LLMService()
        self.vector = VectorService()
        self.grader = GradingService()
        self.reranker = RerankService()
        self.confidence = ConfidenceService()
        self.access = DocumentAccessService()
        self.escalation = EscalationService()
        self.expansion = QueryExpansionService()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(KnowledgeState)
        workflow.add_node("parse_query", self._parse_query)
        workflow.add_node("grade_relevance", self._grade_relevance)
        workflow.add_node("rerank_chunks", self._rerank_chunks)
        workflow.add_node("generate_answer", self._generate_answer)
        workflow.add_node("format_citations", self._format_citations)
        workflow.set_entry_point("parse_query")
        workflow.add_edge("parse_query", "grade_relevance")
        workflow.add_edge("grade_relevance", "rerank_chunks")
        workflow.add_edge("rerank_chunks", "generate_answer")
        workflow.add_edge("generate_answer", "format_citations")
        workflow.add_edge("format_citations", END)
        return workflow.compile()

    async def _parse_query(self, state: KnowledgeState) -> KnowledgeStateUpdate:
        return {"parsed_query": state.get("query", "").strip()}

    async def _grade_relevance(self, state: KnowledgeState) -> KnowledgeStateUpdate:
        chunks = list(state.get("chunk_items", []))
        graded = await self.grader.filter_chunks(
            state.get("parsed_query", state.get("query", "")),
            chunks,
            min_grade=settings.min_relevance_grade,
        )
        if not graded and chunks:
            graded = sorted(chunks, key=lambda c: c.get("score", 0), reverse=True)[
                : settings.rerank_top_k
            ]
        return {"chunk_items": graded}

    async def _rerank_chunks(self, state: KnowledgeState) -> KnowledgeStateUpdate:
        reranked = await self.reranker.rerank(
            state.get("parsed_query", state.get("query", "")),
            list(state.get("chunk_items", [])),
            top_n=settings.rerank_top_k,
        )
        return {"chunk_items": reranked}

    async def _generate_answer(self, state: KnowledgeState) -> KnowledgeStateUpdate:
        items = state.get("chunk_items", [])
        if not items:
            return {
                "answer": (
                    "I don't have enough information in the knowledge base to answer "
                    "that question."
                ),
                "context": "",
            }
        context = format_rag_context(items)
        parsed = state.get("parsed_query", state.get("query", ""))
        raw_answer = await self.llm.generate_answer(
            parsed, context, chunk_items=items
        )
        answer, citations = parse_knowledge_answer(
            raw_answer, list(state.get("chunk_items", []))
        )
        return {"answer": answer, "context": context, "citations": citations}

    async def _format_citations(self, state: KnowledgeState) -> KnowledgeStateUpdate:
        if state.get("citations"):
            return {"citations": state["citations"]}
        citations = []
        for item in state.get("chunk_items", []):
            citations.append(
                {
                    "chunk_id": str(item["chunk_id"]),
                    "document_id": str(item["document_id"])
                    if item.get("document_id")
                    else None,
                    "document_name": item["document_name"],
                    "page_number": item.get("page_number"),
                    "chunk_text": item["content"],
                    "excerpt": item["content"][:200],
                }
            )
        return {"citations": citations}

    async def _retrieve(
        self,
        db: AsyncSession,
        query: str,
        org_id: uuid.UUID | None,
        *,
        user_role: str = "employee",
        user_department: str | None = None,
    ) -> list[RagChunkItem]:
        embedding = await self.embedder.embed(query)
        min_score = 0.2 if self.embedder.uses_openai_embeddings else 0.0
        access_filter = None
        if flags.DOCUMENT_RBAC_ENABLED:
            access_filter = self.access.sqlalchemy_access_filter(
                role=user_role,
                department=user_department,
            )
        rows = await self.vector.similarity_search(
            db,
            embedding,
            org_id=org_id,
            top_k=settings.retrieval_top_k,
            min_score=min_score,
            access_filter=access_filter,
        )
        items: list[RagChunkItem] = []
        for chunk, score, document in rows:
            items.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": document.id,
                    "content": chunk.content,
                    "document_name": document.filename,
                    "page_number": chunk.page_number,
                    "score": score,
                }
            )
        return items

    async def _retrieve_expanded(
        self,
        db: AsyncSession,
        query: str,
        org_id: uuid.UUID | None,
        *,
        user_role: str = "employee",
        user_department: str | None = None,
    ) -> tuple[list[RagChunkItem], list[str]]:
        expanded = self.expansion.expand(query)
        merged: dict[uuid.UUID, RagChunkItem] = {}
        for variant in expanded or [query]:
            items = await self._retrieve(
                db,
                variant,
                org_id,
                user_role=user_role,
                user_department=user_department,
            )
            for item in items:
                chunk_id = item["chunk_id"]
                if (
                    chunk_id not in merged
                    or (item.get("score") or 0) > (merged[chunk_id].get("score") or 0)
                ):
                    merged[chunk_id] = item
        ranked = sorted(
            merged.values(), key=lambda c: c.get("score", 0), reverse=True
        )[: settings.retrieval_top_k]
        return ranked, expanded

    @staticmethod
    def _candidate_trace(
        item: GradedRagChunkItem, stage: str
    ) -> RetrievalCandidate:
        content = item.get("content") or ""
        return RetrievalCandidate(
            document_name=item.get("document_name") or "unknown",
            chunk_id=item.get("chunk_id"),
            score=item.get("score"),
            grade=item.get("grade"),
            stage=stage,
            excerpt=content[:160] if content else None,
        )

    async def _run_pipeline(
        self,
        query: str,
        chunk_items: list[GradedRagChunkItem],
        *,
        expanded_queries: list[str],
        include_trace: bool,
        through_rerank_only: bool = False,
    ) -> tuple[KnowledgeState, RetrievalTrace | None]:
        trace_candidates: list[RetrievalCandidate] = []
        if include_trace:
            trace_candidates.extend(
                self._candidate_trace(c, "retrieved") for c in chunk_items
            )

        state: KnowledgeState = {"query": query, "chunk_items": chunk_items}
        state.update(await self._parse_query(state))
        state.update(await self._grade_relevance(state))
        if include_trace:
            trace_candidates.extend(
                self._candidate_trace(c, "graded")
                for c in state.get("chunk_items", [])
            )

        state.update(await self._rerank_chunks(state))
        if include_trace:
            trace_candidates.extend(
                self._candidate_trace(c, "reranked")
                for c in state.get("chunk_items", [])
            )

        if not through_rerank_only:
            state.update(await self._generate_answer(state))
            state.update(await self._format_citations(state))
        else:
            state.update(await self._format_citations(state))

        trace: RetrievalTrace | None = None
        if include_trace:
            trace = RetrievalTrace(
                original_query=query,
                expanded_queries=expanded_queries,
                candidates=trace_candidates,
            )
        return state, trace

    @staticmethod
    def _to_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

    def _build_citation_models(self, raw: list[CitationRaw]) -> list[Citation]:
        citations: list[Citation] = []
        for c in raw:
            chunk_id = c.get("chunk_id")
            doc_id = c.get("document_id")
            doc_name = c.get("document_name") or "unknown"
            chunk_text = c.get("chunk_text") or ""
            citations.append(
                Citation(
                    chunk_id=self._to_uuid(chunk_id),
                    document_id=self._to_uuid(doc_id),
                    document_name=doc_name,
                    page_number=c.get("page_number"),
                    chunk_text=chunk_text,
                    excerpt=c.get("excerpt"),
                    exact_quote_highlight=c.get("exact_quote_highlight"),
                    citation_index=c.get("citation_index"),
                )
            )
        return citations

    async def _save_query_log(
        self,
        db: AsyncSession,
        *,
        query: str,
        answer: str,
        citations: list[Citation],
        user_id: uuid.UUID | None,
        org_id: uuid.UUID | None,
        latency_ms: int,
        session_id: str | None = None,
        model: str | None = None,
        confidence_score: float | None = None,
        escalated: bool = False,
        escalation_ticket_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        log = QueryLog(
            user_id=user_id,
            org_id=org_id,
            session_id=session_id,
            query_text=query,
            answer_text=answer,
            cited_chunks=[c.model_dump(mode="json") for c in citations],
            cited_chunk_ids=[
                str(c.chunk_id) for c in citations if c.chunk_id is not None
            ],
            model=model or settings.openai_chat_model,
            latency_ms=latency_ms,
            confidence_score=confidence_score,
            escalated=escalated,
            escalation_ticket_id=escalation_ticket_id,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log.id

    def _low_confidence_answer(self, confidence: float) -> str:
        return (
            "I'm not confident I can answer that accurately from our documents "
            f"(confidence {confidence:.0%}). I've escalated this to a human "
            "who will follow up shortly."
        )

    async def _maybe_escalate(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        query: str,
        confidence: float,
        answer: str,
        has_chunks: bool,
    ) -> tuple[str, bool, uuid.UUID | None]:
        if not flags.CONFIDENCE_ESCALATION_ENABLED or org_id is None:
            return answer, False, None
        if has_chunks and not self.confidence.is_low_confidence(confidence):
            return answer, False, None
        ticket_id = await self.escalation.escalate_query(
            db,
            org_id=org_id,
            user_id=user_id,
            query=query,
            confidence=confidence,
            answer_preview=answer,
        )
        return self._low_confidence_answer(confidence), True, ticket_id

    async def run(
        self,
        db: AsyncSession,
        query: str,
        *,
        user_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        session_id: str | None = None,
        user_role: str = "employee",
        user_department: str | None = None,
    ) -> QueryResponse:
        start = time.perf_counter()
        retrieved, expanded_queries = await self._retrieve_expanded(
            db,
            query,
            org_id,
            user_role=user_role,
            user_department=user_department,
        )
        chunk_items = as_graded_chunks(retrieved)
        include_trace = flags.RETRIEVAL_TRACE_ENABLED
        final_state, retrieval_trace = await self._run_pipeline(
            query,
            chunk_items,
            expanded_queries=expanded_queries,
            include_trace=include_trace,
        )
        answer = final_state.get("answer", "")
        citations = self._build_citation_models(final_state.get("citations", []))
        confidence = self.confidence.compute(final_state.get("chunk_items", chunk_items))
        answer, escalated, escalation_ticket_id = await self._maybe_escalate(
            db,
            org_id=org_id,
            user_id=user_id,
            query=query,
            confidence=confidence,
            answer=answer,
            has_chunks=bool(chunk_items),
        )
        if escalated:
            citations = []
        latency_ms = int((time.perf_counter() - start) * 1000)
        query_log_id = await self._save_query_log(
            db,
            query=query,
            answer=answer,
            citations=citations,
            user_id=user_id,
            org_id=org_id,
            latency_ms=latency_ms,
            session_id=session_id,
            confidence_score=confidence,
            escalated=escalated,
            escalation_ticket_id=escalation_ticket_id,
        )
        return QueryResponse(
            answer=answer,
            citations=citations,
            latency_ms=latency_ms,
            confidence_score=confidence,
            escalated=escalated,
            escalation_ticket_id=escalation_ticket_id,
            query_log_id=query_log_id,
            retrieval_trace=retrieval_trace,
        )

    async def _pipeline_through_rerank(
        self, query: str, chunk_items: list[GradedRagChunkItem]
    ) -> KnowledgeState:
        state: KnowledgeState = {"query": query, "chunk_items": chunk_items}
        state.update(await self._parse_query(state))
        state.update(await self._grade_relevance(state))
        state.update(await self._rerank_chunks(state))
        state.update(await self._format_citations(state))
        return state

    async def run_stream(
        self,
        db: AsyncSession,
        query: str,
        *,
        user_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        session_id: str | None = None,
        user_role: str = "employee",
        user_department: str | None = None,
    ) -> AsyncGenerator[str, None]:
        start = time.perf_counter()
        retrieved, expanded_queries = await self._retrieve_expanded(
            db,
            query,
            org_id,
            user_role=user_role,
            user_department=user_department,
        )
        chunk_items = as_graded_chunks(retrieved)
        include_trace = flags.RETRIEVAL_TRACE_ENABLED
        pipeline_state, retrieval_trace = await self._run_pipeline(
            query,
            chunk_items,
            expanded_queries=expanded_queries,
            include_trace=include_trace,
            through_rerank_only=True,
        )
        items = pipeline_state.get("chunk_items", [])
        confidence = self.confidence.compute(items)
        context = format_rag_context(items) if items else ""
        citations = self._build_citation_models(pipeline_state.get("citations", []))

        should_escalate = (
            flags.CONFIDENCE_ESCALATION_ENABLED
            and org_id is not None
            and (not items or self.confidence.is_low_confidence(confidence))
        )

        if should_escalate:
            clean_answer, escalated, escalation_ticket_id = await self._maybe_escalate(
                db,
                org_id=org_id,
                user_id=user_id,
                query=query,
                confidence=confidence,
                answer="",
                has_chunks=bool(items),
            )
            yield json.dumps({"type": "token", "content": clean_answer}) + "\n"
            citations = []
        else:
            raw_answer = ""
            async for token in self.llm.stream_answer(
                query, context, chunk_items=items
            ):
                raw_answer += token
                yield json.dumps({"type": "token", "content": token}) + "\n"
            clean_answer, parsed_raw = parse_knowledge_answer(raw_answer, items)
            citations = self._build_citation_models(
                parsed_raw or pipeline_state.get("citations", [])
            )
            escalated = False
            escalation_ticket_id = None

        latency_ms = int((time.perf_counter() - start) * 1000)
        query_log_id = await self._save_query_log(
            db,
            query=query,
            answer=clean_answer,
            citations=citations,
            user_id=user_id,
            org_id=org_id,
            latency_ms=latency_ms,
            session_id=session_id,
            confidence_score=confidence,
            escalated=escalated,
            escalation_ticket_id=escalation_ticket_id,
        )
        done: StreamDoneEvent = {
            "type": "done",
            "answer": clean_answer,
            "citations": [citation_to_json(c) for c in citations],
            "latency_ms": latency_ms,
            "confidence_score": confidence,
            "escalated": escalated,
            "escalation_ticket_id": str(escalation_ticket_id)
            if escalation_ticket_id
            else None,
            "query_log_id": str(query_log_id),
        }
        if retrieval_trace is not None:
            done["retrieval_trace"] = cast(
                RetrievalTraceJson, retrieval_trace.model_dump(mode="json")
            )
        yield json.dumps(done) + "\n"
