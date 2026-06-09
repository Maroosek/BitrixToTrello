# import requests
# import config
# import time
# from typing import Optional
#
# TRELLO_API_KEY = config.ConfigTrello.TRELLO_API_KEY
# TRELLO_TOKEN = config.ConfigTrello.TRELLO_TOKEN
# BASE_URL = config.ConfigTrello.BASE_URL
# BITRIX_URL = config.ConfigBitrix.BITRIX_URL
#
# STATUS_MAP = {
#     "1": "Nowe",
#     "2": "Oczekujące",
#     "3": "W trakcie",
#     "4": "Do kontroli",
#     "5": "Zakończone",
#     "6": "Odłożone",
# }
#
# # Kolejność kolumn na tablicy Trello
# KOLEJNOSC_STATUSOW = ["1", "2", "3", "4", "5", "6"]
#
#
# def _auth() -> dict:
#     return {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN}
#
#
# # ─────────────────────────────────────────────
# # TRELLO – helpers
# # ─────────────────────────────────────────────
#
# def utworz_tablice(nazwa: str, opis: str = "", workspace_id: Optional[str] = None) -> dict:
#     payload = {**_auth(), "name": nazwa, "desc": opis, "defaultLists": "false"}
#     if workspace_id:
#         payload["idOrganization"] = workspace_id
#         payload["prefs_permissionLevel"] = "org"
#     resp = requests.post(f"{BASE_URL}/boards", params=payload)
#     resp.raise_for_status()
#     tablica = resp.json()
#     print(f"✅ Tablica: '{tablica['name']}' | {tablica['shortUrl']}")
#     return tablica
#
#
# def utworz_liste(board_id: str, nazwa: str) -> dict:
#     resp = requests.post(
#         f"{BASE_URL}/lists",
#         params={**_auth(), "name": nazwa, "idBoard": board_id},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# def dodaj_zadanie(list_id: str, nazwa: str, opis: str = "", termin: Optional[str] = None, member_id: Optional[str] = None) -> dict:
#     payload = {**_auth(), "idList": list_id, "name": nazwa, "desc": opis}
#     if termin:
#         payload["due"] = termin
#     if member_id:
#         payload["idMembers"] = member_id
#     resp = requests.post(f"{BASE_URL}/cards", params=payload)
#     resp.raise_for_status()
#     return resp.json()
#
# def pobierz_id_uzytkownika(username: str) -> str:
#     """Pobiera ID użytkownika na podstawie jego username (@nazwa)."""
#     resp = requests.get(
#         f"{BASE_URL}/members/{username}",
#         params={**_auth(), "fields": "id,fullName,username"},
#     )
#     resp.raise_for_status()
#     member = resp.json()
#     print(f"👤 {member['fullName']} (@{member['username']}) → ID: {member['id']}")
#     return member["id"]
#
# # ─────────────────────────────────────────────
# # BITRIX – pobieranie zadań
# # ─────────────────────────────────────────────
#
# def bitrix_call(method: str, params: dict = None) -> dict:
#     if params is None:
#         params = {}
#     url = f"{BITRIX_URL}{method}"
#     for attempt in range(1, 6):
#         try:
#             resp = requests.post(url, json=params, timeout=30)
#             resp.raise_for_status()
#             result = resp.json()
#             if result.get("error") == "QUERY_LIMIT_EXCEEDED":
#                 raise requests.exceptions.RequestException("QUERY_LIMIT_EXCEEDED")
#             return result
#         except requests.exceptions.RequestException as e:
#             print(f"⚠️  Próba {attempt}/5: {e}")
#             if attempt < 5:
#                 time.sleep(4)
#             else:
#                 print("❌ Nie udało się połączyć z Bitrix24.")
#                 return {"error": str(e)}
#
#
# def pobierz_zadania_bitrix(group_id: int = 57) -> list[dict]:
#     """
#     Pobiera wszystkie zadania z grupy Bitrix24 z paginacją.
#     Zwraca listę słowników z polami: id, title, description, status.
#     """
#     zadania = []
#     start = 0
#
#     print(f"📥 Pobieram zadania z Bitrix24 (GROUP_ID={group_id})...")
#
#     while True:
#         result = bitrix_call("tasks.task.list.json", {
#             "filter": {"GROUP_ID": group_id},
#             "select": ["ID", "TITLE", "DESCRIPTION", "STATUS"],
#             "start": start,
#         })
#
#         if "error" in result:
#             print(f"❌ Błąd Bitrix: {result['error']}")
#             break
#
#         batch = result.get("result", {}).get("tasks", [])
#         if not batch:
#             break
#
#         zadania.extend(batch)
#         print(f"  Pobrano {len(zadania)} zadań...")
#
#         # Bitrix zwraca 50 rekordów na stronę; next wskazuje offset
#         total = result.get("result", {}).get("total", 0)
#         start += 50
#         if start >= total:
#             break
#
#         time.sleep(0.3)  # Drobne opóźnienie, żeby nie przekroczyć limitu
#
#     print(f"✅ Łącznie pobrano {len(zadania)} zadań z Bitrix24.")
#     return zadania
#
#
# # ─────────────────────────────────────────────
# # GŁÓWNA LOGIKA – synchronizacja
# # ─────────────────────────────────────────────
#
# def synchronizuj_bitrix_do_trello(
#         nazwa_tablicy: str = "TEST – zadania ciągłe",
#         group_id: int = 57,
#         workspace_id: Optional[str] = None,
# ) -> None:
#     """
#     1. Pobiera zadania z Bitrix24 (group_id).
#     2. Tworzy tablicę Trello z kolumnami wg STATUS_MAP.
#     3. Wrzuca każde zadanie do odpowiedniej kolumny.
#     """
#
#     # 1. Pobierz zadania z Bitrix
#     zadania = pobierz_zadania_bitrix(group_id)
#     if not zadania:
#         print("ℹ️  Brak zadań do synchronizacji.")
#         return
#
#     # 2. Utwórz tablicę Trello
#     tablica = utworz_tablice(
#         nazwa=nazwa_tablicy,
#         opis=f"Automatyczna synchronizacja z Bitrix24 – Grupa {group_id}",
#         workspace_id=workspace_id,
#     )
#     board_id = tablica["id"]
#
#     # 3. Utwórz kolumny (listy) w kolejności wg KOLEJNOSC_STATUSOW
#     print("\n📋 Tworzę kolumny...")
#     listy: dict[str, str] = {}  # status_id → trello list_id
#     for status_id in KOLEJNOSC_STATUSOW:
#         nazwa_listy = STATUS_MAP[status_id]
#         lista = utworz_liste(board_id, nazwa_listy)
#         listy[status_id] = lista["id"]
#         print(f"  ✅ Kolumna: '{nazwa_listy}'")
#
#     # 4. Dodaj zadania do odpowiednich kolumn
#     print(f"\n📌 Dodaję {len(zadania)} zadań do Trello...")
#     dodane = 0
#     pominięte = 0
#
#     for z in zadania:
#         status_id = str(z.get("status", "1"))
#         list_id = listy.get(status_id, listy["1"])  # fallback → "Nowe"
#
#         tytul = z.get("title", "").strip() or f"Zadanie #{z.get('id')}"
#         opis_raw = z.get("description", "") or ""
#
#         # Opis karty: dodaj ID Bitrix jako odniesienie
#         opis = f"**Bitrix ID:** {z.get('id')}\n\n{opis_raw}".strip()
#
#         karta = dodaj_zadanie(list_id=list_id, nazwa=tytul, opis=opis)
#         print(f"  ✅ [{STATUS_MAP.get(status_id, '?')}] {tytul}")
#         dodane += 1
#
#         time.sleep(0.1)  # Trello API limit: ~100 req/10s
#
#     print(f"\n{'=' * 50}")
#     print(f"✅ Synchronizacja zakończona!")
#     print(f"   Tablica : {tablica['shortUrl']}")
#     print(f"   Dodano  : {dodane} zadań")
#     if pominięte:
#         print(f"   Pominięto: {pominięte} zadań")
#
#
# if __name__ == "__main__":
#     # # 1. Utwórz tablicę
#     # # tablica = utworz_tablice(nazwa="Mój projekt", opis="Tablica testowa")
#     # tablica = utworz_tablice(nazwa="Mój projekt", opis="Tablica testowa", workspace_id="6a18200189faaa62c4e14a49")
#     #
#     # board_id = tablica["id"]
#     #
#     # # Aby dodać zadanie, potrzebujesz ID listy na tej tablicy.
#     # # Jeśli stworzyłeś tablicę z defaultLists=false, dodaj listę ręcznie:
#     # resp = requests.post(
#     #     f"{BASE_URL}/lists",
#     #     params={**_auth(), "name": "Do zrobienia", "idBoard": board_id},
#     # )
#     # resp.raise_for_status()
#     # list_id = resp.json()["id"]
#     #
#     # # 2. Dodaj zadanie
#     # zadanie = dodaj_zadanie(
#     #     list_id=list_id,
#     #     nazwa="Pierwsze zadanie",
#     #     opis="Opis dodany przez API.",
#     #     termin="2025-12-31T23:59:00.000Z",
#     # )
#     # card_id = zadanie["id"]
#     #
#     # # 3. Zaktualizuj zadanie
#     # aktualizuj_zadanie(
#     #     card_id=card_id,
#     #     nazwa="Zaktualizowane zadanie",
#     #     opis="Nowy opis.",
#     # )
#
#     #print(pobierz_tablice())
#
#     # # 4. Usuń zadanie
#     # usun_zadanie(card_id=card_id)
#     #
#     # # 5. Usuń tablicę
#     # usun_tablice(board_id=board_id)
#
#     # synchronizuj_bitrix_do_trello(
#     #     nazwa_tablicy="TEST – zadania ciągłe",
#     #     group_id=57,
#     #     workspace_id="6a18200189faaa62c4e14a49"
#     # )
#
#
#     #dodaj_zadanie(list_id="6a26916467860ca7ab87b4c7", nazwa="Zadanie TEST MARKO ALE MAKS", member_id="6a1825ce4fbae5d6d6ca4705")
#     #uid = pobierz_id_uzytkownika("maksymilianpyc")
import requests
import config
import time
from typing import Optional

