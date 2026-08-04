-- Performance indexes for dashboard/analytics queries.
-- These dramatically speed up the aggregate queries used by:
--   - /analytics/dashboard
--   - /analytics/executive-summary
--   - /evaluation/metrics
--   - /evaluation/unanswered
--   - /tickets

-- Queries table: org-scoped aggregate filters
CREATE INDEX IF NOT EXISTS ix_queries_org_escalated
    ON public.queries (org_id, escalated);

CREATE INDEX IF NOT EXISTS ix_queries_org_feedback
    ON public.queries (org_id, feedback);

CREATE INDEX IF NOT EXISTS ix_queries_org_confidence
    ON public.queries (org_id, confidence_score);

CREATE INDEX IF NOT EXISTS ix_queries_org_latency
    ON public.queries (org_id, latency_ms);

-- Composite for the most common dashboard filter: org + escalated + created_at
CREATE INDEX IF NOT EXISTS ix_queries_org_escalated_created
    ON public.queries (org_id, escalated, created_at);

-- Tickets table: org-scoped list ordering
CREATE INDEX IF NOT EXISTS ix_tickets_org_created
    ON public.tickets (org_id, created_at DESC);

-- Documents table: org-scoped status filter (already has ix_documents_org_status,
-- but add deleted_at to the composite for the ready+not-deleted filter)
CREATE INDEX IF NOT EXISTS ix_documents_org_status_deleted
    ON public.documents (org_id, status, deleted_at);