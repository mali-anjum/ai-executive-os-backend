-- Document-level RBAC (L3) in vector retrieval.
--
-- Previously the Knowledge Agent composed a document-level RBAC predicate in
-- Python (SQLAlchemy) and applied it to the pgvector similarity query over
-- FastAPI's privileged (postgres) connection. This migration moves that
-- authorization into a SECURITY DEFINER RPC so the database is the security
-- boundary: unauthorized chunks never leave PostgreSQL.
--
-- Authorization model (mirrors app/services/document_access_service.py and the
-- role hierarchy owner > admin > manager > employee):
--   * owner / admin     -> every non-deleted document in the org
--   * manager/employee  -> must match documents.allowed_roles (when set) AND
--     documents.allowed_departments (when set; a user without a department can
--     only see documents that have no department restriction).
--
-- The function is invoked by FastAPI over its privileged connection; org_id,
-- role and department are derived server-side from the authenticated JWT, never
-- from the client. EXECUTE is revoked from PUBLIC so the client cannot call this
-- SECURITY DEFINER function directly through PostgREST and forge org/role.

CREATE OR REPLACE FUNCTION public.search_document_chunks(
    p_query_embedding vector,
    p_org_id uuid,
    p_user_role text DEFAULT 'employee',
    p_user_department text DEFAULT NULL,
    p_top_k integer DEFAULT 10,
    p_min_score double precision DEFAULT 0.0
)
RETURNS TABLE (
    chunk_id uuid,
    document_id uuid,
    document_name text,
    content text,
    page_number integer,
    score double precision
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    WITH authorized_documents AS (
        SELECT d.id, d.filename
        FROM public.documents d
        WHERE (p_org_id IS NULL OR d.org_id = p_org_id)
          AND d.deleted_at IS NULL
          AND (
              p_user_role IN ('owner', 'admin')
              OR (
                  -- role must be allowed (NULL / empty list means "any role")
                  (
                      d.allowed_roles IS NULL
                      OR jsonb_array_length(d.allowed_roles) = 0
                      OR d.allowed_roles ? p_user_role
                  )
                  AND
                  -- department must be allowed (NULL / empty list means "any
                  -- department"; a user without a department is only allowed
                  -- when the document has no department restriction)
                  (
                      d.allowed_departments IS NULL
                      OR jsonb_array_length(d.allowed_departments) = 0
                      OR (p_user_department IS NOT NULL
                          AND d.allowed_departments ? p_user_department)
                  )
              )
          )
    ),
    ranked AS (
        SELECT
            c.id,
            c.document_id,
            d.filename,
            c.content,
            c.page_number,
            1 - (c.embedding <=> p_query_embedding) AS score
        FROM public.document_chunks c
        JOIN authorized_documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> p_query_embedding
        LIMIT p_top_k
    )
    SELECT
        r.id AS chunk_id,
        r.document_id,
        r.filename AS document_name,
        r.content,
        r.page_number,
        r.score
    FROM ranked r
    WHERE r.score >= p_min_score;
$$;

-- Only the privileged backend connection may execute this (clients must never
-- be able to forge org_id / role / department).
REVOKE ALL ON FUNCTION public.search_document_chunks(vector, uuid, text, text, integer, double precision) FROM PUBLIC;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT EXECUTE ON FUNCTION public.search_document_chunks(vector, uuid, text, text, integer, double precision) TO service_role;
    END IF;
END $$;