TRELLO_API_KEY = config.ConfigTrello.TRELLO_API_KEY
TRELLO_TOKEN = config.ConfigTrello.TRELLO_TOKEN
BASE_URL = config.ConfigTrello.BASE_URL
BITRIX_URL = config.ConfigBitrix.BITRIX_URL

STATUS_MAP = {
    "1": "Nowe",
    "2": "Oczekujące",
    "3": "W trakcie",
    "4": "Do kontroli",
    "5": "Zakończone",
    "6": "Odłożone",
}

KOLEJNOSC_STATUSOW = ["1", "2", "3", "4", "5", "6"]


def _auth() -> dict:
    return {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN}


# ─────────────────────────────────────────────
# TRELLO – tablice
# ─────────────────────────────────────────────

def utworz_tablice(nazwa: str, opis: str = "", workspace_id: Optional[str] = None) -> dict:
    """Tworzy tablicę Trello, opcjonalnie w podanym workspace'ie."""
    payload = {**_auth(), "name": nazwa, "desc": opis, "defaultLists": "false"}
    if workspace_id:
        payload["idOrganization"] = workspace_id
        payload["prefs_permissionLevel"] = "org"
    resp = requests.post(f"{BASE_URL}/boards", params=payload)
    resp.raise_for_status()
    tablica = resp.json()
    print(f"  ✅ Tablica: '{tablica['name']}' | {tablica['shortUrl']}")
    return tablica


