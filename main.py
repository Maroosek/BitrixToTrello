import requests
import config
import time
from typing import Optional

TRELLO_API_KEY = config.ConfigTrello.TRELLO_API_KEY
TRELLO_TOKEN = config.ConfigTrello.TRELLO_TOKEN
BASE_URL = config.ConfigTrello.BASE_URL
BITRIX_URL = config.ConfigBitrix.BITRIX_URL
WORKSPACE_ID = "6a18200189faaa62c4e14a49"

STATUS_MAP = {
    "1": "Nowe",
    "2": "Oczekujące",
    "3": "W trakcie",
    "4": "Do kontroli",
    "5": "Zakończone",
    "6": "Odłożone",
}

STATUS_ORDER = ["1", "2", "3", "4", "5", "6"]


def _auth() -> dict:
    return {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN}


# ─────────────────────────────────────────────
# TRELLO – boards
# ─────────────────────────────────────────────

def create_board(name: str, description: str = "", workspace_id: Optional[str] = None) -> dict:
    """Creates a Trello board, optionally inside a workspace."""
    payload = {**_auth(), "name": name, "desc": description, "defaultLists": "false"}
    if workspace_id:
        payload["idOrganization"] = workspace_id
        payload["prefs_permissionLevel"] = "org"
    resp = requests.post(f"{BASE_URL}/boards", params=payload)
    resp.raise_for_status()
    board = resp.json()
    print(f"  ✅ Board created: '{board['name']}' | {board['shortUrl']}")
    return board


def update_board(board_id: str, name: Optional[str] = None, description: Optional[str] = None) -> dict:
    """Updates name and/or description of an existing board."""
    payload = {**_auth()}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["desc"] = description
    resp = requests.put(f"{BASE_URL}/boards/{board_id}", params=payload)
    resp.raise_for_status()
    board = resp.json()
    print(f"  ✏️  Board updated: '{board['name']}'")
    return board


def get_trello_boards() -> list[dict]:
    """Returns all boards on the account: id, name, desc, idOrganization, shortUrl."""
    resp = requests.get(
        f"{BASE_URL}/members/me/boards",
        params={**_auth(), "fields": "id,name,desc,idOrganization,shortUrl"},
    )
    resp.raise_for_status()
    return resp.json()


def create_list(board_id: str, name: str) -> dict:
    """Creates a column (list) on a board."""
    resp = requests.post(
        f"{BASE_URL}/lists",
        params={**_auth(), "name": name, "idBoard": board_id},
    )
    resp.raise_for_status()
    return resp.json()


def get_board_lists(board_id: str) -> list[dict]:
    """Returns all lists (columns) on a board."""
    resp = requests.get(
        f"{BASE_URL}/boards/{board_id}/lists",
        params={**_auth(), "fields": "id,name"},
    )
    resp.raise_for_status()
    return resp.json()


def add_member_to_board(board_id: str, member_id: str, role: str = "normal") -> dict:
    """
    Adds a user to a board.
    role: 'normal' | 'admin' | 'observer' (observer requires Trello Premium)
    """
    resp = requests.put(
        f"{BASE_URL}/boards/{board_id}/members/{member_id}",
        params={**_auth(), "type": role},
    )
    resp.raise_for_status()
    print(f"  ✅ Member {member_id} added to board {board_id} as '{role}'")
    return resp.json()


# ─────────────────────────────────────────────
# TRELLO – cards (tasks)
# ─────────────────────────────────────────────

def add_card(
    list_id: str,
    name: str,
    description: str = "",
    due: Optional[str] = None,
    member_id: Optional[str] = None,
) -> dict:
    """Creates a card (task) in the given list."""
    payload = {**_auth(), "idList": list_id, "name": name, "desc": description}
    if due:
        payload["due"] = due
    if member_id:
        payload["idMembers"] = member_id
    resp = requests.post(f"{BASE_URL}/cards", params=payload)
    resp.raise_for_status()
    return resp.json()


