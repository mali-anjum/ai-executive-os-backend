# Product Strategy, Market Position & Implementation Roadmap

**AI Executive OS & SOP Automator**


| Field            | Value                                                                                          |
| ---------------- | ---------------------------------------------------------------------------------------------- |
| Document Version | 1.0                                                                                            |
| Status           | Active reference                                                                               |
| Last Updated     | 2026-06-05                                                                                     |
| Companion docs   | [PROJECT_MASTER.md](./PROJECT_MASTER.md) (engineering), [FEATURE_FLAGS.md](./FEATURE_FLAGS.md) |


> **Purpose:** Single place to understand **what you have built**, **what the market expects**, **whether you need executive access / RBAC upgrades**, and **what to implement next** to stand out in freelancing and enterprise sales.

---

## Table of Contents

1. [Quick verdict](#1-quick-verdict)
2. [What you have achieved (current state)](#2-what-you-have-achieved-current-state)
3. [Access control: RBAC vs executive access](#3-access-control-rbac-vs-executive-access)
4. [Your features vs competitors](#4-your-features-vs-competitors)
5. [What freelance clients ask for most](#5-what-freelance-clients-ask-for-most)
6. [Dream features to stand out](#6-dream-features-to-stand-out)
7. [Recommended implementation roadmap](#7-recommended-implementation-roadmap)
8. [How to talk about this in proposals](#8-how-to-talk-about-this-in-proposals)
9. [Decision log (update as you ship)](#9-decision-log-update-as-you-ship)

---

## 1. Quick verdict


| Question                                             | Answer                                                                                                                                                                                                                 |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Do you need RBAC?**                                | **Already done** — `admin` and `employee` roles are live in backend + frontend. Keep and polish; do not rip out.                                                                                                       |
| **Do you need a separate “executive” login role?**   | **No** for MVP, demos, or most freelance clients. “Executive” in the product name means *operating system for leaders*, not a third auth role.                                                                         |
| **What should you add instead of “executive role”?** | **Executive summary dashboard** (KPI view for admins) and optionally a `**manager` role** between admin and employee.                                                                                                  |
| **When do you need more RBAC?**                      | Enterprise / compliance clients who need **document-level permissions** (HR docs vs engineering docs).                                                                                                                 |
| **Where does RBAC live in code?**                    | `backend/app/core/security.py`, route `require_admin`, frontend `RoleGuard` / `adminOnly` nav — **not** in `llm_classify_circuit.py` (that file is only a rate-limit circuit breaker for Slack ticket classification). |


```
Current state:     ✅ Basic RBAC (admin/employee) — enough for demo + most freelance clients
                   ❌ Executive role — NOT needed as a separate login
                   ❌ Document-level RBAC — skip unless client is enterprise/compliance

Best next RBAC step:  manager role + executive KPI panel (not a new auth system)

Best stand-out bets:  1) Confidence/escalation  2) Executive summary metrics
                      3) Slack in-channel Q&A     4) Unanswered-questions report
```

---

## 2. What you have achieved (current state)

Use this section to track **shipped capabilities** vs **gaps**. Engineering detail lives in [PROJECT_MASTER.md](./PROJECT_MASTER.md).

### 2.1 Two-agent platform (core differentiator)


| Agent                            | Status | What it does                                                                      |
| -------------------------------- | ------ | --------------------------------------------------------------------------------- |
| **Knowledge Agent (RAG)**        | ✅ Done | Upload SOPs/PDFs → chunk → embed → pgvector → chat with citations                 |
| **Project Agent (Event Router)** | ✅ Done | Slack + email webhooks → classify intent/priority/dept → ticket → Jira + assignee |


Most freelance RAG projects are **chat-only**. You already have **knowledge + operations routing** in one monorepo — lead with that in proposals.

### 2.2 Knowledge Agent — shipped features


| Feature                             | Status | Implementation notes                                |
| ----------------------------------- | ------ | --------------------------------------------------- |
| Document upload (PDF/DOCX/MD)       | ✅      | Admin-only; Celery async ingest                     |
| LangGraph RAG pipeline              | ✅      | retrieve → rerank → grade → generate → cite         |
| Cohere rerank + heuristic fallback  | ✅      | Quality layer above vector search                   |
| Relevance grading (drop low scores) | ✅      | Reduces hallucination risk                          |
| Citations with chunk preview        | ✅      | Document name, page, source text                    |
| SSE streaming (`/query/stream`)     | ✅      | Token stream + citations on `done`                  |
| Query logging + latency             | ✅      | `queries` table, analytics input                    |
| Redis RAG cache (1h TTL)            | ✅      | `RAG_CACHE_ENABLED` flag                            |
| Multi-tenant `org_id` isolation     | ✅      | All DB queries scoped by org                        |
| Document delete + cascade           | ✅      | Admin-only                                          |
| Multi-LLM provider                  | ✅      | OpenAI, Anthropic, Gemini, Groq via `features.json` |


### 2.3 Project Agent — shipped features


| Feature                                 | Status | Implementation notes                                     |
| --------------------------------------- | ------ | -------------------------------------------------------- |
| Slack Events webhook (HMAC)             | ✅      | `POST /api/v1/webhook/slack`                             |
| Email webhook (SendGrid inbound)        | ✅      | Celery → Project Agent                                   |
| Intent / priority / department classify | ✅      | LLM JSON + heuristic fallback                            |
| LLM classify circuit breaker            | ✅      | `llm_classify_circuit.py` — skips API on 429, uses rules |
| Ticket feed UI + API                    | ✅      | Org-scoped, polling                                      |
| Assignee mapping + round-robin          | ✅      | Per department                                           |
| Jira REST v3 integration                | ✅      | Create/update issues, encrypted tokens                   |
| Workload balancing                      | ✅      | Lowest open Jira issues per assignee                     |
| SendGrid email fallback                 | ✅      | When Slack DM fails                                      |
| Audit / activity logs                   | ✅      | Create, assign, Jira sync events                         |


### 2.4 Platform & production hardening


| Feature                           | Status | Notes                                      |
| --------------------------------- | ------ | ------------------------------------------ |
| Supabase Auth (JWT)               | ✅      | `user_metadata.role`, `org_id`             |
| Basic RBAC (`admin` | `employee`) | ✅      | See §3                                     |
| Admin analytics dashboard         | ✅      | Recharts — queries, latency, top questions |
| Feature flags (UI + API)          | ✅      | `backend/config/features.json`             |
| Rate limits                       | ✅      | 60 queries/min user, 10 uploads/hour org   |
| Sentry                            | ✅      | FastAPI + Next.js                          |
| CSV export                        | ✅      | Queries + tickets                          |
| CI (GitHub Actions)               | ✅      |                                            |
| Production Docker                 | ✅      | `Dockerfile.prod`, compose prod            |
| Security audit doc                | ✅      | [SECURITY_AUDIT.md](./SECURITY_AUDIT.md)   |


### 2.5 Frontend experience by role


| Surface                    | Admin                             | Employee                   |
| -------------------------- | --------------------------------- | -------------------------- |
| Command Center (full)      | ✅ Attention, AI status, analytics | ✅ Welcome + limited panels |
| AI Assistant (chat)        | ✅                                 | ✅                          |
| Knowledge (upload/library) | ✅                                 | ❌ Hidden + API blocked     |
| Tasks (tickets)            | ✅                                 | ✅                          |
| Analytics charts           | ✅                                 | ❌                          |


**Code references:**

- Backend admin gate: `backend/app/core/security.py` → `require_admin`
- Frontend role guard: `frontend/src/common/organisms/RoleGuard.tsx`
- Nav filtering: `frontend/src/common/lib/navigation.ts` → `adminOnly`
- Employee vs admin dashboard: `frontend/src/dashboard/organisms/CommandCenter.tsx`

### 2.6 Tier 1–3 feature status (updated 2026-06-05)


| Tier | Feature                                   | Status                                                  |
| ---- | ----------------------------------------- | ------------------------------------------------------- |
| 1    | Grounded RAG + citations                  | ✅                                                       |
| 1    | Document upload                           | ✅                                                       |
| 1    | Admin dashboard                           | ✅                                                       |
| 1    | Login + roles (admin/employee)            | ✅                                                       |
| 1    | Confidence + escalation                   | ✅ Backend + chat UI                                     |
| 1    | Web UI                                    | ✅                                                       |
| 2    | Slack in-channel Q&A                      | ✅ `SLACK_QA_ENABLED` + `SlackQaService`                 |
| 2    | Jira integration                          | ✅                                                       |
| 2    | SSE streaming                             | ✅                                                       |
| 2    | Multi-tenant                              | ✅                                                       |
| 2    | Usage analytics                           | ✅                                                       |
| 2    | Security (rate limits, audit, encryption) | ✅                                                       |
| 3    | Document-level RBAC                       | ✅ Upload scope + PATCH access + retrieval filter        |
| 3    | SSO                                       | ✅ Google + Microsoft OAuth via Supabase (`SSO_ENABLED`) |
| 3    | Notion / Google Drive sync                | ✅ Connectors panel + Celery re-sync                     |
| 3    | Evaluation dashboard                      | ✅ Metrics + chat thumbs up/down feedback                |
| 3    | Human approval before Jira                | ✅ Pending tickets + admin approve/reject                |


### 2.7 Remaining gaps (optional follow-ons)


| Item                             | Notes                                                  |
| -------------------------------- | ------------------------------------------------------ |
| `manager` role                   | Schema doc mentions it; code still admin/employee only |
| SSO SCIM / enterprise IdP groups | OAuth only — no group→role mapping                     |
| Scheduled connector cron         | Celery task exists; wire beat schedule in deploy       |
| Executive KPI summary card       | Analytics exist; not a separate exec-only view         |


---

## 3. Access control: RBAC vs executive access

### 3.1 What you have today (basic RBAC)

**Roles:** `admin` | `employee` (defined in `backend/app/models/http/enums.py`)


| Permission                | Admin | Employee     |
| ------------------------- | ----- | ------------ |
| Chat / RAG query          | ✅     | ✅            |
| View tickets              | ✅     | ✅            |
| Upload / delete documents | ✅     | ❌            |
| Analytics dashboard API   | ✅     | ❌            |
| Knowledge nav + screens   | ✅     | ❌ (redirect) |


**Auth flow:** Supabase JWT → `AuthContext` → `ensure_user_row` → route dependencies.

**Dev headers (development only):** `X-Org-Id`, `X-User-Id`, `X-User-Role`

### 3.2 Do you need to add more RBAC?


| Scenario                           | Recommendation                                                                                    |
| ---------------------------------- | ------------------------------------------------------------------------------------------------- |
| Portfolio / Upwork / Fiverr demo   | **No** — current 2-role RBAC is sufficient. Mention “expandable to department-level.”             |
| SMB internal tool (one company)    | **Optional** — add `manager` if they want team-lead ticket view without full admin                |
| Enterprise HR/legal/compliance     | **Yes** — document-level RBAC + retrieval-time permission filter + audit on every chunk retrieved |
| “Executive access” as a login tier | **No** — build an **executive dashboard view** instead                                            |


### 3.3 What “executive access” usually means in sales calls

Clients rarely mean a fourth OAuth role. They usually mean:

1. **Executive dashboard** — ROI metrics: queries automated, hours saved, ticket volume, top knowledge gaps
2. **Manager view** — department tickets, approve routing, team analytics (no upload/delete)
3. **Restricted sensitive docs** — HR/legal visible only to certain roles (document-level RBAC)

### 3.4 RBAC architecture levels (industry standard)


| Level                      | Description                              | Your status       |
| -------------------------- | ---------------------------------------- | ----------------- |
| **L1 — App roles**         | admin vs employee UI/API gates           | ✅ Implemented     |
| **L2 — Tenant isolation**  | `org_id` on every query                  | ✅ Implemented     |
| **L3 — Document-level**    | Per-doc or per-folder ACL on retrieval   | ❌ Not implemented |
| **L4 — Source-synced ACL** | Permissions synced from Drive/Confluence | ❌ Not implemented |
| **L5 — Enterprise IdP**    | SSO, SCIM, group → role mapping          | ❌ Not implemented |


**Do not put authorization in `llm_classify_circuit.py`.** That module only opens/closes LLM calls for Slack classification when the provider returns 429. RBAC belongs in `security.py`, routers, and (for L3+) vector retrieval filters.

### 3.5 Minimum viable RBAC upgrade (recommended next step)

If you want one RBAC improvement with high demo value and low risk:

1. Add `**manager` role** to `UserRole` and `as_user_role`
2. **Manager permissions:** view all tickets, view analytics (read-only), no upload/delete/settings
3. **Admin permissions:** unchanged (full control)
4. **Employee permissions:** unchanged (chat + own tickets view)
5. Add **Executive Summary** card on admin/manager dashboard: total queries, avg latency, open tickets, “top unanswered themes” (when you ship that feature)

---

## 4. Your features vs competitors

You are **not** competing with Glean on connector count. You **can** compete on: **focused SOP automation + ticket routing + citations + fast deploy**.

### 4.1 Where you are strong (vs typical freelance builds)


| Your feature                                          | Market position               |
| ----------------------------------------------------- | ----------------------------- |
| RAG with **citations** + SSE streaming                | Table stakes — you have it    |
| LangGraph pipeline (retrieve → rerank → grade → cite) | Above average                 |
| **Two agents** (Knowledge + Project routing)          | Strong differentiator         |
| Slack + email → classify → Jira ticket                | High value; often extra scope |
| Multi-tenant `org_id` isolation                       | Expected for B2B              |
| Admin analytics + query logging                       | Expected                      |
| Feature flags, rate limits, Redis cache               | Production maturity signal    |
| Circuit breaker on classify LLM                       | Uncommon — good talking point |
| Workload-aware assignee pick                          | Uncommon in freelance builds  |


### 4.2 What enterprise leaders have that you don’t (yet)

References: Glean, GenOS, Gewan Fahim, Vellum, Cerbos/Pinecone RAG security guides (2025–2026).


| Competitor capability                | Examples                                               |
| ------------------------------------ | ------------------------------------------------------ |
| **100+ source connectors**           | SharePoint, Confluence, Notion, Google Drive auto-sync |
| **Permissions from source systems**  | ACLs synced from Drive/Confluence into vector metadata |
| **SSO / SCIM**                       | Azure AD, Okta groups → roles                          |
| **Agent orchestration**              | Multi-agent workflows, human approval gates            |
| **Personalized assistant**           | Per-user memory, personal graph                        |
| **Deep research mode**               | Multi-step research reports                            |
| **Compliance packaging**             | SOC 2, DLP, PII redaction, SIEM export                 |
| **No-code agent builder**            | Business users create agents                           |
| **MCP / embeddable Chat API**        | Plug into Cursor, Teams, custom apps                   |
| **Document-level RBAC on retrieval** | Pre-filter vectors by user permissions                 |


### 4.3 Positioning matrix


| Buyer                      | Lead with                                                   | De-emphasize                        |
| -------------------------- | ----------------------------------------------------------- | ----------------------------------- |
| **Freelance / SMB client** | Citations, Slack→Jira, dual agents, fast setup              | SSO, 100 connectors                 |
| **Mid-market ops team**    | Ticket routing, analytics, audit log, multi-tenant          | Personal graph, deep research       |
| **Enterprise compliance**  | Security audit, tenant isolation, roadmap to doc-level RBAC | “We match Glean connectors day one” |


---

## 5. What freelance clients ask for most

Based on 2025–2026 project brief templates, RFP guides, and production RAG case studies (ZTABS, KUMO, DEV Community RAG builds, enterprise RAG security guides).

### 5.1 Tier 1 — Must have or they won’t pay


| #   | Requirement                                    | Your status           |
| --- | ---------------------------------------------- | --------------------- |
| 1   | Answers **only from their documents**          | ✅ RAG + grading       |
| 2   | **Clickable citations** to source              | ✅                     |
| 3   | **Document upload**                            | ✅ Admin upload        |
| 4   | **Admin dashboard**                            | ✅ Analytics           |
| 5   | **Login + basic roles**                        | ✅ admin/employee      |
| 6   | **“I don’t know” / low-confidence escalation** | ❌ Gap — high priority |
| 7   | Works in **simple web UI** or widget           | ✅ Next.js app         |


**You cover 6/7 Tier 1 items.** Escalation/confidence is the main gap.

### 5.2 Tier 2 — Wins the contract over another freelancer


| #   | Requirement                                     | Your status                           |
| --- | ----------------------------------------------- | ------------------------------------- |
| 8   | Slack or Teams integration                      | ✅ Slack webhook; ❌ in-channel Q&A bot |
| 9   | CRM / helpdesk (Jira, Zendesk, HubSpot)         | ✅ Jira                                |
| 10  | Streaming responses                             | ✅ SSE                                 |
| 11  | Multi-tenant / team workspaces                  | ✅                                     |
| 12  | Usage analytics                                 | ✅                                     |
| 13  | Security story (encryption, audit, rate limits) | ✅                                     |


**You cover most of Tier 2.**

### 5.3 Tier 3 — Enterprise (often scope creep)


| #   | Requirement                              | Your status |
| --- | ---------------------------------------- | ----------- |
| 14  | Document-level permissions by department | ❌           |
| 15  | SSO                                      | ❌           |
| 16  | Auto-sync Notion / Google Drive          | ❌           |
| 17  | Evaluation dashboard (accuracy %)        | ❌           |
| 18  | Human approval before AI actions         | ❌           |


Treat Tier 3 as **paid follow-on phases**, not MVP blockers.

---

## 6. Dream features to stand out

Prioritized by **impact vs effort** for freelancing and portfolio.

### 6.1 High impact, reasonable effort — **IMPLEMENTED**


| Feature                                  | Status | Where                                                                                      |
| ---------------------------------------- | ------ | ------------------------------------------------------------------------------------------ |
| **Confidence score + escalate to human** | ✅      | Chat confidence bar, auto-escalation, manual “Request human help”, `POST /query/escalate`  |
| **Executive summary dashboard**          | ✅      | `ExecutiveSummaryDashboard` on Command Center, `GET /analytics/executive-summary`          |
| `**manager` role**                       | ✅      | `admin` | `manager` | `employee`; managers get dept-scoped tickets + leadership dashboards |
| **Unanswered questions report**          | ✅      | `UnansweredQuestionsReport`, `GET /evaluation/unanswered`                                  |
| **Slack dual-mode Q&A + routing**        | ✅      | `slack_message_mode()` — questions → Q&A, `!ticket` / urgent → Project Agent               |
| **One-click demo tenant**                | ✅      | `DemoSeedCard` + `POST /demo/seed` + `pnpm run demo:seed`                                   |


### 6.2 High impact, higher effort (enterprise tier)


| Feature                               | Why it stands out                    |
| ------------------------------------- | ------------------------------------ |
| **Department-scoped document access** | HR vs engineering doc separation     |
| **Notion / Google Drive connector**   | #1 integration ask after Slack       |
| **Approval gate before Jira ticket**  | “AI suggests → manager approves”     |
| **RAG evaluation harness**            | Accuracy % with regression tests     |
| **Show sources considered**           | Transparency in UI (retrieval debug) |


### 6.3 Portfolio headline features (you already have some)


| Feature                      | Pitch line                                           |
| ---------------------------- | ---------------------------------------------------- |
| Two-agent OS                 | “Ask questions *and* auto-route work — one platform” |
| Circuit breaker + heuristics | “Keeps working when the LLM rate-limits”             |
| Citation-grade answers       | “Every answer is auditable”                          |
| Workload-aware assignment    | “Smarter than round-robin”                           |


---

## 7. Recommended implementation roadmap

### Phase A — Demo & freelance readiness (do first)


| Priority | Task                                                       | RBAC / access notes         |
| -------- | ---------------------------------------------------------- | --------------------------- |
| P0       | Confidence threshold + “I’m not sure, escalating…” in chat | No new roles                |
| P0       | Executive summary panel on dashboard (KPI cards)           | Admin + future manager      |
| P1       | `manager` role (read analytics + all tickets, no upload)   | Extend `UserRole`           |
| P1       | “Top failed / low-confidence queries” widget               | Uses existing `queries` log |
| P2       | Demo org seed script (sample SOPs + tickets)               |                             |


### Phase B — Contract winners


| Priority | Task                                                  |
| -------- | ----------------------------------------------------- |
| P1       | Slack in-channel Q&A (slash command or mention bot)   |
| P2       | Notion export or Google Drive folder sync (pick one)  |
| P2       | Human approval step before Jira create (feature flag) |


### Phase C — Enterprise (only when client pays for it)


| Priority | Task                                               |
| -------- | -------------------------------------------------- |
| P1       | Document tags + `allowed_roles` metadata on chunks |
| P1       | Pre-filter vector search by user role/department   |
| P2       | SSO via Supabase SAML / Azure AD                   |
| P3       | Evaluation harness + accuracy dashboard            |


### What NOT to build yet

- Separate `executive` login role
- Full Glean-style 100 connectors
- SpiceDB/Cerbos unless enterprise contract requires it
- Personal graph / per-user long-term memory

---

## 8. How to talk about this in proposals

### Elevator pitch

> AI Executive OS is a **two-agent internal platform**: employees get **citation-backed answers** from company SOPs, and operations get **automated ticket routing** from Slack/email to Jira with workload-aware assignment. Multi-tenant, role-based, production-hardened with analytics and audit logs.

### Honest RBAC line

> **Role-based access is implemented** (admin vs employee). Document-level permissions and SSO are on the roadmap for enterprise deployments.

### Differentiators vs “just a ChatGPT wrapper”

1. LangGraph RAG with rerank + relevance grading + citations
2. Project Agent: classify → prioritize → assign → Jira
3. Circuit breaker when LLM rate-limits (ticket path stays up)
4. Multi-tenant from day one
5. Feature flags to toggle modules per client

### Scope control (avoid creep)


| Client asks for                 | Response                                          |
| ------------------------------- | ------------------------------------------------- |
| “Executive login”               | Offer **executive dashboard** + manager role      |
| “Permissions like Google Drive” | Phase C — document-level RBAC phase               |
| “Connect our Notion”            | Phase B — priced separately                       |
| “SOC 2”                         | Security audit doc + roadmap; not self-serve cert |


---

## 9. Decision log (update as you ship)


| Date       | Decision                                                | Rationale                                                         |
| ---------- | ------------------------------------------------------- | ----------------------------------------------------------------- |
| 2026-06-05 | **No separate `executive` role**                        | Market wants KPI view, not another login; reduces auth complexity |
| 2026-06-05 | **Keep 2-role RBAC for MVP**                            | Covers freelance Tier 1; manager role is next incremental step    |
| 2026-06-05 | **Document-level RBAC = enterprise phase**              | High build cost; not needed for portfolio demos                   |
| 2026-06-05 | **Priority: confidence/escalation + exec summary**      | Biggest gap vs Tier 1 client checklist                            |
| 2026-06-05 | **Deleted duplicate `frontend/docs/PROJECT_MASTER.md`** | Single source of truth: `docs/PROJECT_MASTER.md`                  |


---

## Related documents


| Document                                 | Use when                                              |
| ---------------------------------------- | ----------------------------------------------------- |
| [PROJECT_MASTER.md](./PROJECT_MASTER.md) | Engineering: architecture, sprints, schema, LangGraph |
| [FEATURE_FLAGS.md](./FEATURE_FLAGS.md)   | Toggling modules per demo/client                      |
| [SECURITY_AUDIT.md](./SECURITY_AUDIT.md) | Pre-release security checklist                        |
| [README.md](../README.md)                | Run dev/prod, API summary                             |


