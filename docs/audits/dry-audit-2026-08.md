# DRY Audit — `todo-backend` (Django REST + MongoDB, Postgres migration in flight)

**Scope:** 147 verified findings across 10 dimensions (views, services, repositories, models, DTOs/serializers, exceptions, dual-write, auth/utils, tests, cross-cutting). Every finding below was re-checked against the files by a second agent; verifier corrections and rejections are carried through. Approximately **3,800 lines of duplicated production code** and **~1,700 lines of duplicated test code**, with overlap between findings.

This is research output. No changes have been made to the repository.

---

## 1. The shape of the problem

The duplication in this codebase is not uniform. It falls into four distinct kinds, each with a different root cause and a different fix.

### 1.1 Two of everything, because a Mongo→Postgres migration is in flight

Every entity is declared three times: as a pydantic `Document`, as a Django model, and again as a hand-written field list inside `DualWriteService._transform_<entity>_data`. Eleven entities × three declarations, plus an eleven-branch `if/elif` dispatch at `todo/services/dual_write_service.py:209-233` that re-encodes routing already present in `COLLECTION_MODEL_MAP` at `:31-43` (findings 48, 56, 84, 93).

The consequences are already load-bearing:

- `PostgresRole.permissions` (`todo/models/postgres/role.py:16`) has no counterpart on `RoleModel`, so `"permissions": data.get("permissions", {})` (`dual_write_service.py:306`) writes `{}` on every row; `RoleModel.scope`/`is_active`/`created_by`/`updated_by` have no columns and are silently dropped.
- `_sync_task_assignment_update` (`dual_write_service.py:377-390`) passes six columns — `status`, `user_mongo_id`, `team_mongo_id`, `assigned_at`, `completed_at`, `assigned_by` — that do not exist on `PostgresTaskAssignment`. It would raise `TypeError` on every call; it is never called. A third copy of the mapping rotted unnoticed.
- The entire `todo/repositories/postgres_repository.py` (304 lines, single commit `781100f`) has **zero importers**, and seven of its eleven finders name columns that do not exist (`user_mongo_id` on `PostgresWatchlist`, whose field is `user_id`; `collection_name` on `PostgresAuditLog`, which has neither).

The same migration produced a second family: the sync epilogue. `EnhancedDualWriteService()` is constructed and the same five-line "build payload → call → function-local `import logging` → warn" tail is pasted in **21 repository write paths** (findings 33, 82, 135). In `todo/repositories/user_role_repository.py` the pasted block re-imports `logging` at `:59` and `:160` even though the module already imports it at `:3` and defines a logger at `:11` — the block was pasted without anyone reading the top of the file.

Mixed id encodings in Mongo are the third artifact of the same migration. Because some documents store `task_id` as an `ObjectId` and some as a string, "try ObjectId, then try the raw string" is hand-written **17 times in four shapes** (findings 34, 44, 139), including a four-way cartesian query at `todo/repositories/user_team_details_repository.py:21-31`. The write side keeps feeding the problem: `ObjectId(user_id)` at `task_assignment_repository.py:118, :129, :188, :201, :314, :325` but a plain string at `:251, :264`, from otherwise-identical blocks.

### 1.2 A layered architecture with no shared base class in any layer

There is no base `APIView`, no shared repository behaviour beyond `get_collection`, no DTO mapper convention outside a single file, and no abstract Django model.

- **Views:** `_handle_validation_errors` is defined in **eight view classes across three files** in **five mutually incompatible shapes** (findings 1, 72, 100, 131) — while `todo/exceptions/exception_handler.py:29-45` already contains a strictly better recursive implementation, wired as the project's `EXCEPTION_HANDLER` at `todo_project/settings/base.py:102`, and already used correctly by `task.py:79`, `label.py:16`, `watchlist.py:57/89/141` and `role.py:105`.
- **Repositories:** the insert prologue (stamp timestamps → `model_dump(mode="json", by_alias=True, exclude_none=True)` → `insert_one` → assign `inserted_id`) appears in **nine create methods** (finding 40); `find_one` → model-or-`None` in five (41); `find` → list-comprehension → swallow in four (46).
- **DTOs:** `RoleDTO.from_model` (`todo/dto/role_dto.py:25-55`) is the only mapper classmethod in the codebase. `TeamModel → TeamDTO` is therefore written out field-by-field **five times in one file** (17), `TaskAssignmentModel → DTO` three times across two near-identical DTO classes (21), `LabelDTO` three times (22).
- **Models:** the `mongo_id` + sync-metadata block and its two indexes are byte-identical in **all eleven Postgres models** (49, 90, 138); the `save()` override is byte-identical in nine, truncated in a tenth, and absent from two.

### 1.3 Copy-paste-per-entity growth

New endpoints were built by copying the nearest sibling and editing the nouns. The fingerprints are unambiguous:

- `todo/views/team_creation_invite_code.py` — `diff` of `:20-26` against `:131-137` is empty, and `diff` of the call sites `:65-71` against `:180-186` is empty. Two classes, one authorization gate, pasted whole (7, 101, 147).
- `todo/services/task_service.py` — `update_task_with_assignee_from_dict` (`:370-460`) and `update_task_with_assignee` (`:462-540`) are a 90-line clone that differs only in input type (137). Their permission preamble is byte-identical at `:293-303`, `:376-386`, `:468-478`, `:544-554` — comments included (14).
- Pagination exists in three `PaginationConfig` classes, four link builders, three serializers and two hand-rolled `int(request.query_params.get(...))` sites (9, 19, 25, 60, 136).
- `AuditLogRepository.create(AuditLogModel(...))` is hand-built at **13 sites** with free-text action strings and three different id-coercion styles (20).

The tell that these are pastes rather than parallel implementations is that the *comments* travel: `# Check if user is the creator` / `# Check if user is assigned to this task` appear verbatim at all five permission-guard sites, including the one in a different layer (`todo/repositories/task_repository.py:274-279`). The trailing comment `# User ID executing the task (for team assignments)` appears on `executor_id` in both `TaskAssignmentDTO` and `TaskAssignmentResponseDTO` (65).

### 1.4 The cost is already paid: fixes land in one copy and never propagate

This is the strongest argument in the audit, and it is not hypothetical. Eleven separately verified cases:

| Fix | Landed in | Missing from |
|---|---|---|
| `e.args` guard against `IndexError` inside the `except` handler | `todo/views/task.py:350`, `exception_handler.py:250` | the other **seven** copies (`task.py:152`, `team.py:46/:89/:301`, `watchlist.py:97`, `task_service.py:656`, `watchlist_service.py:102`) |
| `ObjectId(id)` conversion before `LabelRepository.list_by_ids` (comment: `# Convert here!`) | `watchlist_service.py:142` | `task_service.py:203-214` (works only because `TaskModel.labels` is already `List[PyObjectId]`, while its own type hint says `List[str]`) |
| Batched `UserRepository.get_by_ids` replacing an N+1 | `todo/dto/update_team_dto.py:47-50` — **a class with zero importers** | `todo/dto/team_dto.py:20-24`, the live team-creation path |
| `is_active` in the uniqueness constraint (commit `e58e9ec`, "prevent sync failures … removed and added more than once") | `todo/models/postgres/user_role.py:30-36` | `todo/models/postgres/team.py:99`, still `unique_together` — and `TeamService.join_team_by_invite_code` (`team_service.py:281-299`) falls through on an inactive membership straight into an insert |
| Path-aware `source={ApiErrorSource.PATH: "user_id"}` | `exception_handler.py:195` — **an unreachable branch** | the live branch at `:176` |
| `settings.DEBUG` guard on the 500 detail | 9 of 11 copies | `views/task.py:437` (leaks `str(e)` in production), `views/watchlist.py:104` (never shows detail, even in DEBUG) |
| `status_filter` on the profile branch | `views/task.py:80-88` | the pasted-below original at `:90-99`, which is unreachable and silently took `exclude_none=True` with it (commit `3e51495`) |
| `assert_called_once_with(...)` argument checks on the remove-member audit path | `tests/unit/services/test_team_service.py:303-304` | its twin at `:278-279`, which asserts only `assert_called_once()` |

### 1.5 Defects the duplication has already produced

These are live, verified, and independent of whether any refactor happens:

1. **A misplaced `@extend_schema` decorates the pasted helper instead of the handler.** The block at `todo/views/team.py:452-468` decorates `_handle_validation_errors` at `:469`, not `delete` at `:491`. **Correction (see the completeness review, N1):** an earlier draft of this report claimed this had already dropped `DELETE /teams/{team_id}/members/{user_id}` from `schema.yaml`. That causation is wrong. `schema.yaml` was last committed in `e6c0b5e` on 2025-07-19; `RemoveTeamMemberView` was added in `6007932` on 2025-07-25, six days later. The endpoint is missing because the committed schema is stale — `urls.py` declares 31 routes and `schema.yaml` contains 19, with ten endpoints absent, nine of which have correctly-placed decorators. The misplaced decorator is a real but *latent* bug: it will manifest the next time the schema is regenerated. Treat `schema.yaml` as unreliable evidence for any endpoint added after 2025-07-19.
2. **`POST /teams` returns the team invite code.** Five sibling endpoints pop it; `TeamListView.post` (`team.py:84-86`) does not. `TeamInviteCodeView` exists solely to hand out that code behind a creator-or-POC check returning 403.
3. **`PATCH /tasks/<id>/assign` leaks raw exception text in production** (`views/task.py:437`), while `POST /task-assignments` reaching the same service does not.
4. **The `startedAt` transition is dead on one update endpoint.** `task_service.py:429` compares `validated_data.get("status") == TaskStatus.IN_PROGRESS` — an enum against the `ChoiceField` string — and two lines later at `:434` compares against `TaskStatus.DEFERRED.value` correctly.
5. **Every task update wipes `postgres_task_labels`.** `dual_write_service.py:129-130` calls `_sync_task_labels` unconditionally on updates, and `_sync_task_labels` opens with `.delete()` at `:346` — but neither task payload (`task_repository.py:226-239`, `:324-338`) contains a `labels` key.
6. **`role_id=DEFAULT_ROLE_ID` is discarded at five sites.** `UserTeamDetailsModel` (`todo/models/team.py:46-59`) has no `role_id` field; pydantic 2.10's default `extra="ignore"` drops it silently. Same mechanism drops `details={"added_member_id": member_id}` at `team_service.py:461`.
7. **`TaskAssignmentRepository.get_by_assignee_id` returns `[]` when the ObjectId form matches.** `task_assignment_repository.py:82` does `if not list(cursor):`, exhausting it before the comprehension at `:87`.
8. **User-not-found returns 500 from `UserService` and 404 from `TaskService`.** Two unrelated classes named `UserNotFoundException` (`auth_exceptions.py:40-42`, `user_exceptions.py:4-13`); `exception_handler.py:26` imports only one, and the other extends `BaseAuthException`, not `AuthException`, so it misses that branch too.
9. **`AuthErrorMessages.INVALID_TOKEN` does not exist.** `todo/middlewares/jwt_auth.py:118` raises `TokenInvalidError(AuthErrorMessages.INVALID_TOKEN)`; the constant is `TOKEN_INVALID`. The `AttributeError` is swallowed by the outer `except Exception: return False` at `jwt_auth.py:83-84`, degrading a specific 401 into a generic one.
10. **Clients receive the literal string `Authentication failed: {0}`.** `ApiErrors.AUTHENTICATION_FAILED` (`messages.py:47`) is a format template, used unformatted as `message` at `jwt_auth.py:56` and as `title` in all three middleware 401 builders.
11. **`GET /users?limit=100000` is unbounded.** `views/user.py:90` is a bare `int(...)` passed to `UserService.get_all_users`; the `@extend_schema` at `user.py:46` documents "max: 100"; `PaginationConfig.MAX_LIMIT` is 200.
12. **`AuthErrorMessages` binds `TOKEN_EXPIRED` and `TOKEN_INVALID` twice each** (`messages.py:94/99`, `:95/101`); the first pair is dead.
13. **`POST /user-roles` removal answers HTTP 200 on failure.** `views/user_role.py:94` returns a `Response` with no `status` argument.
14. **Silent `updated_by` loss on the reassign path.** `task_assignment_repository.py:512` writes the key `"updated_by"` where the two originals write `"updatedBy"`; `_transform_task_data` reads only the camelCase form (`dual_write_service.py:262`).

**Fix items 1–3, 9, 10, 12, 13 in place immediately.** They are one- to three-line edits and do not depend on any extraction below.

---

## 2. Prioritized opportunities

Ranked by (drift risk × surface area) / effort. Effort: **S** ≤ half a day, **M** 1–3 days, **L** ≥ a week or requires a data migration.

