# Catalog API

All paths below use the gateway prefix `/api/v1/catalog`. DTOs are defined in
`backend/catalog_service/app/schemas/domain.py`. Errors use `{detail, code}`.

| Method | Path | Access | Request / response |
|---|---|---|---|
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

Draft responses include `card_id` (null until assembly). The business account uses
it to resume either the saved draft or its existing card, including unpublished cards.

`POST /drafts` accepts `{ "description": "...", "locale": "kk" }`. Supported locales
are exactly `ru` (Russian), `kk` (Kazakh), and `en` (English); omitted `locale` defaults
to `ru` for older clients. Unsupported locales and explicit null return HTTP 422
with a validation error for `body.locale`. Both draft GET endpoints and POST responses
include the persisted `locale`. It is fixed at creation; question generation uses
this value, not Accept-Language or the current UI language. Descriptions, saved
questions and answers are never automatically translated or replaced.

On this baseline, catalog startup runs the additive `migrate_draft_locale` upgrade
after `create_all`: old drafts receive `ru`, existing content and relations stay
unchanged, and repeated runs are safe. The new column has a server default, NOT NULL
and a `ru/kk/en` CHECK constraint. This is a narrow T-17 compatibility upgrade, not
the versioned migration system planned in T-15. When T-15 lands, call
`upgrade_draft_locale(connection)` from its next revision and remove the startup
hook in the same integration change. Apply upgrades with one service instance;
back up the database first. SQLite migration is covered by tests; PostgreSQL runtime
verification remains part of the T-15 integration. No database reset is required.

Question generation calls `ai_service` with the user's access token. The AI receives
the original draft as data and instructions to return at least three questions
about missing fields. Invalid JSON/fields/positions produce `502 ai_invalid_response`;
network or upstream errors produce `503 ai_unavailable`. The draft remains saved for
retry. Existing saved questions are returned without replacement, preserving answers.

Card assembly copies the original description into `context` and supplied answers
into their corresponding fields. Explicit request fields override those values.
Missing fields stay empty; no factual content is invented. The client supplies a title.
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

Existing cards receive version 1 through the additive `migrate_card_version`
startup upgrade. It preserves content, ratings and publication and is idempotent.
Back up the database and run upgrades with a single service instance. T-15 is not
available on this baseline: integrate `upgrade_card_version(connection)` into a
versioned revision when it lands, removing the startup hook in that same change.
SQLite migrations and concurrent requests are tested. PostgreSQL runtime validation
and the final T-15 migration integration remain outstanding.

Proposals require `team_id` (UUID), `idea`, `plan`, and an optional HTTP(S)
`prototype_url`. Teams have no separate membership system in this MVP: `team_id`
is supplied by the student; `user_id` is always taken from the verified token.
Decisions accept an explicit `selected_proposal_ids` array, including an empty array
to choose nobody. Every selected proposal must belong to the same task. Decisions
are recorded only following the owner's request; there is no automatic selection.
