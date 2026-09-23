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
| POST | `/tasks/{id}/confirm` | owner | `{confirmed: true}` → `TaskCardRead` |
| POST | `/tasks/{id}/publish` | owner | confirmed card → `CatalogEntryRead` |
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

Proposals require `team_id` (UUID), `idea`, `plan`, and an optional HTTP(S)
`prototype_url`. Teams have no separate membership system in this MVP: `team_id`
is supplied by the student; `user_id` is always taken from the verified token.
Decisions accept an explicit `selected_proposal_ids` array, including an empty array
to choose nobody. Every selected proposal must belong to the same task. Decisions
are recorded only following the owner's request; there is no automatic selection.