| # | Opportunity | Where (files / representative paths) | Copies | ~Lines | Sev | Effort |
|---:|---|---|---:|---:|:--:|:--:|
| 1 | **Route every error response through the already-registered DRF handler** — delete 8 `_handle_validation_errors`, 11 hand-built 500 envelopes, 8 `ValueError`→`ApiErrorResponse` unwraps, 4 unreachable handler branches, 3 middleware 401 builders, the dead role-handler trio | 9 files · `views/{task,team,task_assignment,watchlist,team_creation_invite_code,role}.py`, `exceptions/exception_handler.py`, `exceptions/global_exception_handler.py`, `middlewares/jwt_auth.py` | 44 | ~508 | high | M |
| 2 | **TaskService write-path consolidation** — `_get_task_for_write`, `validate_assignee_exists`, `_build_task_update_payload`/`_apply_task_update`; delete the 90-line clone and the dead `profile` branch | 3 files · `services/task_service.py`, `services/task_assignment_service.py`, `repositories/task_repository.py` | 19 | ~258 | high | S–M |
| 3 | **Move `invite_code` redaction off the view layer onto the DTO** | 2 files · `views/team.py:40,168,224,251,296` (+ the omission at `:85`), `dto/team_dto.py:47` | 6 | ~18 | high | S |
| 4 | **`id_or_str` / `to_object_id` — retire the hand-rolled ObjectId-then-string fallbacks** | 4 files · `repositories/{task_assignment,user_team_details,task,user_role}_repository.py` | 20 | ~173 | high | M |
| 5 | **One `UserNotFoundException`; typed `TeamNotFoundException` / `TaskAssignmentNotFoundException`; shared exception bases** | 8 files · `exceptions/*`, `services/{team,task,task_assignment,user}_service.py`, `repositories/user_repository.py` | 22 | ~98 | high | M |
| 6 | **One pagination stack** — `PaginationConfig`, `PaginationQueryParamsSerializer`, `pagination_utils.build_links`, `schema_params.pagination_params` | 12 files · `services/{task,watchlist,label,user,team_creation_invite_code}_service.py`, `serializers/get_*`, `views/{user,task,watchlist,team_creation_invite_code}.py` | 23 | ~250 | high | M |
| 7 | **`from_model` DTO mappers** — `TeamDTO`×5, `TaskAssignmentDTO`×3 (+ delete `TaskAssignmentResponseDTO`), `LabelDTO`×3, merge the three user DTOs | 8 files · `dto/*`, `services/{team,task,task_assignment,label,watchlist,user}_service.py` | 20 | ~143 | high | S–M |
| 8 | **Abstract Postgres model bases** — `SyncedModel`, `TimestampedModel`, `SoftDeletableModel` + `active_unique()`; `SyncStatus` constants | 11 files · `models/postgres/*.py` | 23 | ~200 | high | M |
| 9 | **Dual-write ritual + declarative entity registry** — `sync_to_postgres` on `MongoRepository`; `EntityMap` replacing 11 `_transform_*`, the 11-branch dispatch, `COLLECTION_MODEL_MAP`, and 11 repository payload dicts | 14 files · all of `repositories/`, `services/dual_write_service.py`, `models/postgres/` | 49 | ~706 | high | L |
| 10 | **ObjectId validation as a type** — `ObjectIdField` (DRF) + annotated pydantic type; delete 10 hand-written validators | 9 files · `serializers/*`, `dto/*`, `models/*`, `utils/task_validation_utils.py`, `views/watchlist.py` | 23 | ~100 | high | M |
| 11 | **Serializer sharing** — `TaskWriteSerializer` base, nested `AssigneeSerializer`, `validate_due_at_in_timezone`, enum `choices()` | 6 files · `serializers/{create,update}_task_serializer.py`, `create_task_assignment_serializer.py`, `get_tasks_serializer.py` | 16 | ~142 | high | M |
| 12 | **`AuditService.record` + `AuditAction` enum** | 6 files · `services/{team,task,task_assignment,team_creation_invite_code}_service.py`, `views/task_assignment.py`, `repositories/task_assignment_repository.py` | 13 | ~78 | med | M |
| 13 | **`MongoRepository` primitives** — `insert`, `find_one_model`, `find_models`; make `UserRepository` a subclass | 8 files · `repositories/*` | 22 | ~160 | med | M |
| 14 | **Sync-service and migration plumbing** — `_sync_collection`, `DualWriteService._write`, `@skip_if_disabled`, `seed_collection`, `BaseRunnerCommand` | 6 files · `services/{postgres_sync,dual_write,enhanced_dual_write}_service.py`, `db/migrations.py`, `management/commands/*` | 20 | ~370 | med | M |
| 15 | **Single team-membership authority + merge the two rival `UserTeamDetailsRepository` classes** | 4 files · `services/team_service.py`, `repositories/{team,user_team_details}_repository.py` | 8 | ~92 | high | L |
| 16 | **Test fixtures and assertion helpers** — `assertApiError`, `seed_task`/`seed_task_assignment`, `AuthCookieMixin`, model/DTO factories, contract mixins | ~20 files · `todo/tests/**` | ~150 | ~1,700 | med | M |

---

## 3. Detailed opportunities

### 3.1 — Route every error response through the registered DRF exception handler

**What is duplicated.** Six distinct fragments, all answering "an operation failed; render it":

| Fragment | Sites |
|---|---|
| `_handle_validation_errors` method | `views/task.py:169-195`, `:367-393`; `views/team.py:102-123`, `:127-129`, `:319-326`, `:469-489`; `views/team_creation_invite_code.py:28-30`, `:125-127` |
| inline validation-error responses | `views/task.py:423-425`; `views/task_assignment.py:54-56`; `views/team.py:244-246` |
| `except Exception` → 500 `ApiErrorResponse` | `views/task.py:434-439`; `views/team.py:179-184`, `:312-317`; `views/task_assignment.py:77-84`, `:138-145`, `:301-308`; `views/watchlist.py:101-108` |
| `except ValueError` → unwrap `e.args[0]` → 500 fallback | `views/task.py:151-167`, `:349-365`; `views/team.py:45-57`, `:88-100`, `:300-317`; `views/watchlist.py:96-108` |
| service-side "wrap in `ValueError(ApiErrorResponse)`" | `services/task_service.py:655-684`; `services/watchlist_service.py:49-62`, `:101-130`; `utils/task_validation_utils.py:26-38`, `:42-54` |
| middleware 401 builder | `middlewares/jwt_auth.py:36-49`, `:54-67`, `:149-157` |

Plus four **unreachable** duplicate branches inside `handle_exception` itself (`exception_handler.py:98-113`, `:114-129`, `:130-145`, `:192-200`) and a dead role-error trio (`exceptions/global_exception_handler.py:16-36` — zero callers — plus `:39-68` and `views/role.py:21-41`).

`diff <(sed -n '169,195p' todo/views/task.py) <(sed -n '367,393p' todo/views/task.py)` returns empty. `diff <(sed -n '76,84p' todo/views/task_assignment.py) <(sed -n '137,145p' ...)` returns empty.

**Drift.** Five wire formats now answer "a serializer rejected the payload":

1. `ApiErrorResponse` envelope with per-field `source` — `task.py:169`, `:367`, `team.py:102`
2. `{"errors": <raw DRF dict>}` — `team.py:127`, `tcic.py:28`, `:125`, `task.py:425`, `task_assignment.py:56`
3. bare `serializer.errors` — `team.py:246`
4. envelope with the field name discarded — `team.py:319-326`: `errors=[{"detail": str(error)} for error in errors.values()]`, where `error` is the *list*, so the client receives the stringified repr of a list
5. hand-built dict — `team.py:469-489`: literal `"Invalid value"` instead of `ApiErrors.VALIDATION_ERROR`, plain `"source": field` instead of `{ApiErrorSource.PARAMETER: field}`, an `"authenticated"` key no other copy emits, and no `isinstance(messages, list)` guard, so a scalar message is iterated character by character

Four more for 500s: bare `status=500` vs `status.HTTP_500_INTERNAL_SERVER_ERROR` in the same file (`team.py:184`, `:317`); `fallback_response` renamed to `error_response` at `task.py:434` (the paste-and-edit tell); the same `ValueError` rendered as 500 by `GET /teams` (`team.py:45-57`), 404 by `GET /teams/<id>` (`team.py:171-177`) and 400 by `POST /teams/<id>/members` (`team.py:300-317`). None of the seven `except Exception` blocks logs anything.

The `/roles` subtree emits a sixth format, `{"error": "..."}`, from a mechanism that exists in triplicate, one copy of which has no callers.

**Proposed abstractions.**

```
todo/exceptions/api_error.py
    class ApiError(Exception)                      # carries .response: ApiErrorResponse
    def server_error(exc) -> ApiError
    def repository_error(exc, *, source: str) -> ApiError

todo/utils/response_utils.py                        # interim shim for views that must not raise
    def validation_error_response(errors) -> Response
    def api_error_response(exc, *, fallback_status=500) -> Response

todo/middlewares/responses.py
    def auth_error_json(message: str, *, detail: str | None = None) -> JsonResponse

todo/exceptions/exception_handler.py                # table replaces the six auth branches
    AUTH_ERROR_SPECS: dict[type[Exception], tuple[int, str]]
    def _build_error_response(exc, status_code, error_list, authenticated=None) -> Response
```

`validation_error_response` delegates to the existing, already-recursive `format_validation_errors` (`exception_handler.py:29-45`) — the only implementation that handles nested serializer dicts and scalar values. To avoid a `views → exceptions` cycle, move `format_validation_errors` into `todo/utils/response_utils.py` and have `exception_handler` import it from there.

**Sketch.**

```python
# todo/utils/response_utils.py
def validation_error_response(errors) -> Response:
    body = ApiErrorResponse(
        statusCode=400,
        message=ApiErrors.VALIDATION_ERROR,
        errors=format_validation_errors(errors),
    )
    return Response(data=body.model_dump(mode="json"), status=status.HTTP_400_BAD_REQUEST)


def api_error_response(exc, *, fallback_status=status.HTTP_500_INTERNAL_SERVER_ERROR) -> Response:
    if isinstance(exc, ValueError) and exc.args and isinstance(exc.args[0], ApiErrorResponse):
        wrapped = exc.args[0]                       # the e.args guard, in one place
        return Response(data=wrapped.model_dump(mode="json"), status=wrapped.statusCode)
    fallback = ApiErrorResponse(
        statusCode=fallback_status,
        message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
        errors=[{"detail": str(exc) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR}],
    )
    return Response(data=fallback.model_dump(mode="json"), status=fallback_status)


# todo/exceptions/exception_handler.py — replaces :56-145 (90 lines)
AUTH_ERROR_SPECS = {
    TokenExpiredError: (401, AuthErrorMessages.TOKEN_EXPIRED_TITLE),
    TokenMissingError: (401, AuthErrorMessages.AUTHENTICATION_REQUIRED),
    TokenInvalidError: (401, AuthErrorMessages.INVALID_TOKEN_TITLE),
    RefreshTokenExpiredError: (403, AuthErrorMessages.TOKEN_EXPIRED_TITLE),
}

def _auth_error_response(exc) -> Response | None:
    for exc_type, (status_code, title) in AUTH_ERROR_SPECS.items():
        if isinstance(exc, exc_type):
            detail = ApiErrorDetail(source={ApiErrorSource.HEADER: "Authorization"},
                                    title=title, detail=str(exc))
            body = ApiErrorResponse(statusCode=status_code, message=detail.detail,
                                    errors=[detail], authenticated=False)
            return Response(data=body.model_dump(mode="json", exclude_none=True), status=status_code)
    return None
```

**Call sites after.**

```python
# todo/views/team.py TeamListView.post — 22-line method deleted, 2 lines become 1
    serializer.is_valid(raise_exception=True)

# todo/views/task_assignment.py TaskAssignmentDetailView.get — 9 lines become 0
    def get(self, request: Request, task_id: str):
        assignment = TaskAssignmentService.get_task_assignment(task_id)
        if not assignment:
            raise TaskAssignmentNotFoundException(task_id)
        return Response(data=assignment.model_dump(mode="json"), status=status.HTTP_200_OK)

# todo/views/team.py TeamListView.get — 13 lines become 2 (interim), then 0
        except ValueError as e:
            return api_error_response(e)

# todo/services/watchlist_service.py:117-130 — 14 lines become 2
        except Exception as e:
            raise server_error(e)

# todo/middlewares/jwt_auth.py:36-49, :54-67, :149-157 — 35 lines become 3
        return self._unauthorized(AuthErrorMessages.AUTHENTICATION_REQUIRED)
```

