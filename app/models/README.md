# `app/models` layout

| Folder | Purpose | Examples |
|--------|---------|----------|
| **`db/`** | SQLAlchemy ORM | `tables.py` — `User`, `Document`, `Ticket` |
| **`http/`** | API / OpenAPI contracts | `schemas.py`, `errors.py`, `enums.py`, `responses.py` |
| **`internal/`** | Pipeline types (not in OpenAPI) | `domain.py`, `coerce.py` |

## Naming

- `http/errors.py` — `ApiErrorResponse` (not `api_errors.py`)
- `http/stream.py` — SSE events (not `stream_events.py`)
- `http/responses.py` — OpenAPI error docs for `/docs` (not OpenAI)
- `http/slack.py` — Slack webhook payloads
- `internal/coerce.py` — narrow DB strings to `Literal` enums

## Import examples

```python
from app.models.db.tables import Document, User
from app.models.http.schemas import QueryResponse
from app.models.http.errors import ApiErrorResponse
from app.models.http.responses import STANDARD_ERROR_RESPONSES
from app.models.internal.domain import RagChunkItem
from app.models.internal.coerce import as_document_status
```