def pobierz_tablice_trello() -> list[dict]:
    """
    Pobiera wszystkie tablice konta z ich workspace_id.
    Zwraca listę słowników: {id, name, idOrganization}.
    """
    resp = requests.get(
        f"{BASE_URL}/members/me/boards",
        params={**_auth(), "fields": "id,name,idOrganization,shortUrl"},
    )
    resp.raise_for_status()
    return resp.json()


def utworz_liste(board_id: str, nazwa: str) -> dict:
    """Tworzy kolumnę (listę) na tablicy."""
    resp = requests.post(
        f"{BASE_URL}/lists",
        params={**_auth(), "name": nazwa, "idBoard": board_id},
    )
    resp.raise_for_status()
    return resp.json()


# ─────────────────────────────────────────────
# TRELLO – zadania (karty)
# ─────────────────────────────────────────────

def dodaj_zadanie(
    list_id: str,
    nazwa: str,
    opis: str = "",
    termin: Optional[str] = None,
    member_id: Optional[str] = None,
) -> dict:
    """Dodaje kartę (zadanie) do wskazanej listy."""
    payload = {**_auth(), "idList": list_id, "name": nazwa, "desc": opis}
    if termin:
        payload["due"] = termin
    if member_id:
        payload["idMembers"] = member_id
    resp = requests.post(f"{BASE_URL}/cards", params=payload)
    resp.raise_for_status()
    return resp.json()


def pobierz_id_uzytkownika(username: str) -> str:
    """Pobiera ID użytkownika Trello na podstawie jego @username."""
    resp = requests.get(
        f"{BASE_URL}/members/{username}",
        params={**_auth(), "fields": "id,fullName,username"},
    )
    resp.raise_for_status()
    member = resp.json()
    print(f"👤 {member['fullName']} (@{member['username']}) → ID: {member['id']}")
    return member["id"]