**Sequencing within this item.** Delete the four unreachable handler branches *first* (a no-op today), after deciding per pair which body is correct — the evidence says keep the dead `UserNotFoundException` body (path-aware `source`, matching its `TaskNotFoundException` sibling at `:185`) and make the expired-token branch return `authenticated=False` like its two peers. Only then remove the per-view catches, or the views' non-500 mappings (`team.py:305-310` → 400, `team.py:171-177` → 404) will silently become 500s. Those two need typed exceptions from item 5 first.

**Client-visible changes to version:** three of the five validation shapes disappear; `/roles` moves onto the standard envelope; `POST /tasks` label errors move from scalar to list; the middleware 401 gains `authenticated: false`.

---

### 3.2 — TaskService write-path consolidation

**What is duplicated.** Four fragments inside one file, plus one that escaped into the repository layer.

*(a) The write guard*, byte-identical at `task_service.py:293-303`, `:376-386`, `:468-478`, `:544-554`, comments included:

```python
        current_task = TaskRepository.get_by_id(task_id)
        if not current_task:
            raise TaskNotFoundException(task_id)
        # Check if user is the creator
        if current_task.createdBy != user_id:
            # Check if user is assigned to this task
            assigned_task_ids = TaskRepository._get_assigned_task_ids_for_user(user_id)
            if current_task.id not in assigned_task_ids:
                raise PermissionError(ApiErrors.UNAUTHORIZED_TITLE)
```

A fifth copy at `repositories/task_repository.py:270-279` re-expresses the same rule against a raw document.

*(b) Assignee-existence validation* at `task_service.py:305-318`, `:388-401`, `:480-492`, `:598-615` and `task_assignment_service.py:29-39`.

*(c) The update-payload loop and write tail* at `task_service.py:324-368`, `:404-449`, `:494-529`.

*(d) An entire 90-line clone:* `update_task_with_assignee` (`:462-540`) duplicates `update_task_with_assignee_from_dict` (`:370-460`). `grep` confirms the only production caller is `views/task.py:343`, which calls the `_from_dict` variant; the clone is referenced solely from six unit-test call sites.

**Drift.**

- The four service copies reach into the *private* `TaskRepository._get_assigned_task_ids_for_user` at `:301`, `:384`, `:476`, `:552` — the only cross-layer private-method calls in the repository package.
- The repository copy filters `isDeleted: False` (`task_repository.py:270`) while `TaskRepository.get_by_id` (`:259-264`) does not, so a soft-deleted task can be updated, deferred and re-assigned but not deleted.
- **The `startedAt` rule is dead on one endpoint.** `task_service.py:429` tests `validated_data.get("status") == TaskStatus.IN_PROGRESS`, but `TaskStatus` is a plain `Enum` (`constants/task.py:4-10`) and `UpdateTaskSerializer.status` is a `ChoiceField` over `status.name` strings (`update_task_serializer.py:18-22`). Always `False`. Two lines later (`:434`) the same method compares against `TaskStatus.DEFERRED.value` — the correct form. The DTO copy at `:519` works because `dto.status` really is an enum.
- Only copy 1 writes the `status_changed` audit row (`:353-363`), so a status change through either of the other two endpoints leaves no audit record.
- `deferredDetails` clearing exists only in copy 2 (`:432-440`); the clone never received it — the fix landed on the path with no production caller.
- Unknown `user_type` raises in `task_assignment_service.py:38-39` and falls through silently in all four `TaskService` copies. `create_task` (`:608-611`) additionally validates the optional `team_id`; the three update copies do not, so an update can attach a non-existent team that create would reject.
- The fetched-user local is named `assignee_data` at `:312` and `user_data` at `:395`/`:486`.
- `resolve_assignee` divergence (finding 23): for an assignment row whose user/team record is gone, `TaskService._prepare_assignee_dto` returns `None` (task renders unassigned) while `TaskAssignmentService.get_task_assignment` substitutes `"Unknown User"`.

**Proposed abstractions.**

```
todo/services/task_service.py
    @classmethod def _get_task_for_write(cls, task_id: str, user_id: str) -> TaskModel
    @classmethod def _build_task_update_payload(cls, current_task, fields: dict, user_id: str) -> dict
    @classmethod def _apply_task_update(cls, current_task, payload: dict, user_id: str) -> TaskModel

todo/repositories/task_repository.py
    @classmethod def get_assigned_task_ids_for_user(cls, user_id)   # promoted from private

todo/utils/assignee_validation_utils.py
    def validate_assignee_exists(assignee_id: str, user_type: str, team_id: str | None = None) -> None
    def resolve_assignee(assignee_id: str, user_type: str) -> tuple[Any | None, str | None]
```

**Sketch.**

```python
# todo/services/task_service.py
    ENUM_FIELDS = {"priority": TaskPriority, "status": TaskStatus}

    @classmethod
    def _get_task_for_write(cls, task_id: str, user_id: str) -> TaskModel:
        task = TaskRepository.get_by_id(task_id)
        if not task:
            raise TaskNotFoundException(task_id)
        if task.createdBy != user_id:
            if task.id not in TaskRepository.get_assigned_task_ids_for_user(user_id):
                raise PermissionError(ApiErrors.UNAUTHORIZED_TITLE)
        return task

    @classmethod
    def _build_task_update_payload(cls, current_task, fields: dict, user_id: str) -> dict:
        payload = {}
        raw = fields.get("status")
        new_status = raw.value if hasattr(raw, "value") else raw   # ONE normalisation, not three
        for field, value in fields.items():
            if field == "assignee" or getattr(current_task, field, None) == value:
                continue
            if field == "labels":
                payload[field] = cls._process_labels_for_update(value)
            elif field in cls.ENUM_FIELDS:
                payload[field] = value.value if hasattr(value, "name") \
                                 else cls._process_enum_for_update(cls.ENUM_FIELDS[field], value)
            elif field in cls.DIRECT_ASSIGNMENT_FIELDS:
                payload[field] = value
        if new_status == TaskStatus.IN_PROGRESS.value and not current_task.startedAt:
            payload["startedAt"] = datetime.now(timezone.utc)      # rule now live on all paths
        if new_status and new_status != TaskStatus.DEFERRED.value and current_task.deferredDetails:
            payload["deferredDetails"] = None
        return payload
```

**Call sites after.**

```python
# defer_task, was :544-554 + body
    @classmethod
    def defer_task(cls, task_id: str, deferred_till: datetime, user_id: str) -> TaskDTO:
        current_task = cls._get_task_for_write(task_id, user_id)
        if current_task.status == TaskStatus.DONE:
            raise TaskStateConflictException(ValidationErrors.CANNOT_DEFER_A_DONE_TASK)
        ...

# update_task_with_assignee_from_dict, was :388-401 + :404-449
        if validated_data.get("assignee"):
            a = validated_data["assignee"]
            validate_assignee_exists(a.get("assignee_id"), a.get("user_type"), a.get("team_id"))
        payload = cls._build_task_update_payload(current_task, validated_data, user_id)
        updated_task = cls._apply_task_update(current_task, payload, user_id)

# update_task_with_assignee (:462-540) — deleted, or kept as a 2-line adapter:
    @classmethod
    def update_task_with_assignee(cls, task_id: str, dto: CreateTaskDTO, user_id: str) -> TaskDTO:
        return cls.update_task_with_assignee_from_dict(
            task_id, dto.model_dump(exclude_none=True, exclude={"createdBy"}), user_id)
```

**Also in scope, as deletions rather than extractions:** the unreachable second `if query.validated_data["profile"]` branch at `views/task.py:90-99`. Decide deliberately whether `exclude_none=True` was the intended profile serialisation before dropping it — the code currently contains both answers and ships the one nobody chose. Check `tests/integration/test_task_profile_api.py` against the current payload.

**Caveat before adopting the adapter:** `exclude_none=True` means a DTO caller cannot express "set this field to null", while the dict path can. Reconcile that before repointing the clone's six tests.

---

### 3.3 — Move the `invite_code` redaction off the view layer

**What is duplicated.** The same three-line tail at `views/team.py:168-170`, `:224-226`, `:251-253`, `:296-298`, and a nested variant at `:40-43`:

```python
            data = response.model_dump(mode="json")
            data.pop("invite_code", None)
            return Response(data=data, status=status.HTTP_200_OK)
```

**Drift — the omission.** `TeamListView.post` (`views/team.py:84-86`) does not pop. The leak is traced end to end: `dto/responses/create_team_response.py:13` declares `team: TeamDTO`; `dto/team_dto.py:47` declares `invite_code: str` with no exclude; `services/team_service.py:145-167` populates it and returns `CreateTeamResponse`.

That the omission is accidental is settled twice: `TeamInviteCodeView` (`views/team.py:350-365`) exists solely to hand out the code and gates it behind a creator-or-POC check returning 403; and `tests/integration/test_team_update.py:135` asserts `assertNotIn("invite_code", data)` on the sibling PATCH response.

**The obvious patch does not work.** Adding `data.pop("invite_code", None)` at `team.py:85` is a no-op — unlike the five other sites, which dump a `TeamDTO` with the field at top level, `CreateTeamResponse` nests it at `data["team"]["invite_code"]`. That the six copies are not structurally interchangeable is itself the argument for moving the rule off the view layer.

**Proposed abstraction.** Make the DTO incapable of carrying the secret into a response:

```python
# todo/dto/team_dto.py:47
class TeamDTO(BaseModel):
    ...
    invite_code: str = Field(exclude=True)      # never serialised into a response
```

`TeamInviteCodeView` is unaffected: `views/team.py:355-361` reads `team.invite_code` off the repository model, never off a DTO dump.

**Call sites after.** All six collapse to a plain dump:

```python
            return Response(data=response.model_dump(mode="json"), status=status.HTTP_200_OK)
```

**Before flipping:** verify no service relies on `invite_code` round-tripping through `TeamDTO` (`team_service.py` `join_team_by_invite_code` / `update_team`). If one does, the alternative is dropping the field from `TeamDTO` entirely and giving `TeamInviteCodeView` a dedicated `TeamInviteCodeDTO`. Keep `test_team_update.py:135` as the regression guard. Combine with item 7 (`TeamDTO.from_model`), which touches the same five construction sites.

---

### 3.4 — One id-encoding helper, retiring the ObjectId-then-string fallbacks

**What is duplicated.** Four shapes of one idea across 20 sites.

*Shape A — run, check `modified_count`, re-run with the string form.* `task_assignment_repository.py:183-205` vs `:308-330`: `diff` shows exactly two differing lines (`update_one` vs `update_many` on both halves).

*Shape B — the cartesian permutation.* `user_team_details_repository.py:21-31`, repeated verbatim at `:45-50`:

```python
        queries = [
            {"user_id": user_id_obj, "team_id": team_id_obj},
            {"user_id": user_id,     "team_id": team_id_obj},
            {"user_id": user_id_obj, "team_id": team_id},
            {"user_id": user_id,     "team_id": team_id},
        ]
        for query in queries:
            result = collection.find_one(query)
```

*Shape C — both encodings in one query, which already works:* `task_assignment_repository.py:378-380`, `task_repository.py:136`.

*Shape D — the bare `try: ObjectId(x) except: <sentinel>` guard*, seven times with three different sentinels: `return None` (`task_repository.py:305-308`, `user_role_repository.py:95-98`), `return False` (`user_role_repository.py:125-128` — a block that diffs against `:95-106` in exactly one line), and fall-through to the raw string (the four blocks in `user_team_details_repository.py`).

**Drift.**

- `task_assignment_repository.py:112-133` runs both `update_many` calls unconditionally, unlike its three verified-identical siblings which guard on `modified_count == 0`.
- `task_assignment_repository.py:82` — `if not list(task_assignments_data):` exhausts the cursor, so a successful ObjectId match returns `[]`. This feeds `TaskRepository._get_assigned_task_ids_for_user` and therefore the task permission checks in item 2.
- The write side mixes encodings from otherwise-identical blocks: `ObjectId(user_id)` at `:118, :129, :188, :201, :314, :325`; plain `user_id` at `:251, :264`.
- Elsewhere the conversion is unguarded and raises: `task_repository.py:261`, `:377`; `team_repository.py:59` is guarded only by a blanket `except Exception` around the whole method. `UserRepository` uses a third converter, `PyObjectId(...)`, which raises `ValueError` rather than `bson.InvalidId`.

**Proposed abstraction.**

```python
# todo/repositories/common/id_filters.py
_RAISE = object()

def id_or_str(value):
    """Match either stored encoding in a single query."""
    v = str(value)
    return {"$in": [ObjectId(v), v]} if ObjectId.is_valid(v) else {"$in": [v]}

def to_object_id(value, *, default=_RAISE):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        if default is _RAISE:
            raise
        return default

def to_object_ids(values) -> list[ObjectId]: ...
def actor_id(value) -> ObjectId:            # used wherever created_by/updated_by is written
    return ObjectId(str(value))
```