def update_card(
    card_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    due: Optional[str] = None,
    list_id: Optional[str] = None,
    member_id: Optional[str] = None,
) -> dict:
    """Updates any fields of an existing card."""
    payload = {**_auth()}
    if name        is not None: payload["name"]      = name
    if description is not None: payload["desc"]      = description
    if due         is not None: payload["due"]       = due
    if list_id     is not None: payload["idList"]    = list_id
    if member_id   is not None: payload["idMembers"] = member_id
    resp = requests.put(f"{BASE_URL}/cards/{card_id}", params=payload)
    resp.raise_for_status()
    return resp.json()


def get_board_cards(board_id: str) -> list[dict]:
    """Returns all cards on a board: id, name, desc, idList."""
    resp = requests.get(
        f"{BASE_URL}/boards/{board_id}/cards",
        params={**_auth(), "fields": "id,name,desc,idList"},
    )
    resp.raise_for_status()
    return resp.json()


def delete_card(card_id: str) -> None:
    """Permanently deletes a card."""
    resp = requests.delete(f"{BASE_URL}/cards/{card_id}", params=_auth())
    resp.raise_for_status()
    print(f"  🗑️  Card deleted: {card_id}")


# ─────────────────────────────────────────────
# TRELLO – members
# ─────────────────────────────────────────────

def get_member_id(username: str) -> str:
    """Returns the Trello member ID for a given @username."""
    resp = requests.get(
        f"{BASE_URL}/members/{username}",
        params={**_auth(), "fields": "id,fullName,username"},
    )
    resp.raise_for_status()
    member = resp.json()
    print(f"  👤 {member['fullName']} (@{member['username']}) → ID: {member['id']}")
    return member["id"]


def get_workspace_members(workspace_id: str) -> list[dict]:
    """Returns all members of a workspace (requires admin access for email field)."""
    resp = requests.get(
        f"{BASE_URL}/organizations/{workspace_id}/members",
        params={**_auth(), "fields": "id,fullName,username,email"},
    )
    resp.raise_for_status()
    members = resp.json()
    for m in members:
        print(f"  [{m['id']}] {m['fullName']} (@{m['username']})")
    return members


def get_board_members(board_id: str) -> list[dict]:
    """Returns all members of a specific board."""
    resp = requests.get(
        f"{BASE_URL}/boards/{board_id}/members",
        params={**_auth(), "fields": "id,fullName,username"},
    )
    resp.raise_for_status()
    return resp.json()


# ─────────────────────────────────────────────
# BITRIX – base call with retry
# ─────────────────────────────────────────────

