# Catalog API

All paths below use the gateway prefix `/api/v1/catalog`. DTOs are defined in
`backend/catalog_service/app/schemas/domain.py`. Application errors use `{detail, code}`;
request validation errors use FastAPI's HTTP 422 response with a `detail` array.

| Method | Path | Access | Request / response |
|---|---|---|---|
| GET | `/health` | authenticated | readiness with database check, 200/503 |
| POST | `/drafts` | business | `TaskDraftCreate` → `TaskDraftRead`, 201 |
| GET | `/drafts` | business | own `TaskDraftRead[]` |
| GET | `/drafts/{id}` | owner | `TaskDraftRead` |
| POST | `/drafts/{id}/questions` | owner | generate or return saved `ClarifyingQuestionRead[]` |
| GET | `/drafts/{id}/questions` | owner | saved questions |
| PATCH | `/questions/{id}` | owner | `{answer}` → `ClarifyingQuestionRead` |
| POST | `/drafts/{id}/card` | owner | `TaskCardCreate` → `TaskCardRead`, 201 |
| GET | `/tasks/{id}` | public when published; otherwise owner | `TaskCardRead` |
| PATCH | `/tasks/{id}` | owner | `TaskCardUpdate` → `TaskCardRead` |
| POST | `/tasks/{id}/confirm` | owner | `{confirmed: true, expected_version}` → `TaskCardRead` |
| POST | `/tasks/{id}/publish` | owner | `{expected_version}` → `CatalogEntryRead` |
| GET | root path | public | `{items: CatalogEntryRead[], total, limit, offset}` |
| POST | `/tasks/{id}/proposals` | student | `ProposalCreate` → `ProposalRead`, 201 |
| GET | `/tasks/{id}/proposals` | owner | `ProposalRead[]` |
| POST | `/tasks/{id}/decisions` | owner | `SelectionDecisionCreate` → `SelectionDecisionRead`, 201 |
| GET | `/tasks/{id}/decisions` | owner | decision history, newest first |

The catalog accepts `limit` (1–200, default 50) and `offset` (default 0), sorted by
descending rating, then publication time, then task ID for stable pagination.
There is no minimum score for publication or proposals.

Every non-null `TaskCardRead.rating` includes the seven component scores, `total`
(0–100), and a stable, language-independent `readiness_code`:

| Total | `readiness_code` | Legacy `readiness` |
|---|---|---|
| 0–39 | `draft` | `черновик` |
| 40–69 | `working` | `рабочая` |
| 70–89 | `ready` | `готовая` |
| 90–100 | `priority` | `приоритетная` |

These fields appear in card responses and cards nested in catalog entries.
`readiness` retains its existing Russian values for older clients. New clients
should use `readiness_code` as the translation key; locale dictionary integration
follows in T-20 after the i18n infrastructure in T-19. Both fields are computed
from the same total and cannot be supplied in create/update requests. Component
weights remain 20/20/15/15/10/10/10; no database migration is needed.

Draft responses include `card_id` (null until assembly). The business account uses
it to resume either the saved draft or its existing card, including unpublished cards.

`POST /drafts` accepts `{ "description": "..." }`. Questions use the language of
that description, independent of the interface and Accept-Language. The optional
legacy `locale` (ru/kk/en) is accepted but does not override detection. Responses
retain an inferred `locale` for compatibility with the three offline dictionaries.
AI detects the source language independently, including other languages. Offline
detection is best-effort for Russian, Kazakh and English; short or ambiguous text
may be misclassified. Saved questions and answers are never replaced on reopening.

Catalog startup applies Alembic revisions before accepting requests. Revision
`0002_locale_version` adds draft locale and card version after the frozen
`0001_catalog` baseline. Old drafts receive `ru` and old cards receive version 1;
existing content and relations stay unchanged. Repeated upgrades are safe. The
locale column has a server default, NOT NULL and a `ru/kk/en` CHECK constraint.
Back up the database before upgrading. SQLite upgrades are covered by tests;
PostgreSQL tests require `CATALOG_TEST_POSTGRES_URL`. No database reset is required.

Question generation calls `ai_service` with the user's access token. The AI receives
the original draft as data and instructions to return at least three questions
about missing fields. If AI is unavailable, times out, or returns invalid questions,
the catalog saves six standard questions in the language inferred from the description and returns HTTP 200.
These ask about structured fields other than the original context; no answers or
facts are invented. The failure code is logged without provider bodies or credentials.
Existing saved questions are returned without replacement, preserving answers.

Card assembly copies the original description into `context` and supplied answers
into their corresponding fields. Explicit request fields override those values.
Missing fields stay empty; no factual content is invented. The client supplies a title.
The API permits assembly without generating questions or supplying answers; the
three-question minimum applies to generation results, not as a publication gate.
Human confirmation is still required before publication.
A draft has at most one card. Editing a card recomputes all seven rating components,
clears confirmation and removes the publication until the business confirms and
publishes the edited content again. Existing proposals and decision history remain.

## Concurrent card changes (T-18)

Card responses (including cards inside catalog entries) include `version`, starting
at 1. PATCH, confirmation and publication require a positive JSON integer
`expected_version` from the last card the user reviewed. Example PATCH:
`{ "expected_version": 3, "data": "Updated materials" }`.
Each successful operation increments the version once, including empty PATCH and
repeat publication. The client must use the returned card's version for its next
operation; publication returns it in `task.version`.

The database checks ownership and version in one conditional UPDATE, holding the
write lock until all changes commit. Card content, rating, confirmation reset,
catalog removal and the version change commit or roll back together. A stale
request returns HTTP 409 with
`{ "detail": "Card changed. Load the latest version before saving, confirming or publishing.", "code": "catalog_version_conflict" }`.
It must not be automatically retried with a fresh version. GET the current card,
let the user compare changes and explicitly submit the chosen content.
An unconfirmed card still cannot be published (400); this failure does not consume
a version. Missing cards return 404, foreign cards/business-role violations 403.

Compatibility: reads gain an additive field, but these three write operations
deliberately require a client update. Missing/null/non-integer/nonpositive versions
return 422. Publish now requires a JSON body. There is no unprotected legacy write
path. Deploy backend and frontend together; update external clients and refresh
old tabs. The repository smoke script and integration tests use the new contract.

Existing cards receive version 1 through Alembic revision `0002_locale_version`,
which invokes `upgrade_card_version(connection)`. Catalog startup runs Alembic
upgrade to `head`; there is no separate card-version startup hook. Content,
ratings and publication are preserved. Back up the database before upgrading.
Run SQLite upgrades with a single service instance; PostgreSQL migrations use a
transactional advisory lock. PostgreSQL migration tests require
`CATALOG_TEST_POSTGRES_URL`; a SQLite-only run does not validate PostgreSQL.

Proposals require `team_id` (UUID), `idea`, `plan`, and an optional HTTP(S)
`prototype_url`. Teams have no separate membership system in this MVP: `team_id`
is supplied by the student; `user_id` is always taken from the verified token.
Decisions accept an explicit `selected_proposal_ids` array, including an empty array
to choose nobody. Every selected proposal must belong to the same task. Decisions
are recorded only following the owner's request; there is no automatic selection.