**Call sites after.**

```python
# task_assignment_repository.py:183-205 — 22 lines become 5
            result = collection.update_one(
                {"task_id": id_or_str(task_id), "is_active": True},
                {"$set": {"is_active": False, "updated_by": actor_id(user_id),
                          "updated_at": datetime.now(timezone.utc)}},
            )

# user_team_details_repository.py:11-32 — 22 lines become 1
        return collection.find_one({"user_id": id_or_str(user_id), "team_id": id_or_str(team_id)})

# task_repository.py:305-308 — the sentinel becomes a visible argument
        obj_id = to_object_id(task_id, default=None)
        if obj_id is None:
            return None
```

**Caveats.** `$in` over mixed types can widen the index scan on `task_details.task_id` where the guarded form short-circuits on the ObjectId hit — measure before converting the Shape-A write paths. Narrowing `except Exception` to `InvalidId` is a real behaviour change: `TypeError`s those blocks currently swallow would start escaping. Treat this helper explicitly as a **bridge to a one-encoding data migration**, not the destination; item 15 (membership) cannot be done safely until that migration lands.

---

### 3.5 — Typed not-found exceptions and a single `UserNotFoundException`

**What is duplicated.** Two unrelated classes with the same name:

```python
# todo/exceptions/user_exceptions.py:4-13 — rich, guarded template formatting
class UserNotFoundException(Exception):
    def __init__(self, user_id: str | None = None, message_template: str = ApiErrors.USER_NOT_FOUND): ...

# todo/exceptions/auth_exceptions.py:40-42 — message only
class UserNotFoundException(BaseAuthException):
    def __init__(self, message: str = RepositoryErrors.USER_NOT_FOUND): ...
```

Nine bare `ValueError`s for a missing team, in two formats split cleanly by file: `"Team with id {x} not found"` at `team_service.py:246, :344, :405`; `"Team not found: {x}"` at `task_service.py:318, :401, :492, :611, :615` and `task_assignment_service.py:37`. Two more spellings in the view layer: `{"detail": "Team not found."}` at `views/team.py:357, :403`. Plus a nested marker class `TeamService.TeamOrUserNotFound` (`team_service.py:481`).

"Task assignment not found" is hand-built byte-identically at `views/task_assignment.py:128-133` and `:291-296`, with a third handler in the same class answering the same condition as `{"error": "Task assignment not found."}` at `:185`.

Three identical `__init__` bodies (`auth_exceptions.py:4-7`, `team_exceptions.py:4-7`, `task_exceptions.py:20-23`) and two copies of the `(entity_id, message_template)` constructor.

**Drift.**

- `exception_handler.py:26` imports only the `user_exceptions` variant, and the auth variant extends `BaseAuthException` but not `AuthException`, so it also misses the auth branch at `:155`. `UserService.get_user_by_id` raising user-not-found falls through to a generic **500** while `TaskService` returns 404 for the identical condition.
- The two templates differ: `RepositoryErrors.USER_NOT_FOUND = "User not found: {0}"` (`messages.py:17`) vs `ApiErrors.USER_NOT_FOUND = "User with ID {0} not found."` (`messages.py:53`) — and the auth variant passes the template through unformatted, so the literal `{0}` reaches the client.
- `TaskNotFoundException.__init__` calls `message_template.format(task_id)` bare (`task_exceptions.py:7`); its sibling `UserNotFoundException` wrapped that call in a `try/except (KeyError, ValueError)` guard (`user_exceptions.py:7-10`). One copy hardened, one not — a caller passing a named placeholder gets a `KeyError` raised *inside* the exception constructor, converting an intended 404 into an unhandled 500.
- `todo/exceptions/team_exceptions.py` defines `BaseTeamException`, `NotTeamAdminException`, `CannotRemoveOwnerException`, `CannotRemoveTeamPOCException` — but no `TeamNotFoundException`, so the one team error that occurs nine times is the only one with no class, and `handle_exception` cannot map it to 404 the way it maps `TaskNotFoundException` at `:182-190`.

**Proposed abstractions.**

```
todo/exceptions/base.py
    class MessageException(Exception)                       # the 3 identical __init__ bodies
    class EntityNotFoundException(MessageException)         # guarded .format, generic fallback

todo/exceptions/team_exceptions.py
    class TeamNotFoundException(EntityNotFoundException)
todo/exceptions/task_exceptions.py
    class TaskAssignmentNotFoundException(EntityNotFoundException)

todo/services/team_service.py
    @classmethod def get_team_or_raise(cls, team_id: str) -> TeamModel

todo/constants/messages.py
    ApiErrors.TEAM_NOT_FOUND = "Team with ID {0} not found."
    ApiErrors.TEAM_NOT_FOUND_GENERIC = "Team not found."
    ApiErrors.TASK_ASSIGNMENT_NOT_FOUND / _DETAIL
```

**Sketch.**

```python
# todo/exceptions/base.py
class EntityNotFoundException(MessageException):
    generic_message = "Not found."
    message_template = "{0} not found."

    def __init__(self, entity_id: str | None = None, message_template: str | None = None):
        template = message_template or self.message_template
        if not entity_id:
            super().__init__(self.generic_message)
            return
        try:
            super().__init__(template.format(entity_id))
        except (KeyError, IndexError, ValueError):     # the guard, applied once
            super().__init__(f"{template} (ID: {entity_id})")


# todo/exceptions/exception_handler.py — one branch replaces :173-181 and :192-200
    elif isinstance(exc, UserNotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
        error_list.append(ApiErrorDetail(
            source={ApiErrorSource.PATH: "user_id"} if user_id else {ApiErrorSource.PARAMETER: "user_id"},
            title=ApiErrors.RESOURCE_NOT_FOUND_TITLE, detail=str(exc)))
```

**Call sites after.**

```python
# todo/services/team_service.py:244-257 and todo/services/task_service.py:318 converge on
        raise TeamNotFoundException(team_id)
# and the three fetch-and-raise preambles collapse to
        return TeamDTO.from_model(cls.get_team_or_raise(team_id))

# todo/services/user_service.py:29 — same call, now reaching the 404 branch
        raise UserNotFoundException(user_id)
```

**Must land together with:** narrowing the two catch-alls at `team_service.py:169-170` and `:478-479` (`except Exception as e: raise ValueError(f"Failed to ...")`), or the new typed exception is swallowed and nothing improves. Every `except UserNotFoundException` and `except BaseAuthException` in views and middleware must be re-checked in the same commit, because `user_service.py:20` re-raises it by name in a tuple. Delete `RepositoryErrors.USER_NOT_FOUND` once nothing reads it.

**Client-visible:** `GET /teams/<id>/invite-code` and `/activity-timeline` 404 bodies move onto the standard envelope; `PATCH /task-assignments/<id>` 404 changes shape (`tests/unit/views/test_task_assignment.py` will need updating).

---

### 3.6 — One pagination stack

**What is duplicated.** Five layers, none agreeing.

| Layer | Sites |
|---|---|
| `PaginationConfig` class | `task_service.py:51-55` (`@dataclass`), `watchlist_service.py:23-26` (plain class), `label_service.py:14-19` (`@dataclass`, `DEFAULT_LIMIT: int = 10` hardcoded) |
| query-param serializer fields | `get_tasks_serializer.py:15-31`, `get_labels_serializer.py:8-24`, `get_watchlist_tasks_serializer.py:8-24` |
| raw `int(request.query_params.get(...))` | `views/user.py:89-90`, `views/team_creation_invite_code.py:189-195` |
| link building | `task_service.py:137-157`, `watchlist_service.py:188-208`, `label_service.py:64-83`, `team_creation_invite_code_service.py:62-67` |
| OpenAPI `page`/`limit` blocks | `views/task.py:40-51`, `views/watchlist.py:28-41`, `views/user.py:35-48`, `views/team_creation_invite_code.py:145-158` |
| bounds validation | `task_service.py:126-135`, `user_service.py:97-114` |

**Drift.**

- **Default page size:** `label_service.py:17` and `get_labels_serializer.py:18` hardcode `10`; the others read `DEFAULT_PAGE_LIMIT` = 20 (`settings/base.py:104`). `/labels` silently pages at half the size of every other list endpoint, and changing the setting moves four endpoints but not labels.
- **Max limit:** `PaginationConfig.MAX_LIMIT` = 200; `user_service.py:110` hardcodes `if limit > 100`; `views/user.py:46` documents "max: 100" and enforces nothing (`user.py:90` is a bare `int()` straight into the service); `team_creation_invite_code.py:155` documents "max: 50" and does enforce it at `:194-195` by silently clamping.
- **Three behaviours for the same untrusted input:** `?page=abc` → uncaught `ValueError` → 500 on `/users`; → 400 on `/team-invite-codes`; → 400 with a proper envelope on the three serializer-backed endpoints.
- **Four message wordings.** `ValidationErrors.PAGE_POSITIVE` / `LIMIT_POSITIVE` / `MAX_LIMIT_EXCEEDED` exist at `messages.py:71-73`. `get_labels_serializer` uses them; `get_tasks_serializer.py:20/:29` invents lowercase literals; `task_service.py:129-135` retypes the same English as three literals; `MAX_LIMIT_EXCEEDED` is reachable only through the hand-rolled service copies.
- **Two rounding formulas** (`math.ceil(total/limit)` vs `(total + limit - 1) // limit`) and **two response contracts** (`LinksData(next=, prev=)` vs bare `next_url`/`previous_url` strings).
- Two different exception types for the same condition: `django.core.exceptions.ValidationError` with a bare message vs `rest_framework.exceptions.ValidationError` with a field-keyed dict — so identical bad input produces two different HTTP shapes.
- `task_service.py:693-707` (`get_tasks_for_user`) validates page and limit and then hardcodes `links=None` on both returns; the links were never wired up on that path. This is the `?profile=true` endpoint.
- The documented caps and the enforced caps come from different sources at every site (`schema.yaml:441-444` documents no defaults at all for `/tasks`).

**Proposed abstractions.**

```
todo/constants/pagination.py
    class PaginationConfig                       # one definition, all three services import it

todo/serializers/pagination_serializer.py
    class PaginationQueryParamsSerializer(serializers.Serializer)   # page + limit, from settings

todo/utils/pagination_utils.py
    def total_pages(total_count: int, limit: int) -> int
    def build_links(view_name: str, page: int, limit: int, total_count: int, **extra_params) -> LinksData
    def validate_pagination_params(page: int, limit: int, max_limit: int = PaginationConfig.MAX_LIMIT) -> None

todo/views/schema_params.py
    def pagination_params(item_noun: str, *, max_limit: int, default_limit: int = 10) -> list[OpenApiParameter]
```

**Sketch.**

```python
# todo/serializers/pagination_serializer.py
_P = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]

class PaginationQueryParamsSerializer(serializers.Serializer):
    page = serializers.IntegerField(
        required=False, default=1, min_value=1,
        error_messages={"min_value": ValidationErrors.PAGE_POSITIVE})
    limit = serializers.IntegerField(
        required=False, default=_P["DEFAULT_PAGE_LIMIT"],
        min_value=1, max_value=_P["MAX_PAGE_LIMIT"],
        error_messages={"min_value": ValidationErrors.LIMIT_POSITIVE,
                        "max_value": ValidationErrors.MAX_LIMIT_EXCEEDED.format(_P["MAX_PAGE_LIMIT"])})


# todo/utils/pagination_utils.py
def build_links(view_name, page, limit, total_count, **extra) -> LinksData:
    pages = total_pages(total_count, limit)
    def url(p): return f"{reverse_lazy(view_name)}?{urlencode({'page': p, 'limit': limit, **extra})}"
    return LinksData(next=url(page + 1) if page < pages else None,
                     prev=url(page - 1) if page > 1 else None)


# todo/views/schema_params.py — the documented cap becomes the enforced constant
def pagination_params(item_noun, *, max_limit, default_limit=10):
    return [OpenApiParameter(name="page", ...),
            OpenApiParameter(name="limit", ...,
                description=f"Number of {item_noun} per page (default: {default_limit}, max: {max_limit})")]
```

**Call sites after.**