def bitrix_call(method: str, params: dict = None) -> dict:
    """Calls a Bitrix24 REST API method with up to 5 retries."""
    if params is None:
        params = {}
    url = f"{BITRIX_URL}{method}"
    for attempt in range(1, 6):
        try:
            resp = requests.post(url, json=params, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            if result.get("error") == "QUERY_LIMIT_EXCEEDED":
                raise requests.exceptions.RequestException("QUERY_LIMIT_EXCEEDED")
            return result
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  Attempt {attempt}/5: {e}")
            if attempt < 5:
                time.sleep(4)
            else:
                print("  ❌ Failed to connect to Bitrix24.")
                return {"error": str(e)}


# ─────────────────────────────────────────────
# BITRIX – users
# ─────────────────────────────────────────────

def fetch_bitrix_users() -> list[dict]:
    """
    Fetches all active Bitrix24 users with pagination (50 per page).
    Returns list of dicts: {ID, NAME, LAST_NAME}.
    """
    users = []
    start = 0
    print("📥 Fetching Bitrix24 users...")

    while True:
        result = bitrix_call("user.get.json", {
            "filter": {"ACTIVE": True},
            "select": ["ID", "NAME", "LAST_NAME"],
            "start": start,
        })

        if "error" in result:
            print(f"  ❌ Bitrix error: {result['error']}")
            break

        batch = result.get("result", [])
        if not batch:
            break

        users.extend(batch)
        print(f"  Fetched {len(users)} users...")

        total = result.get("total", 0)
        start += 50
        if start >= total:
            break

        time.sleep(0.3)

    print(f"✅ Total Bitrix24 users fetched: {len(users)}")
    return users


# ─────────────────────────────────────────────
# BITRIX – projects (groups)
# ─────────────────────────────────────────────

def fetch_group_members(group_id: int) -> list[dict]:
    """
    Returns all members of a Bitrix24 workgroup.
    Each entry contains USER_ID and ROLE ('A' = admin, 'E' = employee, 'K' = moderator).
    """
    result = bitrix_call("sonet_group.user.get.json", {"ID": group_id})

    if "error" in result:
        print(f"  ❌ Bitrix error fetching members for group {group_id}: {result['error']}")
        return []

    members = result.get("result", [])
    print(f"  👥 Group {group_id}: {len(members)} member(s)")
    return members


def fetch_bitrix_projects() -> list[dict]:
    """
    Fetches all Bitrix24 groups/projects with pagination (50 per page).
    Enriches each project with a MEMBER_IDS list (Bitrix user IDs).
    Returns list of dicts: {ID, NAME, DESCRIPTION, MEMBER_IDS}.
    """
    projects = []
    start = 0
    print("📥 Fetching Bitrix24 projects...")

    while True:
        result = bitrix_call("sonet_group.get.json", {
            "select": ["ID", "NAME", "DESCRIPTION"],
            "start": start,
        })

        if "error" in result:
            print(f"  ❌ Bitrix error: {result['error']}")
            break

        batch = result.get("result", [])
        if not batch:
            break

        projects.extend(batch)
        print(f"  Fetched {len(projects)} projects...")

        total = result.get("total", 0)
        start += 50
        if start >= total:
            break

        time.sleep(0.3)

    print(f"✅ Total Bitrix24 projects fetched: {len(projects)}")

    # Enrich each project with its member list
    print("📥 Fetching group members...")
    for project in projects:
        members = fetch_group_members(int(project["ID"]))
        project["MEMBER_IDS"] = [str(m["USER_ID"]) for m in members]
        time.sleep(0.2)

    print("✅ Group members fetched.")
    return projects


# ─────────────────────────────────────────────
# BITRIX – tasks
# ─────────────────────────────────────────────

def fetch_bitrix_tasks(group_id: int, exclude: bool = False) -> list[dict]:
    """
    Fetches all tasks for a Bitrix24 group with cursor-based pagination.
    Returns list of dicts: {id, title, description, status, createdDate,
                             closedDate, dateStart, createdBy, responsibleId}.

    Args:
        group_id: Bitrix24 group ID to filter by.
        exclude:  If True, fetches tasks where GROUP_ID != group_id (filter key '!GROUP_ID').
                  E.g. fetch_bitrix_tasks(0, exclude=True) returns all tasks not in any group.
    """
    tasks = []
    start = 0
    filter_key = "!GROUP_ID" if exclude else "GROUP_ID"
    print(f"  📥 Fetching tasks where {filter_key}={group_id}...")

    while True:
        result = bitrix_call("tasks.task.list.json", {
            "filter": {filter_key: group_id},
            "select": [
                "ID", "TITLE", "DESCRIPTION", "STATUS",
                "CREATED_DATE", "CLOSED_DATE", "DATE_START",
                "CREATED_BY", "RESPONSIBLE_ID",
            ],
            "start": start,
        })

        if "error" in result:
            print(f"  ❌ Bitrix error: {result['error']}")
            break

        batch = result.get("result", {}).get("tasks", [])
        if not batch:
            break

        tasks.extend(batch)

        # 'total' sits at root level, not inside result.result
        total      = result.get("total", 0)
        next_start = result.get("next")

        print(f"    Fetched {len(tasks)}/{total} tasks...")

        # Bitrix omits 'next' on the last page
        if next_start is None:
            break

        start = next_start
        time.sleep(0.3)

    print(f"  ✅ Total tasks fetched: {len(tasks)}")
    return tasks


# ─────────────────────────────────────────────
# USER MATCHING – Bitrix ↔ Trello
# ─────────────────────────────────────────────

_PL_CHARS = str.maketrans(
    "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
    "acelnoszzACELNOSZZ",
)


def normalize(name: str) -> str:
    """Lowercases and replaces Polish diacritics with ASCII equivalents."""
    return name.strip().lower().translate(_PL_CHARS)


def build_user_map(bitrix_users: list[dict], trello_members: list[dict]) -> dict[str, str]:
    """
    Tries to match Bitrix24 users with Trello members by full name.
    Normalizes Polish diacritics on both sides before comparing,
    so differences like 'n' vs 'ń' or 'l' vs 'ł' are handled.
    Returns dict: {bitrix_user_id → trello_member_id}.
    """
    print("\n🔗 Matching Bitrix24 users with Trello members...")

    # Build Trello lookup: normalized full name → member_id
    trello_by_name: dict[str, str] = {}
    for m in trello_members:
        key = normalize(m.get("fullName", ""))
        if key:
            trello_by_name[key] = m["id"]

    user_map: dict[str, str] = {}
    unmatched: list[str] = []

    for u in bitrix_users:
        bitrix_id = str(u["ID"])
        raw_name  = f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip()
        key       = normalize(raw_name)
        trello_id = trello_by_name.get(key)

        if trello_id:
            user_map[bitrix_id] = trello_id
            print(f"  ✅ Matched: '{raw_name}' → Trello {trello_id}")
        else:
            unmatched.append(f"{raw_name} (Bitrix ID={bitrix_id})")

    if unmatched:
        print(f"\n  ⚠️  Unmatched Bitrix users ({len(unmatched)}):")
        for name in unmatched:
            print(f"    - {name}")

    print(f"\n✅ User map built: {len(user_map)} matched, {len(unmatched)} unmatched.")
    return user_map


# ─────────────────────────────────────────────
# CARD DESCRIPTION builder
# ─────────────────────────────────────────────

def build_card_description(task: dict, bitrix_users: list[dict]) -> str:
    """
    Builds a Trello card description from a Bitrix24 task.
    Starts with the Bitrix ID, then task details on a new line.
    """
    user_lookup = {
        str(u["ID"]): f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip()
        for u in bitrix_users
    }

    created_by  = user_lookup.get(str(task.get("createdBy", "")),     task.get("createdBy",     "—"))
    responsible = user_lookup.get(str(task.get("responsibleId", "")), task.get("responsibleId", "—"))
    raw_desc    = (task.get("description", "") or "").strip()

    lines = [
        f"**Bitrix ID:** {task.get('id', '—')}",
        "",
        f"**Created by:** {created_by}",
        f"**Responsible:** {responsible}",
        f"**Created:** {task.get('createdDate', '—')}",
        f"**Started:** {task.get('dateStart', '—')}",
        f"**Closed:** {task.get('closedDate', '—')}",
    ]

    if raw_desc:
        lines += ["", "---", "", raw_desc]

    return "\n".join(lines)


# ─────────────────────────────────────────────
# INIT – boards (upsert)
# ─────────────────────────────────────────────

def init_upsert_boards(
    projects: list[dict],
    user_map: dict[str, str],
    workspace_id: Optional[str] = None,
) -> dict[str, dict]:
    """
    For each Bitrix24 project, finds an existing Trello board by name or creates a new one.
    Updates description if it differs.
    Adds matched Bitrix group members to the board.

    Returns:
        {bitrix_group_id → {"bitrix": project, "trello": board, "lists": {status_id: list_id}}}
    """
    print("\n📋 Upserting boards in Trello...")
    existing_boards = get_trello_boards()
    boards_by_name  = {b["name"].strip().lower(): b for b in existing_boards}

    board_map: dict[str, dict] = {}

    for project in projects:
        group_id = str(project["ID"])
        name     = project.get("NAME", f"Project #{group_id}").strip()
        desc     = project.get("DESCRIPTION", "") or ""
        key      = name.lower()

        if key in boards_by_name:
            board = boards_by_name[key]
            if board.get("desc", "").strip() != desc.strip():
                board = update_board(board["id"], description=desc)
            else:
                print(f"  ✔️  Board already up to date: '{name}'")
        else:
            board = create_board(name=name, description=desc, workspace_id=workspace_id)

        board_id = board["id"]

        # Ensure all status columns exist
        existing_lists = get_board_lists(board_id)
        lists_by_name  = {l["name"].strip().lower(): l["id"] for l in existing_lists}
        lists: dict[str, str] = {}

        for status_id in STATUS_ORDER:
            col_name = STATUS_MAP[status_id]
            if col_name.lower() in lists_by_name:
                lists[status_id] = lists_by_name[col_name.lower()]
            else:
                new_list = create_list(board_id, col_name)
                lists[status_id] = new_list["id"]
            time.sleep(0.05)

        # Add Bitrix group members to the Trello board
        current_board_members = {m["id"] for m in get_board_members(board_id)}
        for bitrix_user_id in project.get("MEMBER_IDS", []):
            trello_member_id = user_map.get(bitrix_user_id)
            if trello_member_id and trello_member_id not in current_board_members:
                try:
                    add_member_to_board(board_id, trello_member_id)
                    current_board_members.add(trello_member_id)
                except requests.exceptions.HTTPError as e:
                    print(f"  ⚠️  Could not add member {trello_member_id} to board '{name}': {e}")
                time.sleep(0.1)

        board_map[group_id] = {
            "bitrix": project,
            "trello": board,
            "lists":  lists,
        }
        time.sleep(0.15)

    print(f"✅ Boards upserted: {len(board_map)}")
    return board_map


# ─────────────────────────────────────────────
# INIT – tasks (upsert)
# ─────────────────────────────────────────────

def init_upsert_tasks(
    board_map: dict[str, dict],
    bitrix_users: list[dict],
    user_map: dict[str, str],
) -> int:
    """
    For each project, fetches Bitrix24 tasks and upserts them as Trello cards.
    Matches existing cards by 'Bitrix ID' in description; updates if changed, creates if new.

    Returns total number of cards created or updated.
    """
    total = 0

    for group_id, data in board_map.items():
        lists    = data["lists"]
        board    = data["trello"]
        board_id = board["id"]
        print(f"\n📌 Project: '{board['name']}' (GROUP_ID={group_id})")

        tasks = fetch_bitrix_tasks(int(group_id))
        if not tasks:
            print("  ℹ️  No tasks.")
            continue

        # Build lookup of existing cards by Bitrix ID extracted from description
        existing_cards     = get_board_cards(board_id)
        cards_by_bitrix_id: dict[str, dict] = {}
        for card in existing_cards:
            desc = card.get("desc", "") or ""
            for line in desc.splitlines():
                if line.startswith("**Bitrix ID:**"):
                    bid = line.replace("**Bitrix ID:**", "").strip()
                    cards_by_bitrix_id[bid] = card
                    break

        for task in tasks:
            bitrix_task_id = str(task.get("id", ""))
            status_id      = str(task.get("status", "1"))
            list_id        = lists.get(status_id, lists["1"])
            title          = (task.get("title", "") or "").strip() or f"Task #{bitrix_task_id}"
            description    = build_card_description(task, bitrix_users)
            due            = task.get("closedDate") or None
            trello_member  = user_map.get(str(task.get("responsibleId", "")))

            existing = cards_by_bitrix_id.get(bitrix_task_id)

            if existing:
                changed = (
                    existing.get("name")   != title       or
                    existing.get("desc")   != description or
                    existing.get("idList") != list_id
                )
                if changed:
                    update_card(
                        card_id=existing["id"],
                        name=title,
                        description=description,
                        due=due,
                        list_id=list_id,
                        member_id=trello_member,
                    )
                    print(f"    ✏️  Updated: [{STATUS_MAP.get(status_id, '?')}] {title}")
                    total += 1
                else:
                    print(f"    ✔️  No changes: {title}")
            else:
                add_card(
                    list_id=list_id,
                    name=title,
                    description=description,
                    due=due,
                    member_id=trello_member,
                )
                print(f"    ✅ Created: [{STATUS_MAP.get(status_id, '?')}] {title}")
                total += 1

            time.sleep(0.1)

    print(f"\n✅ Total cards created/updated: {total}")
    return total


# ─────────────────────────────────────────────
# COMPARE – boards vs Bitrix projects
# ─────────────────────────────────────────────

def compare_boards_with_bitrix(board_map: dict[str, dict]) -> None:
    """
    Compares existing Trello boards against Bitrix24 projects.
    Prints: matched | only in Trello | only in Bitrix24.
    """
    print("\n" + "=" * 55)
    print("🔍 Board comparison: Trello ↔ Bitrix24")
    print("=" * 55)

    all_trello_boards = get_trello_boards()
    bitrix_names      = {
        data["bitrix"]["NAME"].strip().lower(): gid
        for gid, data in board_map.items()
    }
    mapped_trello_ids = {data["trello"]["id"] for data in board_map.values()}

    matched     = []
    trello_only = []

    for b in all_trello_boards:
        if b["id"] in mapped_trello_ids or b["name"].strip().lower() in bitrix_names:
            matched.append(b)
        else:
            trello_only.append(b)

    trello_names_lower = {b["name"].strip().lower() for b in all_trello_boards}
    bitrix_only = [
        data["bitrix"]
        for data in board_map.values()
        if data["bitrix"]["NAME"].strip().lower() not in trello_names_lower
    ]

    print(f"\n✅ Matched ({len(matched)}):")
    for b in matched:
        print(f"   [{b['id']}] {b['name']}")

    print(f"\n⚠️  Trello only – no Bitrix24 project ({len(trello_only)}):")
    for b in trello_only:
        print(f"   [{b['id']}] {b['name']}")

    print(f"\n❌ Bitrix24 only – no Trello board ({len(bitrix_only)}):")
    for p in bitrix_only:
        print(f"   [GROUP_ID={p['ID']}] {p['NAME']}")
    print()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def init_sync(workspace_id: Optional[str] = WORKSPACE_ID) -> None:
    """
    Full initialisation / sync flow:
      1. Fetch Bitrix24 users and Trello workspace members; build user map.
      2. Fetch Bitrix24 projects (with member lists); upsert Trello boards and add members.
      3. Fetch tasks per project; upsert Trello cards (create or update).
      4. Compare boards for discrepancies.
    """
    print("=" * 55)
    print("🚀 Starting Bitrix24 → Trello sync")
    print("=" * 55)

    # 1. Users
    bitrix_users   = fetch_bitrix_users()
    trello_members = get_workspace_members(workspace_id)
    user_map       = build_user_map(bitrix_users, trello_members)

    # 2. Projects → boards (members fetched inside fetch_bitrix_projects)
    projects  = fetch_bitrix_projects()
    board_map = init_upsert_boards(projects, user_map=user_map, workspace_id=workspace_id)

    # 3. Tasks → cards
    init_upsert_tasks(board_map, bitrix_users, user_map)

    # 4. Comparison report
    compare_boards_with_bitrix(board_map)

    print("=" * 55)
    print("✅ Sync complete.")
    print("=" * 55)


if __name__ == "__main__":
    init_sync()