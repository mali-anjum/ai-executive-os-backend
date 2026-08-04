import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.http.enums import DocumentStatus, TicketSource, TicketStatus, UserRole
from app.models.internal.domain import TopQuestionRow


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: DocumentStatus
    mime_type: str | None = None
    file_size_bytes: int | None = None
    page_count: int | None = None
    allowed_departments: list[str] | None = None
    allowed_roles: list[str] | None = None
    source_connector: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IngestResponse(BaseModel):
    document_id: uuid.UUID
    status: DocumentStatus = "pending"
    message: str = "Document queued for processing"


class Citation(BaseModel):
    chunk_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    document_name: str
    page_number: int | None = None
    chunk_text: str
    excerpt: str | None = None
    exact_quote_highlight: str | None = None
    citation_index: int | None = None


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    session_id: str | None = Field(default=None, max_length=64)


class RetrievalCandidate(BaseModel):
    document_name: str
    chunk_id: uuid.UUID | None = None
    score: float | None = None
    grade: int | None = None
    stage: str
    excerpt: str | None = None


class RetrievalTrace(BaseModel):
    original_query: str
    expanded_queries: list[str] = []
    candidates: list[RetrievalCandidate] = []


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    latency_ms: int | None = None
    confidence_score: float | None = None
    escalated: bool = False
    escalation_ticket_id: uuid.UUID | None = None
    query_log_id: uuid.UUID | None = None
    retrieval_trace: RetrievalTrace | None = None


class HarnessCaseResult(BaseModel):
    id: str
    question: str
    passed: bool
    answer_preview: str
    confidence_score: float | None = None
    escalated: bool = False
    checks: dict = Field(default_factory=dict)


class HarnessRunResponse(BaseModel):
    total_cases: int
    passed: int
    failed: int
    accuracy_pct: float
    results: list[HarnessCaseResult]


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None = None
    job_title: str | None = None
    role: UserRole
    org_id: uuid.UUID | None = None
    department: str | None = None
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class TicketResponse(BaseModel):
    id: uuid.UUID
    source: TicketSource
    title: str | None = None
    intent: str | None
    priority: int | None
    summary: str | None
    department: str | None
    status: TicketStatus
    assignee_email: str | None = None
    assignee_id: uuid.UUID | None = None
    assignee_name: str | None = None
    slack_channel_id: str | None = None
    requires_approval: bool = False
    approval_status: str = "auto_approved"
    external_ticket_id: str | None = None
    due_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsDashboard(BaseModel):
    queries_today: int
    latency_p50_ms: int | None
    latency_p95_ms: int | None
    documents_indexed: int
    top_questions: list[TopQuestionRow]


class ExecutiveSummary(BaseModel):
    total_queries: int
    queries_today: int
    automated_queries: int
    escalated_queries: int
    estimated_hours_saved: float
    automation_rate_pct: float
    escalation_rate_pct: float
    documents_ready: int
    open_tickets: int
    low_confidence_unanswered: int
    knowledge_gaps: list[TopQuestionRow]
    department_scope: str | None = None


class UnansweredQuestionsReport(BaseModel):
    escalated: list[TopQuestionRow]
    low_confidence: list[TopQuestionRow]
    negative_feedback: list[TopQuestionRow]
    total_gaps: int


class QueryEscalateRequest(BaseModel):
    query: str = Field(..., min_length=1)
    query_log_id: uuid.UUID | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    answer_preview: str | None = None


class QueryEscalateResponse(BaseModel):
    escalated: bool = True
    escalation_ticket_id: uuid.UUID
    message: str


class DemoSeedResponse(BaseModel):
    documents_queued: int
    sample_queries: int
    sample_tickets: int
    message: str


class EvaluationMetrics(BaseModel):
    total_queries: int
    escalated_queries: int
    low_confidence_queries: int
    positive_feedback: int
    negative_feedback: int
    accuracy_pct: float | None
    escalation_rate_pct: float
    avg_confidence_pct: float | None
    unanswered_questions: list[TopQuestionRow]


class QueryFeedbackRequest(BaseModel):
    feedback: str = Field(..., pattern="^(positive|negative)$")


class IntegrationConfigRequest(BaseModel):
    provider: str = Field(..., min_length=2, max_length=32)
    config: dict = Field(default_factory=dict)


class NotionSyncRequest(BaseModel):
    page_id: str = Field(..., min_length=8)
    allowed_departments: list[str] | None = None
    allowed_roles: list[str] | None = None


class GoogleDriveSyncRequest(BaseModel):
    file_id: str = Field(..., min_length=8)
    allowed_departments: list[str] | None = None
    allowed_roles: list[str] | None = None


class DocumentAccessUpdate(BaseModel):
    allowed_departments: list[str] | None = None
    allowed_roles: list[str] | None = None


class ConnectorSyncResponse(BaseModel):
    id: uuid.UUID
    connector: str
    external_id: str
    document_id: uuid.UUID | None = None
    status: str
    last_synced_at: datetime | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}