```python
# todo/serializers/get_watchlist_tasks_serializer.py — its whole body deletes
class GetWatchlistTaskQueryParamsSerializer(PaginationQueryParamsSerializer):
    pass

# todo/serializers/get_labels_serializer.py — keeps only `search` and validate_search
class GetLabelQueryParamsSerializer(PaginationQueryParamsSerializer):
    search = serializers.CharField(required=False, default="", allow_blank=True, ...)

# todo/views/user.py:89-90 — replaces the two bare int() calls
        query = PaginationQueryParamsSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        page, limit = query.validated_data["page"], query.validated_data["limit"]

# todo/services/watchlist_service.py:188-208 — 20 lines become 1
        links = build_links("watchlist", page, limit, count)

# todo/views/watchlist.py — 14 lines of decorator become 1
        parameters=pagination_params("tasks", max_limit=MAX_PAGE_LIMIT),

# todo/services/task_service.py:707 — the gap finally closes
        return GetTasksResponse(tasks=task_dtos,
                                links=build_links("tasks", page, limit, total, status=status_filter))
```

**Behaviour changes to announce, not slip in:** `/labels` default page size 10 → 20; `/users?limit=` cap 100 → 200 (or keep 100 by passing `max_limit=100` explicitly — the parameter exists so the difference is stated rather than silent); `GET /users?limit=100000` starts returning 400 instead of a huge page; `GET /team-invite-codes?limit=99` starts returning 400 instead of silently falling back to 10. Migrate `TeamCreationInviteCodeService` onto `LinksData` as a separate announced change.

---

### 3.7 — `from_model` DTO mappers

**What is duplicated.** The convention already exists — `RoleDTO.from_model` (`dto/role_dto.py:25-55`), used by `role_service.py:17, :27`. Nothing else follows it.

| Mapper | Sites | Notes |
|---|---|---|
| `TeamModel → TeamDTO` | `team_service.py:145-155`, `:212-222`, `:247-257`, `:314-324`, `:371-381` (+ `:466-476`) | diffing the bodies yields only the receiver name |
| `TaskAssignmentModel → DTO` | `task_service.py:232-245`, `task_assignment_service.py:109-120`, `:143-155` | across two near-identical DTO classes |
| `LabelModel → LabelDTO` | `task_service.py:203-214`, `watchlist_service.py:140-152`, `label_service.py:85-111` | |
| user DTOs | `dto/user_dto.py:6-10/13-18/21-23`, `user_service.py:41-55`, `:116-130`, `views/user.py:98-104` | three overlapping classes |

**Drift.**

- All five `TeamDTO` copies omit `TeamDTO.users` (declared at `dto/team_dto.py:52`), so the enrichment is bolted on in the view at `views/team.py:165-167`. `get_user_teams` (`team_service.py:209-210`) re-fetches each team one at a time inside the loop — an N+1 that exists only because there is no shared mapper to feed from a batch query.
- `create_task_assignment` (`task_assignment_service.py:109-120`) omits `team_id` — 39 lines after writing that exact value into the model at `:70`. The omission then got baked into a second type: `TaskAssignmentResponseDTO` (`dto/task_assignment_dto.py:57-68`) has no `team_id` field at all, so `GET /task-assignments/{id}` and `POST /task-assignments` return two payload shapes for one entity. The two classes are the same 11 fields with two transposed and one dropped — and the trailing comment `# User ID executing the task (for team assignments)` appears verbatim in both (`:48`, `:63`).
- `watchlist_service.py:142` carries the `# Convert here!` `ObjectId` conversion that `task_service.py:203-214` lacks; `LabelRepository.list_by_ids` is typed `List[ObjectId]` and queries `{"_id": {"$in": ids}}`, so string ids match nothing. `TaskService` survives only because `TaskModel.labels` is `List[PyObjectId]` — an undocumented, load-bearing assumption, contradicted by its own `List[str]` type hint.
- `label_service.py:88-101` fabricates `createdBy`/`updatedBy` `UserDTO`s and passes four extra kwargs to `LabelDTO`, which declares only `id`/`name`/`color` — all discarded under `extra="ignore"`. Sixteen lines of dead work.
- `user_service.py:47-53` constructs a `UserDTO` with exactly `UserSearchDTO`'s field set; `UserDTO` declares none of `email_id`/`created_at`/`updated_at` and sets no `model_config`, so all three are silently dropped. `UserSearchDTO` has zero importers. `views/user.py:96-104` re-runs the identical comprehension over DTOs the service already built, wrapping DTOs in DTOs — necessary only because `search_users` returns raw `UserModel`s while `get_all_users` returns `UsersDTO`s.

**Proposed abstractions.**

```python
# todo/dto/team_dto.py
    @classmethod
    def from_model(cls, team: "TeamModel", users: list | None = None) -> "TeamDTO": ...

# todo/dto/task_assignment_dto.py  (and delete TaskAssignmentResponseDTO)
    @classmethod
    def from_model(cls, a: "TaskAssignmentModel", assignee_name: str | None = None) -> "TaskAssignmentDTO": ...

# todo/dto/label_dto.py
    @classmethod
    def from_model(cls, label: "LabelModel") -> "LabelDTO": ...

# todo/utils/label_utils.py
def prepare_label_dtos(label_ids: Iterable[str | ObjectId]) -> list[LabelDTO]:
    object_ids = [ObjectId(str(i)) for i in label_ids]      # one normalisation for every caller
    return [LabelDTO.from_model(m) for m in LabelRepository.list_by_ids(object_ids)]

# todo/dto/user_dto.py  — three classes become one
    model_config = ConfigDict(extra="forbid")               # the silent-drop bug becomes an error
    @classmethod
    def from_model(cls, user_model, **extras) -> "UserDTO": ...
```

**Call sites after.**

```python
# team_service.py:244-257
        return TeamDTO.from_model(cls.get_team_or_raise(team_id))
# views/team.py:165-167 — the users enrichment finally has one home
        return TeamDTO.from_model(team, users=[u.dict() for u in users])

# task_assignment_service.py:109-122
        return CreateTaskAssignmentResponse(data=TaskAssignmentDTO.from_model(assignment))

# task_service.py:161 / watchlist_service.py:156 — both private copies deleted
        label_dtos = prepare_label_dtos(task_model.labels) if task_model.labels else []

# views/user.py:98-104 — deletes entirely; the service already returns UserDTOs
```

**Guard the `str(None)` hazard inside the mapper** (`str(team.updated_by) if team.updated_by else None`) rather than at five call sites. **Do not leak `email_id`** when merging the user DTOs: `UsersDTO` is what the public search endpoint returns, so give the response an explicit projection rather than relying on `exclude_none`. **Decide separately** whether `LabelDTO` should grow the four audit fields or whether `label_service.py:88-101` should be deleted — extracting the mapper without that decision only relocates dead code.

---

### 3.8 — Abstract Postgres model bases

**What is duplicated.** Byte-identical in **all eleven** models (verified by grep count):

```python
    # Sync metadata
    last_sync_at = models.DateTimeField(auto_now=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[("SYNCED", "Synced"), ("PENDING", "Pending"), ("FAILED", "Failed")],
        default="SYNCED",
    )
    sync_error = models.TextField(null=True, blank=True)
```

plus `mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)` ×11, `models.Index(fields=["mongo_id"])` ×11, `models.Index(fields=["sync_status"])` ×11, and the `save()` override ×9:

```python
    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
```

**Drift.**

- **Two models never received `save()`** — `PostgresAuditLog` and `PostgresUserRole` — so those two preserve the Mongo `created_at` handed to them while the other nine overwrite it. A tenth, `PostgresTeamCreationInviteCode` (`:53-56`), is the same block with the `updated_at` line removed (correct for that model, but nothing records why; it reads as an incomplete paste).
- **The override defeats the backfill.** `PostgresSyncService._sync_labels_table` reads `created_at` straight from Mongo (`dual_write_service.py:297`) then calls `objects.create(**postgres_data)` (`postgres_sync_service.py:168`), which routes through `save()` and stamps `timezone.now()`. Every backfilled label gets today's date; backfilled audit logs and user roles keep theirs. `DualWriteService.update_document` carries `preserve_fields = {"created_at", "mongo_id"}` (`:118`) — a workaround written once in the service to compensate for nine copies in the models, and itself incomplete (`save()` at `:126` still stamps `updated_at`).
- **`updated_at` has two definitions:** `default=timezone.now` at `postgres/team.py:29, :82`; `null=True, blank=True` in the other six. Exactly mirroring the pydantic-side convention split (finding 52).
- **The soft-delete constraint fix propagated to one model of three.** `git show e58e9ec` (2025-09-19) replaced `unique_together` with a conditional `UniqueConstraint(..., condition=Q(is_active=True))` on `PostgresUserRole`, with the commit body "include is_active in unique constraint to prevent sync failures … fix bug where … data sync failed if a user was removed and added more than once". `PostgresUserTeamDetails` (`postgres/team.py:99`) and `PostgresWatchlist` (`postgres/watchlist.py:50`) still carry plain `unique_together`. The live exposure is `TeamService.join_team_by_invite_code` (`team_service.py:281-299`), whose membership check is `if str(user_team.team_id) == str(team.id) and user_team.is_active:` — an inactive membership falls straight through to `UserTeamDetailsRepository.create`, which dual-writes an insert violating `unique_together`. Precisely the remove-then-re-join scenario the other commit fixed one file over.
- `"PENDING"` and `"FAILED"` appear only inside the eleven choice lists and are assigned nowhere — `_record_sync_failure` (`dual_write_service.py:470-478`) appends to an in-memory list and never touches `sync_status`. The `sync_status` index is dead in all eleven; the `mongo_id` index is redundant with `unique=True`.

**Proposed abstractions.**

```python
# todo/constants/sync.py
class SyncStatus(models.TextChoices):
    SYNCED = "SYNCED", "Synced"; PENDING = "PENDING", "Pending"; FAILED = "FAILED", "Failed"

# todo/models/postgres/base.py
class SyncedModel(models.Model):
    mongo_id = models.CharField(max_length=24, unique=True, null=True, blank=True)
    last_sync_at = models.DateTimeField(auto_now=True)
    sync_status = models.CharField(max_length=20, choices=SyncStatus.choices, default=SyncStatus.SYNCED)
    sync_error = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True
        indexes = [models.Index(fields=["sync_status"], name="%(class)s_sync_idx")]


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        now = timezone.now()
        if self._state.adding and self.created_at is None:
            self.created_at = now            # honour a value the sync supplied
        if self.updated_at is None or not self._state.adding:
            self.updated_at = now
        super().save(*args, **kwargs)


class SoftDeletableModel(models.Model):
    is_active = models.BooleanField(default=True)
    class Meta: abstract = True


def active_unique(*fields: str, name: str) -> models.UniqueConstraint:
    """Uniqueness over live rows only, so a soft-deleted row never blocks re-creation."""
    return models.UniqueConstraint(fields=list(fields), condition=models.Q(is_active=True), name=name)
```

**Call sites after.**

```python
# todo/models/postgres/label.py — 12 field lines + the 5-line save() both delete
class PostgresLabel(SyncedModel, TimestampedModel):
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default="#000000")
    description = models.TextField(null=True, blank=True)

    class Meta(SyncedModel.Meta):                       # explicit, or base indexes vanish
        db_table = "postgres_labels"
        indexes = SyncedModel.Meta.indexes + [models.Index(fields=["name"])]

# todo/models/postgres/team.py — the re-join bug closes
class PostgresUserTeamDetails(SyncedModel, SoftDeletableModel):
    user_id = models.CharField(max_length=24)
    team_id = models.CharField(max_length=24)

    class Meta(SyncedModel.Meta):
        db_table = "postgres_user_team_details"
        constraints = [active_unique("user_id", "team_id", name="uniq_active_user_team")]

# dual_write_service.py:124 and the four other bare literals
                postgres_instance.sync_status = SyncStatus.SYNCED
```

**Sequencing within this item.** Land the base classes as a **pure no-op refactor first** and verify `makemigrations` produces nothing but index renames. Change `save()` in a second, separately reviewed commit — it is a behaviour change on nine tables. The constraint change needs a **data migration**, not just schema: Django must drop the `unique_together` index and add a partial one, and any duplicate inactive rows that have accumulated must be reconciled first. `Meta.indexes` is not inherited additively; write `class Meta(SyncedModel.Meta)` explicitly in each child or all eleven index sets are silently dropped in one commit.

---

### 3.9 — The dual-write ritual and a declarative entity registry

This is the largest single item and the one with the longest tail. Do it last (see §6).

**What is duplicated.** Three interlocking layers.

*(a) The epilogue, 21 copies.* `grep -c "dual_write_success = "` over `todo/repositories/` returns 21, and `EnhancedDualWriteService()` is instantiated 21 times in the same files:

```python
        dual_write_success = dual_write_service.create_document(
            collection_name="teams", data=team_data, mongo_id=str(team.id)
        )
        if not dual_write_success:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync team {team.id} to Postgres")
```

