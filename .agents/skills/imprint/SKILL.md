---
name: imprint
description: After building any API endpoint or HTTP model in the AI Executive OS backend, extract the contract/response patterns that matter for consistency and save them to api-registry.md. So every endpoint built after this one matches what came before.
---

API consistency does not happen by accident. Each AI-built endpoint is built in isolation and the agent does not remember what it built three sessions ago — so error shapes drift, `response_model`s go missing, docstrings vanish, and the frontend breaks. This skill fixes that. Run it after building any endpoint or HTTP model so the external contract stays consistent.

For a backend, the "UI" is the **HTTP contract** — what the frontend consumes. That is what this skill captures.

## Project Grounding — this backend's contract system

- **HTTP models** live in `app/models/http/`: `schemas.py` (request/response Pydantic), `errors.py` (error shapes -> `ApiErrorResponse`), `responses.py` (`STANDARD_ERROR_RESPONSES`), `stream.py` (typed SSE events), `enums.py` (Literal types).
- **Every finished route** declares `response_model=<SomeModel>` and, where errors are possible, `responses=STANDARD_ERROR_RESPONSES`.
- **Every failure** returns `ApiErrorResponse` via handlers registered in `app/core/exception_handlers.py`.
- **Streaming** uses TypedDict events from `app/models/http/stream.py` (token / error / done).
- The **schema mirror** is the contract with the frontend (`src/common/types/http/` maps 1:1). Changing a field here is a breaking change for the frontend.

**Register at `api-registry.md` in the project root.**

## How to Invoke

- `/imprint` — capture from the most recently built endpoint(s)/model(s)
- `/imprint [filepath]` — capture from a specific file
- `/imprint audit` — scan the whole API surface and establish a baseline

Run `/imprint audit` before first use on this existing codebase (there is already a lot of API surface), then `/imprint` going forward.

## Step 1 — Find What Was Just Built

If a filepath was given, read it. Otherwise identify the router/`app/models/http/` file most recently created or modified this session. If unclear, ask which endpoint/model to capture.

## Step 2 — Extract What Matters for Consistency

Read the endpoint/model. Extract only the contract properties that affect cross-API consistency:

- **Response model** — is a typed `response_model` declared? Which `app/models/http/schemas.py` model?
- **Error shape** — does it use `responses=STANDARD_ERROR_RESPONSES` and return `ApiErrorResponse`? Are all failures handled (no silent `except: pass`)?
- **Auth + org** — which `security.py` deps (`get_current_user`, `tenant_org_id`, `require_admin`)? Any feature-flag gate?
- **Tag / path** — consistent router tag and `/api/v1` prefix under `app/api/v1/routers/`.
- **Naming** — Pydantic field names/types consistent with `enums.py` Literal values; snake_case fields matching the frontend mirror.
- **Docstring** — one-sentence module purpose (the repo standard).
- **Streaming** — if SSE, typed token/error/done events from `app/models/http/stream.py`.

Do not capture handler internals that are pure implementation (query specifics, per-use branching) — only what keeps the API contract consistent.

## Step 3 — Write to api-registry.md

Open `api-registry.md` (create if missing). Append an entry for each captured endpoint/model — never overwrite existing entries. Record the canonical pattern (e.g. `Protected route → response_model + STANDARD_ERROR_RESPONSES + get_current_user + tenant_org_id` as protocol) and note any endpoint that deviates from the established contract.

## Audit Mode (`/imprint audit`)

Establish a clean baseline before further capturing. Scan every router under `app/api/v1/routers/` and every model under `app/models/http/`, read each, and report conflicts:

```markdown
## API Consistency Audit

### Conflicts found
- response_model missing / inconsistent
- error responses not using STANDARD_ERROR_RESPONSES / ApiErrorResponse
- missing auth or org-scope deps
- naming / Literal mismatches; schema-mirror drift with the frontend

### Deviations found
[every endpoint/file that deviates, with recommendation]

### Recommended baseline
[the canonical contract pattern every endpoint should follow]
```

Present the audit and wait for confirmation — do not fix anything and do not update `api-registry.md` yet. After confirmation, write the agreed baseline to `api-registry.md` labelled `## Baseline — Established [date]`, then list every endpoint that deviates so the developer can fix them systematically.

## Hard Rules — Must Never Violate

1. **Reuse before capturing** — check that a schema/route/error pattern already exists in `app/models/http/` or an existing router before creating a new one; never duplicate.
2. Every route declares `response_model` and uses `STANDARD_ERROR_RESPONSES` / `ApiErrorResponse`.
3. Schema-mirror discipline — any change to `app/models/http/*` is a change to the frontend contract; it must be reflected in the frontend's `src/common/types/http/` mirror and checked, not silently drifted.
4. No new HTTP schema that duplicates or renames an existing one — extend `schemas.py` (`errors.py` / `stream.py` / `enums.py`).
5. Keep the `app/models/http/` layer the single home of request/response types — never define them inline in a router or service.

