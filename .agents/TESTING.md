# Backend Testing Standards — Building Stage

Backend tests are maintained in the centralized `tests/` directory:
```text
tests/
├── unit/
├── integration/
├── ai/
└── conftest.py
```

## Core Rules
1. **Unit tests:** Test isolated business logic, services, utilities, validation, security logic, and state transformations.
2. **Integration tests:** Test APIs, database behavior, external integrations, authentication/authorization, and multi-tenancy.
3. Security-sensitive behavior must have tests.
4. Multi-tenant boundaries must be tested to prevent cross-organization data access.
5. External integrations such as Slack must test validation, failures, retries, and duplicate events.
6. AI behavior should have evaluation tests/datasets for important classification, summarization, and decision-making behavior.
7. Do not test trivial code merely for coverage.
8. Every important new backend behavior should have an appropriate test.
9. When modifying existing behavior, update the existing tests or add regression tests where necessary.
10. Tests must verify expected behavior and failure behavior.
11. Prefer deterministic tests; mock external services where appropriate.
12. AI-generated backend code must not be considered correct until relevant tests, type/static checks, and linting pass.
13. Do not modify a test simply to make incorrect implementation pass. Tests represent the intended behavior.