*(b) The payload, written twice per entity.* For **8 of 11** entities the repository builds a snake_case dict that `_transform_<entity>_data` then rebuilds key-for-key — an identity round-trip. `team_repository.py:28-37` vs `dual_write_service.py:268-278`: same nine keys, same order, same `str(...) if x else None` coercions. Same pairing for `task_assignments`, `watchlists`, `users`, `user_team_details`, `user_roles`, `audit_logs`, `team_creation_invite_codes`. Only `tasks` genuinely translates (camelCase → snake_case).

*(c) The routing, declared three times.* The document `collection_name` ClassVar, `COLLECTION_MODEL_MAP` (`dual_write_service.py:31-43`), and an eleven-branch `if/elif` (`:209-233`) that restates the same eleven keys again.

Plus 6 copies of the task-assignment deactivation payload inside one file (`task_assignment_repository.py:28-38, :138-148, :210-220, :273-283, :335-345, :471-481`, three of them byte-identical) and 3 copies of the task payload across two files (`task_repository.py:227-241, :324-338`, `task_assignment_repository.py:494-509`).

**Drift.**

- **Failure handling forked three ways:** 20 sites log and continue; `task_assignment_repository.py:514-520` logs and then `return False`, aborting the caller; four sites nested inside a blanket `except Exception: return False` (`task_assignment_repository.py:233-234, :296-297, :358-359`; `team_repository.py:318-319`) swallow a dual-write exception with no log at all.
- **20 distinct warning strings for one event.** No single grep finds all sync failures.
- **21 throwaway service instances** mean `self.sync_failures` (`dual_write_service.py:46`) is discarded after every call, so `get_sync_metrics` and `retry_failed_sync` — which read it — can never see anything. Both, plus `get_sync_status`, `get_sync_failures` and `clear_sync_failures`, have zero external callers.
- **The layer that normalises is decided per entity, inconsistently.** Enum unwrapping for `user_roles` happens in the repository (`user_role_repository.py:46-47`) and not in the mapper; for `tasks` it is the opposite (`dual_write_service.py:240-247`). ObjectId stringification for `user_roles` happens only in the mapper; for `teams` it happens in both, so `str()` runs twice.
- **Absent-value convention forked:** `str(data.get("updated_by", ""))` (empty string) at `:274` vs `... if data.get("updated_by") else None` at `:322` — same nullable FK, two answers, side by side. Across the file, `str(data.get(...))` appears 31 times split 15 unguarded / 14 guarded.
- **Key casing forked between neighbours:** `_transform_label_data` reads `createdAt`/`updatedAt` (`:297-298`); `_transform_role_data` reads `created_at`/`updated_at` (`:307-308`).
- **Create and update disagree about a mapper typo:** `create_document` passes the dict to `objects.create(**data)` (`:76`) so it raises; `update_document` filters with `hasattr` (`:121`) so it silently ignores.
- **Two entities' collection name and routing key differ:** `WatchlistModel.collection_name = "watchlist"` vs the key `"watchlists"`; `TaskAssignmentModel.collection_name = "task_details"` vs `"task_assignments"`. So a helper must **not** derive the routing key from `cls.collection_name`.
- **Two live bugs already noted in §1.5:** the label wipe on every task update, and the `"updated_by"` key at `task_assignment_repository.py:512`. Plus `update_executor` (`:273-283`) silently carries `"is_active": current_assignment.is_active` and re-sources `assignee_id` from the executor where its three identical twins hardcode `False` — correct for that site, invisible against three near-identical neighbours. And `deactivate_by_task_id` (`:308-330`) syncs exactly one row for a Mongo `update_many`, because its local named `active_assignments` comes from `get_by_task_id` → `find_one`.

**Proposed abstractions.**

```python
# todo/repositories/common/dual_write.py
logger = logging.getLogger(__name__)
_service = EnhancedDualWriteService()        # one instance, so sync_failures accumulates

def sync_to_postgres(collection_name: str, mongo_id: str,
                     payload: Mapping[str, Any] | None = None, *,
                     operation: str = "create", action: str = "") -> bool:
    """Push one write to Postgres. Never raises; logs and returns False on failure."""

def sync_model_to_postgres(collection_name: str, model, *, operation="create", action="") -> bool:
    return sync_to_postgres(collection_name, str(model.id),
                            payload_for(collection_name, model), operation=operation, action=action)


# todo/models/postgres/mapping.py
@dataclass(frozen=True)
class EntityMap:
    collection: str                 # dual-write routing key ("watchlists", "task_assignments")
    document: type                  # pydantic Document
    model: type                     # Django model
    fields: dict[str, F]            # postgres column -> F(source, cast, default)
    def to_postgres(self, data: dict, mongo_id: str) -> dict: ...

REGISTRY: dict[str, EntityMap] = {m.collection: m for m in ENTITIES}

def objectid_str(v): return str(v) if v else None      # ONE answer for nullable FKs
def enum_value(v):   return v.value if hasattr(v, "value") else v
def payload_for(collection_name: str, model) -> dict: ...
```

**Sketch.**

```python
# todo/models/postgres/mapping.py
TEAM = EntityMap("teams", TeamModel, PostgresTeam, {
    "name": F("name"), "description": F("description"), "invite_code": F("invite_code"),
    "poc_id":     F("poc_id",     cast=objectid_str),
    "created_by": F("created_by", cast=objectid_str),
    "updated_by": F("updated_by", cast=objectid_str),
    "is_deleted": F("is_deleted", default=False),
    "created_at": F("created_at"), "updated_at": F("updated_at"),
})
USER_ROLE = EntityMap("user_roles", UserRoleModel, PostgresUserRole, {
    "user_id":   F("user_id",   cast=objectid_str),
    "role_name": F("role_name", cast=enum_value),     # unwrap now lives in exactly one layer
    "scope":     F("scope",     cast=enum_value),
    ...
})

# dual_write_service.py:31-43 and :189-235 both collapse
class DualWriteService:
    COLLECTION_MODEL_MAP = {k: e.model for k, e in REGISTRY.items()}

    def _transform_data_for_postgres(self, collection_name, data, mongo_id):
        entity = REGISTRY.get(collection_name)
        if entity is None:
            return {"mongo_id": mongo_id, "sync_status": SyncStatus.SYNCED,
                    "sync_error": None, **self._transform_generic_data(data)}
        return entity.to_postgres(data, mongo_id)

# the test that would have caught the phantom columns, `permissions`, and the seven bad finders
@pytest.mark.parametrize("m", REGISTRY.values(), ids=lambda m: m.collection)
def test_every_mapped_column_exists(m):
    cols = {f.name for f in m.model._meta.get_fields()}
    assert set(m.fields) <= cols, f"{m.collection}: {set(m.fields) - cols}"
```

**Call sites after.**

```python
# todo/repositories/team_repository.py:27-48 — 22 lines become 1
        sync_model_to_postgres("teams", team)

# todo/repositories/audit_log_repository.py:18-42 — 25 lines become 1
        sync_model_to_postgres("audit_logs", audit_log)

# todo/repositories/user_team_details_repository.py:56-65 — 10 lines become 1
        sync_to_postgres("user_team_details", str(document["_id"]),
                         operation="delete", action="deletion")

# todo/repositories/task_assignment_repository.py:272-293 — the override becomes visible
        cls._sync_assignment(current_assignment, updated_by=user_id, action="executor change",
                             is_active=current_assignment.is_active,
                             assignee_id=executor_id, user_type="user")
```

**Explicitly rejected sub-proposal:** do **not** generate the pydantic `Document` and the Django model from one schema. `PyObjectId` vs `CharField(24)`, `DeferredDetailsModel` vs a OneToOne table, and `List[PyObjectId]` vs the `PostgresTaskLabel` junction cannot come from one declaration without per-entity branching, and a model factory fights Django's migration autodetector. Extract only the Django-model ↔ transform layer.

**Sequencing within this item.** (1) Introduce `objectid_str`/`enum_value` and use them inside the existing eleven methods — this alone forces the empty-string/`None` split to be decided once. (2) Convert the ten mechanical entities to `FIELD_MAPS`. (3) Leave `tasks` last, as a hand-written entry with an `extra=` hook for the synthetic `labels` key, and fix the label wipe there. (4) Only then repoint the 21 repository call sites; migrating the transforms piecemeal writes NULLs silently, because each currently reads whatever key convention its matching repository happens to emit. The routing-key switch (`cls.collection_name` vs the literals) **must land in one commit** with the map-key rename, or sync breaks for `watchlist` and `task_details`. These strings are never persisted — `_record_sync_failure` keeps them in an in-memory list — so no stored data needs migrating whichever spelling wins.

---

## 4. The rest of the table, in brief

**10 — ObjectId validation as a type (23 sites, ~100 lines).** Seven different error strings answer one condition: `ValidationErrors.INVALID_OBJECT_ID` (`messages.py:64`, used by 5 of 23), three hand-rolled f-strings in `dto/task_assignment_dto.py:17/:24/:38`, `ValidationErrors.INVALID_TASK_ID_FORMAT`, `ApiErrors.INVALID_TASK_ID`, and a bare literal `"Invalid task_id"` at `views/watchlist.py:174`. So `POST /watchlist`, `GET /watchlist?task_id=`, and `POST /task-assignments` return three different 400 bodies for the identical malformed id. Inside one file, `ObjectIdValidatorMixin.validate_object_id` (`models/team.py:10-17`) *rejects* `None` and returns the value unconverted, while `TeamModel.validate_object_id` twenty lines below (`:37-43`) *accepts* `None` and returns an `ObjectId` — same name, shadowed, opposite semantics, and `UserTeamDetailsModel` (`:61-63`) resolves through the MRO to the mixin. Proposed: `todo/serializers/fields.py::ObjectIdField(serializers.CharField)` + `object_id_list_field()`, and `todo/models/common/pyobjectid.py::StrObjectId` for the DTO layer. The three model-layer validators (`models/task_assignment.py:29-35`, `team.py:37-43`, `team_creation_invite_code.py:25-31`) are **dead** — with V1-style `@validator` at default `pre=False`, `PyObjectId.validate` has already run — so those are deletions, not extractions. Preserve the mixin's raise-on-`None` for `UserTeamDetailsModel`'s four fields before removing it.

**11 — Serializer sharing (16 copies, ~142 lines).** `CreateTaskSerializer` and `UpdateTaskSerializer` redeclare seven fields with incompatible constraints: `title` is `required=True, allow_blank=False` with **no** `max_length` on create and `required=False, allow_blank=True, max_length=255` on update, so a 300-character title is accepted on POST and rejected on PATCH. `timezone` is required on one and optional on the other while both `validate()` bodies enforce the same rule. `assignee` is three flat fields on create and an opaque `DictField` on update, so the update path silently drops the `team_id` the create path stores. The dueAt/timezone cross-field validator is copied with two behavioural divergences: create raises a scalar (`{"timezone": <str>}`) and update a list (`{"timezone": [<str>]}`) for the identical failure, and create's `try` wraps only `ZoneInfo(...)` while update's wraps the comparison too — so a `ZoneInfoNotFoundError` during comparison is a clean 400 on PATCH and a 500 on POST. Both share the same unfixed hole: `ZoneInfo("")` raises `ValueError`, not `ZoneInfoNotFoundError`. Proposed: `todo/serializers/task_fields.py::TaskWriteSerializer`, a nested `AssigneeSerializer`, `todo/serializers/validators.py::validate_due_at_in_timezone(due_at, timezone_str) -> dict[str, list[str]]`, and `TaskStatus.choices()` / `TaskPriority.choices()` on the enums (the comprehension is written five times, four with `.name` and one with `.value`; `CaseInsensitiveChoiceField` exists but is applied to exactly one field on one endpoint, so `GET /tasks?status=todo` succeeds while `POST /tasks {"status":"todo"}` is a 400). Four of the five `user_type in ["user","team"]` checks are unreachable behind an already-declared `Literal`/`ChoiceField`; the one that *does* run (`update_task_serializer.py:74-75`) is the one whose list and message have the two words in the opposite order.

**12 — `AuditService.record` (13 sites, ~78 lines).** Thirteen free-text action strings with no constants module, `"assigned_to_team"` written from two different layers (`task_assignment_service.py:86-93` and `task_assignment_repository.py:429-435`), and three id-coercion styles including a raw string at `views/task_assignment.py:250`. Only `team_service.py:515` defends a missing actor. `team_service.py:461` passes `details={"added_member_id": member_id}` to a model with no `details` field — silently discarded. `create_team` writes one `team_created` row and no per-member rows, while `add_team_members` writes one per member, so members added at creation have no audit trail. Proposed: `todo/constants/audit.py::AuditAction(str, Enum)` and `todo/services/audit_service.py::AuditService.record(action, *, performed_by, task_id=None, team_id=None, **fields)` with one `_oid()` coercion. Adding a real `details: dict | None` field to `AuditLogModel` is a prerequisite. Pairs with `TeamService._add_members` (finding 27), which would fold the row creation, role assignment and audit write into one unit and let the dead `role_id=DEFAULT_ROLE_ID` be deleted rather than enshrined.

