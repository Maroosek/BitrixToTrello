import logging
import time
from urllib.parse import parse_qs
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Query, Depends
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import requests

import config
from BitrixTrello import (
    fetch_bitrix_users,
    get_workspace_members,
    build_user_map,
    fetch_bitrix_projects,
    _build_board_map_from_trello,
    build_card_description,
    _extract_bitrix_id_from_card,
    get_board_cards,
    get_board_members,
    add_card,
    update_card,
    add_member_to_board,
    STATUS_MAP,
    WORKSPACE_ID,
    bitrix_call,
    tasks_and_members_sync,
    refresh_today_tasks,
    full_sync,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bitrix24 → Trello Sync",
    description="""
## Bitrix24 → Trello synchronisation API

### Authentication
All manual trigger endpoints (`/sync_tasks`, `/refresh_tasks`, `/full_sync_bitrix`)
require a `token` query parameter matching the configured `API_Token`.

Bitrix24 webhook endpoint (`POST /webhook/bitrix/task`) authenticates via
`auth[application_token]` in the form body sent automatically by Bitrix24.

### Sync modes
| Endpoint | Description |
|---|---|
| `GET /full_sync_bitrix` | Creates missing boards/columns, syncs all tasks and members |
| `GET /sync_tasks` | Syncs tasks + members — boards must already exist |
| `GET /refresh_tasks` | Syncs only tasks changed today (fast, incremental) |
| `POST /webhook/bitrix/task` | Real-time single-task upsert triggered by Bitrix24 event |
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

EXPECTED_TOKEN: str = config.Token.API_Token


# ─────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────

def _parse_form_body(raw: bytes) -> dict[str, str]:
    """
    Parses application/x-www-form-urlencoded body sent by Bitrix24.
    Returns a flat dict (first value of each key).
    """
    parsed = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {k: v[0] for k, v in parsed.items()}


def _validate_webhook_token(fields: dict[str, str]) -> bool:
    """
    Validates the Bitrix24 webhook application token from a parsed form body.
    Bitrix encodes it as 'auth[application_token]'.
    """
    return fields.get("auth[application_token]", "") == EXPECTED_TOKEN


def _require_query_token(
    token: str = Query(..., description="API token for authorisation"),
) -> None:
    """
    FastAPI dependency — validates the `token` query parameter.
    Raises HTTP 403 if the token is missing or incorrect.
    """
    if token != EXPECTED_TOKEN:
        logger.warning("Invalid token in request")
        raise HTTPException(status_code=403, detail="Invalid token")


# ─────────────────────────────────────────────
# Bitrix24 task helper
# ─────────────────────────────────────────────

def fetch_single_bitrix_task(task_id: int) -> Optional[dict]:
    """
    Fetches a single task from Bitrix24 by ID.
    Returns the task dict or None if not found / error.
    """
    result = bitrix_call("tasks.task.get.json", {"taskId": task_id})
    if "error" in result:
        logger.error("Bitrix error fetching task %s: %s", task_id, result["error"])
        return None
    task = result.get("result", {}).get("task")
    if not task:
        logger.warning("Task %s not found in Bitrix24 response", task_id)
    return task


def upsert_single_task(task: dict, workspace_id: str = WORKSPACE_ID) -> dict:
    """
    Syncs a single Bitrix24 task to the matching Trello board.

    Steps:
      1. Build user map (Bitrix ↔ Trello).
      2. Find the Trello board that corresponds to the task's GROUP_ID.
      3. Fetch existing cards on that board; locate card by Bitrix task ID.
      4. Create or update the card as needed.
      5. Ensure the responsible user is a board member.

    Returns a summary dict: {action, task_id, group_id, board, card_id}.
    """
    bitrix_task_id = str(task.get("id", ""))
    group_id       = str(task.get("groupId", task.get("GROUP_ID", "0")))

    if group_id == "0":
        return {"action": "skipped", "reason": "ungrouped task", "task_id": bitrix_task_id}

    # 1. Users
    bitrix_users   = fetch_bitrix_users()
    trello_members = get_workspace_members(workspace_id)
    user_map       = build_user_map(bitrix_users, trello_members)

    # 2. Find matching board
    all_projects = fetch_bitrix_projects(with_members=False)
    project      = next((p for p in all_projects if str(p["ID"]) == group_id), None)

    if not project:
        return {
            "action":   "skipped",
            "reason":   f"no Bitrix project for GROUP_ID={group_id}",
            "task_id":  bitrix_task_id,
            "group_id": group_id,
        }

    board_map = _build_board_map_from_trello([project], workspace_id)

    if group_id not in board_map:
        return {
            "action":   "skipped",
            "reason":   f"no matching Trello board for project '{project.get('NAME')}'",
            "task_id":  bitrix_task_id,
            "group_id": group_id,
        }

    data     = board_map[group_id]
    lists    = data["lists"]
    board    = data["trello"]
    board_id = board["id"]

    # 3. Build card fields
    status_id    = str(task.get("status", "1"))
    list_id      = lists.get(status_id, lists["1"])
    title        = (task.get("title", "") or "").strip() or f"Task #{bitrix_task_id}"
    description  = build_card_description(task, bitrix_users)
    start        = task.get("dateStart") or None
    due          = task.get("closedDate") or None
    due_complete = status_id == "5"
    trello_member = user_map.get(str(task.get("responsibleId", "")))

    # 4. Find existing card
    existing_cards_raw = get_board_cards(board_id)
    existing = next(
        (c for c in existing_cards_raw if _extract_bitrix_id_from_card(c) == bitrix_task_id),
        None,
    )

    board_member_ids: set[str] = {m["id"] for m in get_board_members(board_id)}
    action  = "unchanged"
    card_id = existing["id"] if existing else None

    if existing is None:
        card    = add_card(
            list_id=list_id,
            name=title,
            description=description,
            start=start,
            due=due,
            due_complete=due_complete,
            member_id=trello_member,
        )
        card_id = card["id"]
        action  = "created"
        logger.info("Created card for task %s on board '%s'", bitrix_task_id, board["name"])

    else:
        changed = (
            existing.get("name")              != title        or
            existing.get("desc")              != description  or
            existing.get("idList")            != list_id      or
            existing.get("due")               != due          or
            existing.get("start")             != start        or
            bool(existing.get("dueComplete")) != due_complete
        )
        if changed:
            update_card(
                card_id=existing["id"],
                name=title,
                description=description,
                start=start,
                due=due,
                due_complete=due_complete,
                list_id=list_id if existing.get("idList") != list_id else None,
                member_id=trello_member,
            )
            action = "updated"
            logger.info("Updated card for task %s on board '%s'", bitrix_task_id, board["name"])
        else:
            logger.info("Card for task %s unchanged, skipping", bitrix_task_id)

    # 5. Ensure responsible is a board member
    if trello_member and trello_member not in board_member_ids:
        try:
            add_member_to_board(board_id, trello_member)
        except requests.exceptions.HTTPError as e:
            logger.warning("Could not add member %s to board: %s", trello_member, e)

    return {
        "action":   action,
        "task_id":  bitrix_task_id,
        "group_id": group_id,
        "board":    board["name"],
        "card_id":  card_id,
    }


# ─────────────────────────────────────────────
# Manual trigger routes (token via query param)
# ─────────────────────────────────────────────

@app.get(
    "/sync_tasks",
    summary="Sync tasks + board members",
    description=(
        "Syncs all tasks and board members from Bitrix24 to Trello. "
        "Boards and columns must already exist — this endpoint does **not** create new boards. "
        "Requires a valid `token` query parameter."
    ),
    tags=["Manual triggers"],
    dependencies=[Depends(_require_query_token)],
)
async def route_sync_tasks():
    tasks_and_members_sync()
    return {"ok": True, "action": "tasks_and_members_sync"}


@app.get(
    "/refresh_tasks",
    summary="Refresh today's changed tasks",
    description=(
        "Fetches only tasks with `ACTIVITY_DATE >= today` from Bitrix24 and upserts "
        "them to the relevant Trello boards. Much faster than a full sync. "
        "Requires a valid `token` query parameter."
    ),
    tags=["Manual triggers"],
    dependencies=[Depends(_require_query_token)],
)
async def route_refresh_tasks():
    refresh_today_tasks()
    return {"ok": True, "action": "refresh_today_tasks"}


@app.get(
    "/full_sync_bitrix",
    summary="Full sync (creates boards if missing)",
    description=(
        "Full synchronisation: creates any missing Trello boards and columns, "
        "syncs all Bitrix24 group members to boards, then upserts all tasks. "
        "This is the slowest operation — use sparingly. "
        "Requires a valid `token` query parameter."
    ),
    tags=["Manual triggers"],
    dependencies=[Depends(_require_query_token)],
)
async def route_full_sync():
    full_sync()
    return {"ok": True, "action": "full_sync"}


# ─────────────────────────────────────────────
# Bitrix24 real-time webhook
# ─────────────────────────────────────────────

@app.post(
    "/webhook/bitrix/task",
    summary="Bitrix24 task event webhook",
    description=(
        "Receives `ONTASKUPDATE` and `ONTASKADD` events from Bitrix24. "
        "Bitrix sends `application/x-www-form-urlencoded` with `auth[application_token]` "
        "for authentication and `data[FIELDS_AFTER][ID]` for the task ID. "
        "The task is fetched from Bitrix24 and upserted to the matching Trello board."
    ),
    tags=["Webhooks"],
)
async def bitrix_task_webhook(request: Request):
    raw_body = await request.body()
    fields   = _parse_form_body(raw_body)

    if not _validate_webhook_token(fields):
        logger.warning("Invalid application_token in webhook request")
        raise HTTPException(status_code=403, detail="Invalid application token")

    event       = fields.get("event", "")
    task_id_str = (
        fields.get("data[FIELDS_AFTER][ID]")
        or fields.get("data[FIELDS_BEFORE][ID]")
    )

    logger.info("Received event=%s task_id=%s", event, task_id_str)

    if not task_id_str:
        logger.error("No task ID found in webhook payload: %s", fields)
        raise HTTPException(status_code=400, detail="Missing task ID in payload")

    try:
        task_id = int(task_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid task ID: {task_id_str!r}")

    task = fetch_single_bitrix_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found in Bitrix24")

    result = upsert_single_task(task)
    logger.info("Upsert result: %s", result)

    return {"ok": True, "event": event, **result}


# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────

@app.get(
    "/health",
    summary="Health check",
    description="Returns HTTP 200 with a timestamp. Use to verify the server is running.",
    tags=["Health"],
)
async def health():
    return {"status": "ok", "ts": int(time.time())}


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=False)