# ─────────────────────────────────────────────
# BITRIX – pobieranie danych z paginacją (co 50)
# ─────────────────────────────────────────────

def bitrix_call(method: str, params: dict = None) -> dict:
    """Wywołuje metodę Bitrix24 REST API z retry (5 prób)."""
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
            print(f"⚠️  Próba {attempt}/5: {e}")
            if attempt < 5:
                time.sleep(4)
            else:
                print("❌ Nie udało się połączyć z Bitrix24.")
                return {"error": str(e)}


def pobierz_projekty_bitrix() -> list[dict]:
    """
    Pobiera wszystkie grupy/projekty z Bitrix24 z paginacją co 50.
    Zwraca listę słowników: {ID, NAME, DESCRIPTION}.
    """
    projekty = []
    start = 0
    print("📥 Pobieram projekty z Bitrix24...")

    while True:
        result = bitrix_call("sonet_group.get.json", {
            "select": ["ID", "NAME", "DESCRIPTION"],
            "start": start,
        })

        if "error" in result:
            print(f"❌ Błąd Bitrix: {result['error']}")
            break

        batch = result.get("result", [])
        if not batch:
            break

        projekty.extend(batch)
        print(f"  Pobrano {len(projekty)} projektów...")

        total = result.get("total", 0)
        start += 50
        if start >= total:
            break

        time.sleep(0.3)

    print(f"✅ Łącznie pobrano {len(projekty)} projektów z Bitrix24.")
    return projekty


def pobierz_zadania_bitrix(group_id: int) -> list[dict]:
    """
    Pobiera wszystkie zadania z konkretnej grupy Bitrix24 z paginacją co 50.
    Zwraca listę słowników: {id, title, description, status}.
    """
    zadania = []
    start = 0
    print(f"  📥 Pobieram zadania dla GROUP_ID={group_id}...")

    while True:
        result = bitrix_call("tasks.task.list.json", {
            "filter": {"GROUP_ID": group_id},
            "select": ["ID", "TITLE", "DESCRIPTION", "STATUS"],
            "start": start,
        })

        if "error" in result:
            print(f"  ❌ Błąd Bitrix: {result['error']}")
            break

        batch = result.get("result", {}).get("tasks", [])
        if not batch:
            break

        zadania.extend(batch)
        print(f"    Pobrano {len(zadania)} zadań...")

        total = result.get("result", {}).get("total", 0)
        start += 50
        if start >= total:
            break

        time.sleep(0.3)

    return zadania


# ─────────────────────────────────────────────
# INIT – tworzenie projektów i zadań
# ─────────────────────────────────────────────

def init_utworz_projekty(
    workspace_id: Optional[str] = None,
) -> dict[str, dict]:
    """
    Pobiera wszystkie projekty z Bitrix24 i tworzy dla każdego tablicę w Trello.

    Returns:
        Słownik {bitrix_group_id → {"bitrix": projekt, "trello": tablica, "listy": {status_id: list_id}}}.
    """
    projekty_bitrix = pobierz_projekty_bitrix()
    if not projekty_bitrix:
        print("ℹ️  Brak projektów w Bitrix24.")
        return {}

    print(f"\n📋 Tworzę {len(projekty_bitrix)} tablic w Trello...")
    mapa: dict[str, dict] = {}

    for projekt in projekty_bitrix:
        group_id = str(projekt["ID"])
        nazwa    = projekt.get("NAME", f"Projekt #{group_id}")
        opis     = projekt.get("DESCRIPTION", "")

        tablica = utworz_tablice(nazwa=nazwa, opis=opis, workspace_id=workspace_id)
        board_id = tablica["id"]

        # Utwórz kolumny statusów
        listy: dict[str, str] = {}
        for status_id in KOLEJNOSC_STATUSOW:
            lista = utworz_liste(board_id, STATUS_MAP[status_id])
            listy[status_id] = lista["id"]
            time.sleep(0.1)

        mapa[group_id] = {
            "bitrix": projekt,
            "trello": tablica,
            "listy":  listy,
        }
        time.sleep(0.2)

    print(f"✅ Utworzono {len(mapa)} tablic.")
    return mapa