**13 — `MongoRepository` primitives (22 sites, ~160 lines).** `insert()` with a per-class `timestamp_fields` declaration (nine create methods; `WatchlistRepository.create` is the drifted copy on every axis — no `mode="json"`, no `exclude_none`, needs a `doc.pop("_id")` no sibling needs, and assigns a `str` into a `PyObjectId` field). `find_one_model(model_cls, filter, *, document_hook=None)` for the five `find_one`→model finders (`RoleRepository` routes through a `_document_to_model` hook that coerces the scope enum; `TeamRepository` calls the constructor directly and wraps everything in `except Exception: return None`, collapsing "absent" and "malformed"). `find_models(...)` for the four list reads in `UserTeamDetailsRepository`, two of which issue the *same* query for overlapping data. Make `UserRepository` a `MongoRepository` subclass — it is the only Mongo repository that is not, so it forgoes caching and constructs a `DatabaseManager()` on each of five calls, and its hand-typed `"users"` literal (plus `"user_team_details"` at `user_team_details_repository.py:7`) bypasses the model's `collection_name`. Do **not** bake `except Exception: return []` into the shared helper — keep it at whichever call sites genuinely want to degrade, since `team_service` currently reads `[]` as "no members" rather than "read failed".

**14 — Sync-service and migration plumbing (20 copies, ~370 lines).** `PostgresSyncService._sync_labels_table` (`:128-180`) and `_sync_roles_table` (`:182-228`) are the same 50-line routine with the nouns swapped; the soft-delete filter is written twice per entity and inconsistently (`_get_mongo_collection_count` branches on `if collection_name == "labels"` at `:100-104`, and each sync method repeats the filter inline). `sync_all_tables` at `:37-40` is *already* a table-driven list — the author intended this to be data. `DualWriteService.create/update/delete_document` repeat the model guard and failure tail three times, with three different answers to "the row is not there". `EnhancedDualWriteService` bolts a feature flag onto a base written without one by repeating the same five-line guard four times, then routes around its own overrides in `_batch_operations_sync` (`:73-77`) — evidence the flag belongs on the base. The two migration seeders diverge functionally: labels validate the model and then insert the **raw** dict (`db/migrations.py:105-111`), roles insert the validated `model_dump` (`:189-192`). `migrate_labels` and `migrate_roles` both call the same argument-less `run_all_migrations()`, so they do identical work despite their names, and one wraps output in `self.style.SUCCESS` while the other does not. `sync_postgres_tables --force` is declared, printed, and passed nowhere.

**15 — Team membership authority (8 sites, ~92 lines) — blocked on item 4.** Five non-equivalent implementations of "is this user an active member of this team", reading three different queries plus one that reads a different collection entirely (`UserRoleService.has_role`, which disagrees whenever `_assign_user_role` swallowed a failure at `team_service.py:179-184`). Three error messages for one condition. Compounding it, `team_service.py` imports **two different classes both named `UserTeamDetailsRepository`** — from `repositories.team_repository` at line 7 and from `repositories.user_team_details_repository` at line 504 — over the same collection, with **opposite delete semantics** (soft `is_active=False` + dual-write update vs hard `delete_one` + dual-write delete) and different read predicates (one filters `is_active`, one does not). Proposed: one class in `todo/repositories/user_team_details_repository.py` exposing both operations under honest names (`deactivate_membership`, `purge_membership`) plus one `find_membership(user_id, team_id, *, active_only=True)`, re-exported from `team_repository` for the existing import path; and `todo/services/team_membership_service.py::TeamMembershipService.{is_member, require_member}` as the single authority. **Do not start this before the id-encoding migration** — consolidating the query shape first will grant or revoke access on real data. Test patch targets must move with it (`tests/unit/services/test_team_service.py:264,289`; `tests/unit/repositories/test_user_repository.py:100`).

**16 — Test fixtures and assertion helpers (~150 copies, ~1,700 lines).** The largest raw surface, and the one whose extraction most directly de-risks every other item, because the client-visible changes above all land as edits to these assertions. Highest-value pieces, in order: `assertApiError(response, *, status, message, title, source=None, detail=None, error_count=None)` (10 sites, and the three integration 404 copies never assert `statusCode` while the two unit copies do); `assertGetTasksCalled(...)` (the seven-kwarg blob repeated 13 times, six with the literal `"updatedAt"` and two with `SORT_FIELD_UPDATED_AT`, seven hardcoding `limit=20` where the settings value is read elsewhere); `seed_task` / `seed_task_assignment` on `AuthenticatedMongoTestCase` (four integration setUps seeding `task_details` with **three different id encodings** — all-str, all-ObjectId, and a hybrid); `AuthCookieMixin.authenticate()` (five copies, four of which re-type the user dict and all four drop `"picture"` from the shared fixture, so unit-test tokens carry a different claim set than integration tokens); `make_task_model`/`make_task_dto`/`make_team_dto`/`make_create_task_dto` factories; `stub_serializer(mock_cls, ...)` (11 sites in two competing idioms in one file); `MongoCollectionTestCase` (four hand-written `tearDown`s where `addCleanup` would do; one of four drops `spec=Collection`). Also: 12 redundant `delete_many({})` calls in setUps that the base class already wipes, four empty `setUp` overrides, and two byte-identical duplicate tests (`test_watchlist_check.py:45-62` vs `:111-128`; `test_auth.py:32-45` vs `:47-61`). Two repository "permission denied" tests (`test_task_repository.py:355-363`, `:509-517`) build a full mock scaffold and then `raise PermissionError(...)` **inside** the `assertRaises` block, never invoking the method under test — routing them through a shared `assert_permission_denied(tc, call, ...)` helper that takes a callable forces them to name the code they claim to test, and is expected to make them fail. That failure is the deliverable.

---

## 5. Quick wins

Small, self-contained, low-risk. None depends on any of the above.

**Deletions (no abstraction, just remove):**
- `views/task.py:90-99` — the unreachable second `if profile` branch. Decide first whether `exclude_none=True` was intended (finding 8).
- `exception_handler.py:98-113, :114-129, :130-145, :192-200` — four unreachable branches (findings 70, 94, 133).
- `exceptions/global_exception_handler.py:16-36` — the `handle_exceptions` decorator, zero callers; and `GlobalExceptionHandler.handle_validation_error` (`:57-61`), never called, so role validation errors take the generic 500 path (76, 146).
- `messages.py:94-95` — shadowed `TOKEN_EXPIRED` / `TOKEN_INVALID` bindings (78, 104, 145).
- `dto/task_assignment_dto.py:57-68` — `TaskAssignmentResponseDTO` (21, 65).
- `dto/user_dto.py:13-18, :21-23` — `UserSearchDTO` (zero importers) and `UsersDTO` (64).
- `dto/update_team_dto.py`, `AddTeamMemberDTO`, `dto/team_creation_invite_code_dto.py`'s unused half — three DTOs with no importers outside test patch strings (62, 63).
- `services/dual_write_service.py:360-396` — `_sync_task_assignment_update`, unreferenced, writing six phantom columns (48).
- `todo/repositories/postgres_repository.py` — 304 lines, one commit, zero importers, seven broken field names. Delete rather than refactor (38, 39, 42, 43, 91).
- `models/{role,user_role,task,task_assignment}.py` — four character-identical re-declarations of `Document`'s `id` field; and `ser_enum="value"`, not a valid pydantic `ConfigDict` key, in three configs (54).
- `services/task_service.py:462-540` — `update_task_with_assignee`, no production caller (137).

**One-line collapses:**
- `views/team.py:506-511` — three consecutive `except` clauses with byte-identical bodies become one tuple-catch: `except (NotTeamAdminException, CannotRemoveTeamPOCException, CannotRemoveOwnerException) as e:` (12).
- `exception_handler.py:226-248` — two adjacent branches with byte-identical bodies, behind a `_is_invalid_object_id(exc)` predicate. The four pydantic models raise `f"Invalid ObjectId: {v}"`, which matches neither of the two hardcoded literals at `:239` and falls through to a 500 (106).
- `messages.py` — one `SEARCH_QUERY_EMPTY` definition instead of two classes plus a hardcoded third at `user_service.py:102` (79, 145).
- `services/user_role_service.py:86-87` — a bare `except Exception: return False` with no logging in `has_role`, which gates `_validate_is_user_team_admin` (`team_service.py:532`) and `_validate_is_user_team_member` (`:544`). An infrastructure error becomes a silent permission denial with no trace. Add the log line.

**Small extractions:**
- `todo/middlewares/permissions.py::IsAdminEmail(BasePermission)` — replaces two byte-identical `_check_authorization` methods and two byte-identical 403 blocks in `views/team_creation_invite_code.py`, and makes `VerifyTeamCreationInviteCodeView`'s missing gate a visible decision rather than an invisible omission. Preserve the `if user_email and ...` truthiness guard: `ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "").split(",")` yields `['']` when unset. Note the 403 body changes shape, and confirm `request.user_email` is populated before permission checks run (7, 101, 147).
- `todo/utils/cookie_utils.py::{auth_cookie_kwargs, set_access_cookie, clear_auth_cookies}` — two `_get_cookie_config` methods differing on exactly one key: `views/auth.py:140` reads `COOKIE_HTTPONLY` from settings, `middlewares/jwt_auth.py:141` hardcodes `True`. The same access cookie carries different flags depending on whether it was minted at login or silently refreshed. `COOKIE_PATH` (`settings/base.py:152`) has no readers. The delete config omits `secure`/`httponly`/`samesite`, so the clearing cookie does not match the set cookie (95, 142).
- `todo/views/schema_params.py::{task_id_param, team_id_param, user_id_param, role_id_param}` — 17 `OpenApiParameter.PATH` blocks. **Documentation-only:** the verifier refuted the claimed drift (drf-spectacular forces `required: true` on path parameters regardless, and `type=str` vs `OpenApiTypes.STR` both render `type: string`; `schema.yaml` is not self-inconsistent). Use factories, not constants, since four descriptions are genuinely per-handler (5).
- `todo/utils/task_status_utils.py::effective_task_status(status, deferred_details)` — the "deferred overrides stored status" rule in two DTO mappers, both comparing a stored `deferredTill` against `datetime.now(timezone.utc)` with no tzinfo normalisation (while `defer_task` normalises before writing at `task_service.py:559-560`) and no `None` guard, so a naive datetime raises `TypeError` in both (29).
- `todo/services/team_service.py::get_team_or_raise` + `todo/constants/messages.py::ApiErrors.TEAM_NOT_FOUND_GENERIC` — the byte-identical three-line team-lookup-and-404 at `views/team.py:355-357` and `:401-403`, the only two team endpoints that call `TeamRepository.get_by_id` directly from the view, thereby bypassing whatever `TeamService` applies (11).
- `todo/dto/responses/api_success_response.py::ApiSuccessResponse` + `success_envelope(...)` — the hand-built `{statusCode, message, data}` envelope at `views/auth.py:48-54, :176-182` and `views/user.py:64-71, :79-85, :113-118`, with `statusCode` present on the 404 branch and absent from the two 200 branches eleven and forty-nine lines later, and four conventions for where the status lives. The asymmetry is structural: `ApiErrorResponse` exists and has no success counterpart (13).
- `models/postgres/*` — three sites missing `mode="json"` on the response dump (`role.py:109`, `:141`, `user.py:116`). This changes datetime rendering on those payloads — corrective, but a real API change.

**Verify-and-fix, not extractions:**
- `wsgi.py:14` points `DJANGO_SETTINGS_MODULE` at `todo_project.settings`, a directory with no `__init__.py`. Masked only because `production.Dockerfile:22` sets the variable and `.coveragerc` excludes `wsgi.py`.
- `configure.py` maps no `TEST` environment, so `settings/test.py` — the only module setting `DUAL_WRITE_ENABLED = False` — is unreachable through `manage.py`; its behaviour is instead re-derived by `TESTING` sniffing at `base.py:125`.
- `settings/staging.py` re-affirms `DEBUG = True`, so staging serves debug tracebacks and, through the view-layer fallbacks, echoes `str(e)` to clients.
- `settings/base.py:134` reads `REFRESH_LIFETIME` in the TESTING branch and `:142` reads `REFRESH_TOKEN_LIFETIME` in the production branch. `.env.example:15`, `.github/workflows/test.yml:23` and `.github/workflows/deploy.yml:67` all supply the **first** spelling. The operator-configured refresh-token lifetime is discarded in every real deployment (96).
- `views/team.py:492` — `print(f"DEBUG: RemoveTeamMemberView.delete called ...")` writes to stdout; `views/task_assignment.py:223-235` — `print()` + `traceback.print_exc()`.
- `middlewares/team_access_middleware.py:37` forwards a `None` user id into a role query whose `user_id=None` shape means "all users in the team" at `user_role_service.py:108`.
- `repositories/team_repository.py` `add_user_to_team` reactivates an inactive membership in place with `update_one` and performs **no dual-write at all**, so Postgres keeps `is_active=False`.

