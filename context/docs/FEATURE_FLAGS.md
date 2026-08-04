# Feature Flag System

**Purpose:** Turn parts of the application on or off without changing code. One JSON file controls the **web UI** and the **API**.

**Config file:** `backend/config/features.json`

---

## 1. File format (for professors / reviewers)

```json
{
  "ai_provider": "gemini",
  "ai_models": {
    "gemini": {
      "name": "Google Gemini",
      "chat_model": "gemini-2.0-flash",
      "grading_model": "gemini-2.0-flash"
    },
    "groq": { "name": "Groq", "chat_model": "...", "grading_model": "..." },
    "openai": { "name": "OpenAI (ChatGPT)", "chat_model": "...", "grading_model": "..." },
    "anthropic": { "name": "Anthropic (Claude)", "chat_model": "...", "grading_model": "..." }
  },
  "features": {
    "DOCUMENT_UPLOAD_ENABLED": true,
    "KNOWLEDGE_AGENT_ENABLED": true,
    "ANALYTICS_DASHBOARD_ENABLED": true
  }
}
```

| Section | Type | Meaning |
|---------|------|---------|
| `ai_provider` | **string** (one value) | Which AI vendor is active: `gemini`, `groq`, `openai`, or `anthropic` |
| `ai_models` | object | Display names and model IDs per vendor (not feature on/off) |
| `features` | object of **boolean** | `true` = show feature + allow API; `false` = hide UI + block API |

---

## 2. How it works (simple flow)

```mermaid
flowchart LR
  JSON[features.json]
  API[FastAPI backend]
  UI[Next.js frontend]

  JSON --> API
  API -->|GET /api/v1/config/features| UI
  JSON -->|env override| API
```

1. Developer edits `features.json` (or sets env vars).
2. Backend reads flags → enables or disables routes (e.g. upload returns 403 if off).
3. Frontend calls `GET /api/v1/config/features` → hides menu items and forms when `false`.

---

## 3. Examples

### Hide PDF upload

In `features.json`:

```json
"DOCUMENT_UPLOAD_ENABLED": false
```

| Layer | Behavior |
|-------|----------|
| UI | Upload button and document library upload UI hidden |
| API | `POST /api/v1/ingest` returns disabled response |

### Switch AI to Groq

```json
"ai_provider": "groq"
```

Add to `.env`: `GROQ_API_KEY=...`

### Switch AI to OpenAI (paid client)

```json
"ai_provider": "openai"
```

Add to `.env`: `OPENAI_API_KEY=sk-...`

---

## 4. Optional environment overrides

Without editing JSON, you can override in `backend/.env`:

```env
LLM_PROVIDER=gemini
FEATURE_DOCUMENT_UPLOAD_ENABLED=false
```

Env wins over JSON defaults.

---

## 5. Code usage (minimal)

**Backend** (`app/core/feature_flags.py`):

```python
from app.core.feature_flags import flags

if not flags.DOCUMENT_UPLOAD_ENABLED:
    raise HTTPException(403, "Document upload is disabled")
```

**Frontend**:

```tsx
import { useFeature } from "@/components/providers/FeatureFlagsProvider";

const showUpload = useFeature("DOCUMENT_UPLOAD_ENABLED");
if (!showUpload) return null;
```

---

## 6. Live values

With the API running: **http://localhost:8000/api/v1/config/features**

Example response:

```json
{
  "ai_provider": "gemini",
  "ai_model_name": "Google Gemini",
  "ai_chat_model": "gemini-2.0-flash",
  "features": {
    "DOCUMENT_UPLOAD_ENABLED": true,
    "KNOWLEDGE_AGENT_ENABLED": true
  }
}
```

---

## 7. Adding a new feature later

1. Add `"MY_NEW_FEATURE_ENABLED": true` under `features` in `features.json`.
2. Add a property on `FeatureFlags` in `backend/app/core/feature_flags.py`.
3. Guard the API route with `flags.MY_NEW_FEATURE_ENABLED`.
4. Add the name to `frontend/src/config/features.config.ts` (`FeatureName` type).
5. Use `useFeature("MY_NEW_FEATURE_ENABLED")` in the component.

---

## 8. Feature list (current)

| Flag | When `true` | When `false` |
|------|-------------|--------------|
| `DOCUMENT_UPLOAD_ENABLED` | PDF upload UI + ingest API | Hidden + blocked |
| `KNOWLEDGE_AGENT_ENABLED` | Chat / RAG UI + query API | Hidden + blocked |
| `ANALYTICS_DASHBOARD_ENABLED` | Dashboard charts + analytics API | Hidden + blocked |
| `PROJECT_AGENT_ENABLED` | Tickets UI + ticket API | Hidden + blocked |
| `SLACK_WEBHOOK_ENABLED` | Slack webhook processing | Webhook rejected |
| `EMAIL_WEBHOOK_ENABLED` | Email webhook processing | Webhook rejected |
| `JIRA_INTEGRATION_ENABLED` | Jira sync in project agent | Skipped |
| `WORKLOAD_BALANCING_ENABLED` | Auto-assign by workload | Skipped |
| `AUDIT_LOG_ENABLED` | Activity log writes | Skipped |
| `RAG_CACHE_ENABLED` | Redis answer cache | Cache off |
| `MULTI_TENANT_ENABLED` | Org isolation on API | Relaxed dev mode |

**AI (single string, not boolean):** `ai_provider` → `gemini` | `groq` | `openai` | `anthropic`