def init_utworz_zadania(mapa_projektow: dict[str, dict]) -> int:
    """
    Dla każdego projektu w mapie pobiera zadania z Bitrix24
    i tworzy odpowiednie karty w Trello.

    Args:
        mapa_projektow: Wynik zwrócony przez init_utworz_projekty().

    Returns:
        Łączna liczba dodanych kart.
    """
    lacznie = 0

    for group_id, dane in mapa_projektow.items():
        listy   = dane["listy"]
        tablica = dane["trello"]
        print(f"\n📌 Projekt: '{tablica['name']}' (GROUP_ID={group_id})")

        zadania = pobierz_zadania_bitrix(int(group_id))
        if not zadania:
            print("  ℹ️  Brak zadań.")
            continue

        for z in zadania:
            status_id = str(z.get("status", "1"))
            list_id   = listy.get(status_id, listy["1"])

            tytul    = z.get("title", "").strip() or f"Zadanie #{z.get('id')}"
            opis_raw = z.get("description", "") or ""
            opis     = f"**Bitrix ID:** {z.get('id')}\n\n{opis_raw}".strip()

            dodaj_zadanie(list_id=list_id, nazwa=tytul, opis=opis)
            print(f"    ✅ [{STATUS_MAP.get(status_id, '?')}] {tytul}")
            lacznie += 1
            time.sleep(0.1)

    print(f"\n✅ Łącznie dodano {lacznie} zadań.")
    return lacznie


def init_synchronizacja(workspace_id: Optional[str] = None) -> None:
    """
    Punkt wejścia całej inicjalizacji:
      1. Pobiera projekty z Bitrix24 i tworzy tablice Trello.
      2. Pobiera zadania dla każdego projektu i tworzy karty.
      3. Porównuje tablice Trello z projektami Bitrix24.
    """
    print("=" * 55)
    print("🚀 START inicjalizacji Bitrix24 → Trello")
    print("=" * 55)

    # 1. Projekty → tablice
    mapa = init_utworz_projekty(workspace_id=workspace_id)
    if not mapa:
        return

    # 2. Zadania → karty
    init_utworz_zadania(mapa)

    # 3. Weryfikacja zgodności
    porownaj_tablice_z_bitrixem(mapa)


# ─────────────────────────────────────────────
# WERYFIKACJA – porównanie tablic z projektami
# ─────────────────────────────────────────────

def porownaj_tablice_z_bitrixem(mapa_projektow: dict[str, dict]) -> None:
    """
    Porównuje tablice istniejące w Trello z projektami pobranymi z Bitrix24.
    Wypisuje:
      - tablice zgodne (nazwa pasuje do projektu Bitrix)
      - tablice w Trello bez odpowiednika w Bitrix24
      - projekty Bitrix24 bez tablicy w Trello
    """
    print("\n" + "=" * 55)
    print("🔍 Weryfikacja zgodności tablic Trello ↔ Bitrix24")
    print("=" * 55)

    tablice_trello = pobierz_tablice_trello()

    # Zbiór nazw projektów Bitrix (lowercase do porównania)
    nazwy_bitrix: dict[str, str] = {
        dane["bitrix"]["NAME"].strip().lower(): group_id
        for group_id, dane in mapa_projektow.items()
    }

    # Nazwy tablic utworzonych przez init (po trello id)
    trello_ids_z_mapy = {
        dane["trello"]["id"] for dane in mapa_projektow.values()
    }

    zgodne       = []
    tylko_trello = []

    for t in tablice_trello:
        nazwa_lower = t["name"].strip().lower()
        if t["id"] in trello_ids_z_mapy or nazwa_lower in nazwy_bitrix:
            zgodne.append(t)
        else:
            tylko_trello.append(t)

    # Projekty Bitrix bez tablicy w Trello
    nazwy_trello_lower = {t["name"].strip().lower() for t in tablice_trello}
    tylko_bitrix = [
        dane["bitrix"]
        for dane in mapa_projektow.values()
        if dane["bitrix"]["NAME"].strip().lower() not in nazwy_trello_lower
    ]

    print(f"\n✅ Zgodne ({len(zgodne)}):")
    for t in zgodne:
        print(f"   [{t['id']}] {t['name']}")

    print(f"\n⚠️  Tylko w Trello – brak w Bitrix24 ({len(tylko_trello)}):")
    for t in tylko_trello:
        print(f"   [{t['id']}] {t['name']}")

    print(f"\n❌ Tylko w Bitrix24 – brak tablicy Trello ({len(tylko_bitrix)}):")
    for p in tylko_bitrix:
        print(f"   [GROUP_ID={p['ID']}] {p['NAME']}")

    print()


# ─────────────────────────────────────────────
# URUCHOMIENIE
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_synchronizacja(workspace_id="6a18200189faaa62c4e14a49")