---

## 6. Suggested sequencing

Each wave is chosen so that the next one gets cheaper, and so that no wave changes behaviour that a later wave depends on.

**Wave 0 — the live defects, fixed in place (½ day, no extraction).**
The fourteen items in §1.5 that are one- to three-line edits: move the `@extend_schema` block off `_handle_validation_errors` at `team.py:469` onto `delete` at `:491`; redact `data["team"]["invite_code"]` at `team.py:85` (or go straight to item 3); add the `settings.DEBUG` guard at `task.py:437`; fix `AuthErrorMessages.INVALID_TOKEN` → `TOKEN_INVALID` at `jwt_auth.py:118`; add a non-template `AUTHENTICATION_FAILED_TITLE`; delete the shadowed constants at `messages.py:94-95`; add `status=` at `views/user_role.py:94`. Plus the deletions in §5. These are not refactors and should not wait for one.

**Wave 1 — the error contract (items 1 and 5; the `assertApiError` helper from item 16).**
Do this first because it is upstream of everything else. Six later opportunities — the service envelope factories, the typed exceptions, the repository failure policy, the middleware, the role subtree, and every test assertion — currently express failure by hand-building a response, and each of them would otherwise carry its own copy of the envelope decision into its own extraction.

Order inside the wave: (a) delete the four unreachable handler branches and adopt their intended bodies; (b) introduce `validation_error_response` / `api_error_response` and migrate the 19 validation and 500 sites; (c) introduce `ApiError` + `server_error`/`repository_error` in the services; (d) collapse the two `UserNotFoundException` classes and add `TeamNotFoundException` / `TaskAssignmentNotFoundException`, landing that **together with** narrowing the `team_service.py:169-170` and `:478-479` catch-alls; (e) only then delete the per-view `try/except` blocks, once `team.py:171-177` (404) and `team.py:300-317` (400) raise typed exceptions instead of bare `ValueError`s. Extract `assertApiError` before (b) so the client-visible envelope changes are reviewable in one place rather than across 10 assertion sites.

**Wave 2 — DTO mappers and the invite-code leak (items 3 and 7).**
Cheap, independent of Wave 1, and a prerequisite for the team work: `TeamDTO.from_model` touches the same five construction sites as the `invite_code` redaction, and `TaskAssignmentDTO.from_model` is the natural home for `resolve_assignee`, which Wave 3 needs. Doing these before the team-membership work means `TeamService` methods shrink to one or two lines each and the subsequent membership refactor is a smaller diff.

**Wave 3 — the task write path and pagination (items 2, 6, 11).**
Item 2 is the highest ratio in the audit after Wave 1 and touches almost exclusively one file. It becomes materially easier after Wave 1, because `_get_task_for_write` can raise cleanly instead of each caller deciding how to render the failure. Item 6 spans serializers + services + views and should land as one change so the documented cap and the enforced cap become the same constant; item 11 (`TaskWriteSerializer`, `AssigneeSerializer`, `validate_due_at_in_timezone`) overlaps its serializer half and is best done in the same pass. Item 10 (`ObjectIdField`) also belongs here — item 11's `AssigneeSerializer` wants it, and it subsumes several small validation findings.

**Wave 4 — id normalisation, then membership (items 4 and 15).**
Item 4 first as a pure helper (fixing the cursor-exhaustion bug on the way), then the **data migration to one encoding**, and only then item 15. Consolidating the membership query shape before the encodings agree will grant or revoke access on real data. `to_object_id`'s narrowed `except (InvalidId, TypeError)` is a real behaviour change; land it with tests on both the ObjectId-stored and string-stored cases. Item 13 (`MongoRepository` primitives) can ride along here, since it touches the same files.

**Wave 5 — the Postgres side (items 8, then 9, then 14).**
Item 8 first, in three commits: (i) the abstract bases as a verified no-op, `makemigrations` producing only index renames; (ii) the corrected `save()`; (iii) the `active_unique` constraint plus its data migration to reconcile duplicate inactive rows. Item 9 depends on item 8 existing so the registry has one target shape, and internally follows the four-step order in §3.9. Item 14 (`_sync_collection`, `_write`, the seeders, the commands) is easiest once the registry exists, because `_sync_collection` can read its per-entity config from it.

**Wave 6 — the test suite (item 16), continuously.**
The fixture and factory work should be pulled forward wherever a wave touches the tests it duplicates, rather than batched. The two repository "permission denied" tests should be routed through `assert_permission_denied` during Wave 3, and are expected to break; the sort-matrix consolidation should follow item 2.

---

## 7. Deliberately not worth doing

These were proposed during the audit and **rejected on verification**. They are recorded so they are not re-proposed.

| Proposal | Why not |
|---|---|
| `error_response(status_code, message, detail=None)` for the ~30 ad-hoc `{"detail"}`/`{"error"}`/`{"message"}` dicts | Fails "helper with more parameters than the duplication saves": three parameters replacing a statement that already has two arguments, saving zero lines and needing per-caller branching (which key? array or not? envelope or bare dict?). This is an API-contract decision, versioned, not a refactor. The real items inside it are constants (`ApiErrors.UNAUTHORIZED_TITLE` exists and none of the three authorization strings use it) and bugs (`views/user_role.py:94` returning HTTP 200; `views/task_assignment.py:237` leaking `str(e)`). |
| `success_response(model, status_code, *, exclude_none=False)` for the ~17 `Response(data=x.model_dump(mode="json"), ...)` calls | The idiomatic one-liner. A three-parameter helper replacing a two-argument call saves no lines and hides that the response is a JSON-mode dump. It does not fix the cited problems either — the three missing `mode="json"` sites are two-character edits, and the envelope inconsistency needs a contract decision, not a wrapper. |
| Shared `get_user_dtos_by_ids` | Only two of five sites even perform a per-id fetch into a `UserDTO`, and they build different field sets. A shared function would branch per caller on missing-user policy (raise / skip / placeholder), return shape (DTO / dict / `UsersDTO`) and field set. The real items are bugs: `task_service.py:162-163` raises on a deleted user so one deleted account fails an entire task serialisation; `user_service.py:50-52` constructs the wrong DTO; `label_service.py:94` hardcodes `name="User"`. |
| `@swallow_and_log(default=..., action=...)` for the six `except Exception → falsy` blocks in `UserRoleService` | Two arguments replacing two argument-shaped lines — break-even — while hiding control flow and making the return type opaque. The real problem is an undecided failure contract (`UserRoleService` swallows; `RoleService` raises for the same class of failure), and deduplicating would freeze it. Fix the silent bare `except` at `user_role_service.py:86-87` instead. |
| Shared `_role_to_dict` mapper | Two lines of genuine overlap; the surrounding loops do different things (flatten vs group-by-user). A shared mapper would either widen a response payload or take a field-selection parameter. |
| `live_filter(extra)` soft-delete wrapper | The "four spellings" are four **different collections' real field names** (`isDeleted`, `is_deleted`, `isActive`, `is_active`) — schema naming, not drifting copies of one predicate, and unreconcilable without a data migration. What remains is a single dict key inside structurally unrelated queries. The sibling-method inconsistencies (`WatchlistRepository.get_by_user_and_task` vs `get_watchlisted_tasks`; `TaskRepository.get_by_id` vs `delete_by_id`) are correctness bugs to file separately. |
| `skip_for(page, limit)` and a shared `$facet` helper | `(page - 1) * limit` is one expression. The two `$facet` pipelines are not near-identical: label's data branch is three stages, watchlist's is ~fifteen including five `$lookup`s. A helper taking the pipeline as a parameter is a helper whose parameter carries all the variation. |
| Deduplicating the `collection_name` `__init_subclass__` guard between `Document` and `MongoRepository` | Four lines, two copies, zero drift, incompatible metaclass situations (pydantic `BaseModel` + `ABC` vs plain `ABC`). A new module existing to hold one four-line hook costs more than the duplication. Separately, the guard does not cover `UserRepository` anyway — addressed by item 13. |
| A `MongoRefField` alias and re-extracting the Django audit fields | Double-counts item 8, and the `CharField(max_length=24)` half is 44 independent column declarations describing 44 different references — 44 migration entries and a non-standard field class to save 14 characters a line. (The finder's arithmetic was also wrong: there are 8 `updated_at` declarations, not 10.) |
| A generic `PaginatedResponse[T]` with `items: List[T]` | Destroys the endpoint-specific OpenAPI component names that `views/*.py` reference via `OpenApiResponse(response=...)`, and the proposed remedy — per-endpoint aliases — restores the field names it just removed. The genuinely extractable piece (the three near-identical `_build_pagination_links` pairs) is already item 6. |
| Collapsing the serializer/DTO double validation | The unit of claimed duplication is a one-line constructor call plus paired field declarations. Neither option is an abstraction — one is "delete the DTO validators", the other "delete the serializers", both per-endpoint redesigns, and a `parse_body(request, DTOClass)` wrapper would forfeit drf-spectacular's `request=` schema generation. The real item is deleting three unreachable DTOs. |
| `reject_if_past(value, *, tz=None, granularity="instant"\|"date")` | `granularity` exists purely to branch per caller. The null guards did **not** diverge for no reason — each matches its own field declaration (`DeferTaskSerializer.deferredTill` is required; `UpdateTaskSerializer.startedAt` is `allow_null=True`). The substantive observation — that `dueAt` is judged as a calendar date in the caller's timezone while `deferredTill`/`startedAt` are judged as UTC instants — is a product decision, and its `dueAt` half is already item 11. |
| Unifying the three "who is the current user" idioms | One-line attribute reads over the same attribute; the abstraction (`get_current_user_info`) already exists and the watchlist sites already use it. Rewriting ~20 `request.user_id` sites is churn. The real items are bugs: an advertised `Optional` return that no caller handles, and `team_access_middleware.py:37` forwarding `None`. |
| A single `validate_task_id` shared across the util, serializer and view layers | Each site **must** raise a different type to work at all — a DRF field validator must raise `serializers.ValidationError` for DRF to collect it; the util's contract is `ValueError(ApiErrorResponse(...))`; the view needs a `Response`. Per-caller branching on exception type is disqualifying. The real item is the constant duplication (`ApiErrors.INVALID_TASK_ID` vs `ValidationErrors.INVALID_TASK_ID_FORMAT` vs two inline literals), covered in §5. |
| Consolidating the per-environment settings modules | Excluded declarative configuration — `from .base import *` plus one `DEBUG` assignment is the standard Django split-settings layout, and the proposal is a deletion, not an extraction. `configure.py:16-26` and `wsgi.py:14` are not near-identical (a mapping function vs a hardcoded literal). The real items are the `wsgi.py` bug, the unreachable `test.py`, and staging's `DEBUG = True`. |
| A `MiddlewareTestCase` with `make_request(**attrs)` and a shared `assertRejected` | Two copies, ~2 genuinely shared lines. A shared `make_request` setting `path`, `COOKIES` and `user_id` together would silently pre-populate attributes each middleware does not read, so a middleware reading the wrong attribute would find it already set and the test would pass. `assertRejected` accepting either envelope key cannot catch an endpoint emitting the wrong one. The `message`/`detail` inconsistency is a production contract decision, not something a fixture should paper over. |
| A `CollectionNameContractMixin` for the `collection_name` validation tests | The class bodies are not interchangeable: `Document` needs `collection_name: ClassVar[str] = 123` (pydantic rejects an unannotated attribute before the check runs); `MongoRepository` needs the unannotated form. The mixin would need a per-subclass namespace-and-annotations hook plus a base class plus a message template — four parameters to share three short tests. |
| Refactoring the `Postgres*Repository` finders / get-one-or-None blocks | The whole module is unreachable dead code — zero importers, single commit, never wired up. Delete it (§5) rather than abstracting it. The nine one-line delegations are out of scope anyway, and the proposed per-subclass `user_field = "user_id"` attribute trades one line of code for one line of configuration. |

Two more, drawn from the findings themselves rather than the rejections: `views/task.py:90-99` is a **deletion, not an extraction** — do not build a helper to make the two `model_dump` variants shareable. And `DualWriteService._require_model`/`_fail` (finding 31) and `run_steps` (finding 89) are genuine but marginal: worth doing when those files are next touched, not as standalone commits.