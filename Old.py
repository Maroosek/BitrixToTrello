# # import requests
# # import config
# # import time
# # from typing import Optional
# #
# # TRELLO_API_KEY = config.ConfigTrello.TRELLO_API_KEY
# # TRELLO_TOKEN = config.ConfigTrello.TRELLO_TOKEN
# # BASE_URL = config.ConfigTrello.BASE_URL
# # BITRIX_URL = config.ConfigBitrix.BITRIX_URL
# #
# # STATUS_MAP = {
# #     "1": "Nowe",
# #     "2": "Oczekujące",
# #     "3": "W trakcie",
# #     "4": "Do kontroli",
# #     "5": "Zakończone",
# #     "6": "Odłożone",
# # }
# #
# # # Kolejność kolumn na tablicy Trello
# # KOLEJNOSC_STATUSOW = ["1", "2", "3", "4", "5", "6"]
# #
# #
# # def _auth() -> dict:
# #     return {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN}
# #
# #
# # # ─────────────────────────────────────────────
# # # TRELLO – helpers
# # # ─────────────────────────────────────────────
# #
# # def utworz_tablice(nazwa: str, opis: str = "", workspace_id: Optional[str] = None) -> dict:
# #     payload = {**_auth(), "name": nazwa, "desc": opis, "defaultLists": "false"}
# #     if workspace_id:
# #         payload["idOrganization"] = workspace_id
# #         payload["prefs_permissionLevel"] = "org"
# #     resp = requests.post(f"{BASE_URL}/boards", params=payload)
# #     resp.raise_for_status()
# #     tablica = resp.json()
# #     print(f"✅ Tablica: '{tablica['name']}' | {tablica['shortUrl']}")
# #     return tablica
# #
# #
# # def utworz_liste(board_id: str, nazwa: str) -> dict:
# #     resp = requests.post(
# #         f"{BASE_URL}/lists",
# #         params={**_auth(), "name": nazwa, "idBoard": board_id},
# #     )
# #     resp.raise_for_status()
# #     return resp.json()
# #
# #
# # def dodaj_zadanie(list_id: str, nazwa: str, opis: str = "", termin: Optional[str] = None, member_id: Optional[str] = None) -> dict:
# #     payload = {**_auth(), "idList": list_id, "name": nazwa, "desc": opis}
# #     if termin:
# #         payload["due"] = termin
# #     if member_id:
# #         payload["idMembers"] = member_id
# #     resp = requests.post(f"{BASE_URL}/cards", params=payload)
# #     resp.raise_for_status()
# #     return resp.json()
# #
# # def pobierz_id_uzytkownika(username: str) -> str:
# #     """Pobiera ID użytkownika na podstawie jego username (@nazwa)."""
# #     resp = requests.get(
# #         f"{BASE_URL}/members/{username}",
# #         params={**_auth(), "fields": "id,fullName,username"},
# #     )
# #     resp.raise_for_status()
# #     member = resp.json()
# #     print(f"👤 {member['fullName']} (@{member['username']}) → ID: {member['id']}")
# #     return member["id"]
# #
# # # ─────────────────────────────────────────────
# # # BITRIX – pobieranie zadań
# # # ─────────────────────────────────────────────
# #
# # def bitrix_call(method: str, params: dict = None) -> dict:
# #     if params is None:
# #         params = {}
# #     url = f"{BITRIX_URL}{method}"
# #     for attempt in range(1, 6):
# #         try:
# #             resp = requests.post(url, json=params, timeout=30)
# #             resp.raise_for_status()
# #             result = resp.json()
# #             if result.get("error") == "QUERY_LIMIT_EXCEEDED":
# #                 raise requests.exceptions.RequestException("QUERY_LIMIT_EXCEEDED")
# #             return result
# #         except requests.exceptions.RequestException as e:
# #             print(f"⚠️  Próba {attempt}/5: {e}")
# #             if attempt < 5:
# #                 time.sleep(4)
# #             else:
# #                 print("❌ Nie udało się połączyć z Bitrix24.")
# #                 return {"error": str(e)}
# #
# #
# # def pobierz_zadania_bitrix(group_id: int = 57) -> list[dict]:
# #     """
# #     Pobiera wszystkie zadania z grupy Bitrix24 z paginacją.
# #     Zwraca listę słowników z polami: id, title, description, status.
# #     """
# #     zadania = []
# #     start = 0
# #
# #     print(f"📥 Pobieram zadania z Bitrix24 (GROUP_ID={group_id})...")
# #
# #     while True:
# #         result = bitrix_call("tasks.task.list.json", {
# #             "filter": {"GROUP_ID": group_id},
# #             "select": ["ID", "TITLE", "DESCRIPTION", "STATUS"],
# #             "start": start,
# #         })
# #
# #         if "error" in result:
# #             print(f"❌ Błąd Bitrix: {result['error']}")
# #             break
# #
# #         batch = result.get("result", {}).get("tasks", [])
# #         if not batch:
# #             break
# #
# #         zadania.extend(batch)
# #         print(f"  Pobrano {len(zadania)} zadań...")
# #
# #         # Bitrix zwraca 50 rekordów na stronę; next wskazuje offset
# #         total = result.get("result", {}).get("total", 0)
# #         start += 50
# #         if start >= total:
# #             break
# #
# #         time.sleep(0.3)  # Drobne opóźnienie, żeby nie przekroczyć limitu
# #
# #     print(f"✅ Łącznie pobrano {len(zadania)} zadań z Bitrix24.")
# #     return zadania
# #
# #
# # # ─────────────────────────────────────────────
# # # GŁÓWNA LOGIKA – synchronizacja
# # # ─────────────────────────────────────────────
# #
# # def synchronizuj_bitrix_do_trello(
# #         nazwa_tablicy: str = "TEST – zadania ciągłe",
# #         group_id: int = 57,
# #         workspace_id: Optional[str] = None,
# # ) -> None:
# #     """
# #     1. Pobiera zadania z Bitrix24 (group_id).
# #     2. Tworzy tablicę Trello z kolumnami wg STATUS_MAP.
# #     3. Wrzuca każde zadanie do odpowiedniej kolumny.
# #     """
# #
# #     # 1. Pobierz zadania z Bitrix
# #     zadania = pobierz_zadania_bitrix(group_id)
# #     if not zadania:
# #         print("ℹ️  Brak zadań do synchronizacji.")
# #         return
# #
# #     # 2. Utwórz tablicę Trello
# #     tablica = utworz_tablice(
# #         nazwa=nazwa_tablicy,
# #         opis=f"Automatyczna synchronizacja z Bitrix24 – Grupa {group_id}",
# #         workspace_id=workspace_id,
# #     )
# #     board_id = tablica["id"]
# #
# #     # 3. Utwórz kolumny (listy) w kolejności wg KOLEJNOSC_STATUSOW
# #     print("\n📋 Tworzę kolumny...")
# #     listy: dict[str, str] = {}  # status_id → trello list_id
# #     for status_id in KOLEJNOSC_STATUSOW:
# #         nazwa_listy = STATUS_MAP[status_id]
# #         lista = utworz_liste(board_id, nazwa_listy)
# #         listy[status_id] = lista["id"]
# #         print(f"  ✅ Kolumna: '{nazwa_listy}'")
# #
# #     # 4. Dodaj zadania do odpowiednich kolumn
# #     print(f"\n📌 Dodaję {len(zadania)} zadań do Trello...")
# #     dodane = 0
# #     pominięte = 0
# #
# #     for z in zadania:
# #         status_id = str(z.get("status", "1"))
# #         list_id = listy.get(status_id, listy["1"])  # fallback → "Nowe"
# #
# #         tytul = z.get("title", "").strip() or f"Zadanie #{z.get('id')}"
# #         opis_raw = z.get("description", "") or ""
# #
# #         # Opis karty: dodaj ID Bitrix jako odniesienie
# #         opis = f"**Bitrix ID:** {z.get('id')}\n\n{opis_raw}".strip()
# #
# #         karta = dodaj_zadanie(list_id=list_id, nazwa=tytul, opis=opis)
# #         print(f"  ✅ [{STATUS_MAP.get(status_id, '?')}] {tytul}")
# #         dodane += 1
# #
# #         time.sleep(0.1)  # Trello API limit: ~100 req/10s
# #
# #     print(f"\n{'=' * 50}")
# #     print(f"✅ Synchronizacja zakończona!")
# #     print(f"   Tablica : {tablica['shortUrl']}")
# #     print(f"   Dodano  : {dodane} zadań")
# #     if pominięte:
# #         print(f"   Pominięto: {pominięte} zadań")
# #
# #
# # if __name__ == "__main__":
# #     # # 1. Utwórz tablicę
# #     # # tablica = utworz_tablice(nazwa="Mój projekt", opis="Tablica testowa")
# #     # tablica = utworz_tablice(nazwa="Mój projekt", opis="Tablica testowa", workspace_id="6a18200189faaa62c4e14a49")
# #     #
# #     # board_id = tablica["id"]
# #     #
# #     # # Aby dodać zadanie, potrzebujesz ID listy na tej tablicy.
# #     # # Jeśli stworzyłeś tablicę z defaultLists=false, dodaj listę ręcznie:
# #     # resp = requests.post(
# #     #     f"{BASE_URL}/lists",
# #     #     params={**_auth(), "name": "Do zrobienia", "idBoard": board_id},
# #     # )
# #     # resp.raise_for_status()
# #     # list_id = resp.json()["id"]
# #     #
# #     # # 2. Dodaj zadanie
# #     # zadanie = dodaj_zadanie(
# #     #     list_id=list_id,
# #     #     nazwa="Pierwsze zadanie",
# #     #     opis="Opis dodany przez API.",
# #     #     termin="2025-12-31T23:59:00.000Z",
# #     # )
# #     # card_id = zadanie["id"]
# #     #
# #     # # 3. Zaktualizuj zadanie
# #     # aktualizuj_zadanie(
# #     #     card_id=card_id,
# #     #     nazwa="Zaktualizowane zadanie",
# #     #     opis="Nowy opis.",
# #     # )
# #
# #     #print(pobierz_tablice())
# #
# #     # # 4. Usuń zadanie
# #     # usun_zadanie(card_id=card_id)
# #     #
# #     # # 5. Usuń tablicę
# #     # usun_tablice(board_id=board_id)
# #
# #     # synchronizuj_bitrix_do_trello(
# #     #     nazwa_tablicy="TEST – zadania ciągłe",
# #     #     group_id=57,
# #     #     workspace_id="6a18200189faaa62c4e14a49"
# #     # )
# #
# #
# #     #dodaj_zadanie(list_id="6a26916467860ca7ab87b4c7", nazwa="Zadanie TEST MARKO ALE MAKS", member_id="6a1825ce4fbae5d6d6ca4705")
# #     #uid = pobierz_id_uzytkownika("maksymilianpyc")
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
# KOLEJNOSC_STATUSOW = ["1", "2", "3", "4", "5", "6"]
#
#
# def _auth() -> dict:
#     return {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN}
#
#
# # ─────────────────────────────────────────────
# # TRELLO – tablice
# # ─────────────────────────────────────────────
#
# def utworz_tablice(nazwa: str, opis: str = "", workspace_id: Optional[str] = None) -> dict:
#     """Tworzy tablicę Trello, opcjonalnie w podanym workspace'ie."""
#     payload = {**_auth(), "name": nazwa, "desc": opis, "defaultLists": "false"}
#     if workspace_id:
#         payload["idOrganization"] = workspace_id
#         payload["prefs_permissionLevel"] = "org"
#     resp = requests.post(f"{BASE_URL}/boards", params=payload)
#     resp.raise_for_status()
#     tablica = resp.json()
#     print(f"  ✅ Tablica: '{tablica['name']}' | {tablica['shortUrl']}")
#     return tablica
#
#
# def pobierz_tablice_trello() -> list[dict]:
#     """
#     Pobiera wszystkie tablice konta z ich workspace_id.
#     Zwraca listę słowników: {id, name, idOrganization}.
#     """
#     resp = requests.get(
#         f"{BASE_URL}/members/me/boards",
#         params={**_auth(), "fields": "id,name,idOrganization,shortUrl"},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# def utworz_liste(board_id: str, nazwa: str) -> dict:
#     """Tworzy kolumnę (listę) na tablicy."""
#     resp = requests.post(
#         f"{BASE_URL}/lists",
#         params={**_auth(), "name": nazwa, "idBoard": board_id},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# # ─────────────────────────────────────────────
# # TRELLO – zadania (karty)
# # ─────────────────────────────────────────────
#
# def dodaj_zadanie(
#     list_id: str,
#     nazwa: str,
#     opis: str = "",
#     termin: Optional[str] = None,
#     member_id: Optional[str] = None,
# ) -> dict:
#     """Dodaje kartę (zadanie) do wskazanej listy."""
#     payload = {**_auth(), "idList": list_id, "name": nazwa, "desc": opis}
#     if termin:
#         payload["due"] = termin
#     if member_id:
#         payload["idMembers"] = member_id
#     resp = requests.post(f"{BASE_URL}/cards", params=payload)
#     resp.raise_for_status()
#     return resp.json()
#
#
# def pobierz_id_uzytkownika(username: str) -> str:
#     """Pobiera ID użytkownika Trello na podstawie jego @username."""
#     resp = requests.get(
#         f"{BASE_URL}/members/{username}",
#         params={**_auth(), "fields": "id,fullName,username"},
#     )
#     resp.raise_for_status()
#     member = resp.json()
#     print(f"👤 {member['fullName']} (@{member['username']}) → ID: {member['id']}")
#     return member["id"]
#
# def dodaj_uzytkownika_do_tablicy(board_id: str, member_id: str, rola: str = "normal") -> dict:
#     """
#     Dodaje użytkownika do tablicy Trello.
#     """
#     resp = requests.put(
#         f"{BASE_URL}/boards/{board_id}/members/{member_id}",
#         params={**_auth(), "type": rola},
#     )
#     resp.raise_for_status()
#     print(f"✅ Dodano użytkownika {member_id} do tablicy {board_id} jako '{rola}'")
#     return resp.json()
#
# def pobierz_czlonkow_workspace(workspace_id: str) -> list[dict]:
#     resp = requests.get(
#         f"{BASE_URL}/organizations/{workspace_id}/members",
#         params={**_auth(), "fields": "id,fullName,username,email"},
#     )
#     resp.raise_for_status()
#     members = resp.json()
#     for m in members:
#         print(f"  [{m['id']}] {m['fullName']} (@{m['username']})")
#     return members
#
# # ─────────────────────────────────────────────
# # BITRIX – pobieranie danych z paginacją (co 50)
# # ─────────────────────────────────────────────
#
# def bitrix_call(method: str, params: dict = None) -> dict:
#     """Wywołuje metodę Bitrix24 REST API z retry (5 prób)."""
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
# def pobierz_projekty_bitrix() -> list[dict]:
#     """
#     Pobiera wszystkie grupy/projekty z Bitrix24 z paginacją co 50.
#     Zwraca listę słowników: {ID, NAME, DESCRIPTION}.
#     """
#     projekty = []
#     start = 0
#     print("📥 Pobieram projekty z Bitrix24...")
#
#     while True:
#         result = bitrix_call("sonet_group.get.json", {
#             "select": ["ID", "NAME", "DESCRIPTION"],
#             "start": start,
#         })
#
#         if "error" in result:
#             print(f"❌ Błąd Bitrix: {result['error']}")
#             break
#
#         batch = result.get("result", [])
#         if not batch:
#             break
#
#         projekty.extend(batch)
#         print(f"  Pobrano {len(projekty)} projektów...")
#
#         total = result.get("total", 0)
#         start += 50
#         if start >= total:
#             break
#
#         time.sleep(0.3)
#
#     print(f"✅ Łącznie pobrano {len(projekty)} projektów z Bitrix24.")
#     return projekty
#
#
# def pobierz_zadania_bitrix(group_id: int) -> list[dict]:
#     """
#     Pobiera wszystkie zadania z konkretnej grupy Bitrix24 z paginacją co 50.
#     Zwraca listę słowników: {id, title, description, status}.
#     """
#     zadania = []
#     start = 0
#     print(f"  📥 Pobieram zadania dla GROUP_ID={group_id}...")
#
#     while True:
#         result = bitrix_call("tasks.task.list.json", {
#             "filter": {"GROUP_ID": group_id},
#             "select": ["ID", "TITLE", "DESCRIPTION", "STATUS"],
#             "start": start,
#         })
#
#         if "error" in result:
#             print(f"  ❌ Błąd Bitrix: {result['error']}")
#             break
#
#         batch = result.get("result", {}).get("tasks", [])
#         if not batch:
#             break
#
#         zadania.extend(batch)
#         print(f"    Pobrano {len(zadania)} zadań...")
#
#         total = result.get("result", {}).get("total", 0)
#         start += 50
#         if start >= total:
#             break
#
#         time.sleep(0.3)
#
#     return zadania
#
# def fetch_users_bitrix():
#     #user.get.json?filter[ACTIVE]=T
#     users = []
#
# # ─────────────────────────────────────────────
# # INIT – tworzenie projektów i zadań
# # ─────────────────────────────────────────────
#
# def init_utworz_projekty(
#     workspace_id: Optional[str] = None,
# ) -> dict[str, dict]:
#     """
#     Pobiera wszystkie projekty z Bitrix24 i tworzy dla każdego tablicę w Trello.
#
#     Returns:
#         Słownik {bitrix_group_id → {"bitrix": projekt, "trello": tablica, "listy": {status_id: list_id}}}.
#     """
#     projekty_bitrix = pobierz_projekty_bitrix()
#     if not projekty_bitrix:
#         print("ℹ️  Brak projektów w Bitrix24.")
#         return {}
#
#     print(f"\n📋 Tworzę {len(projekty_bitrix)} tablic w Trello...")
#     mapa: dict[str, dict] = {}
#
#     for projekt in projekty_bitrix:
#         group_id = str(projekt["ID"])
#         nazwa    = projekt.get("NAME", f"Projekt #{group_id}")
#         opis     = projekt.get("DESCRIPTION", "")
#
#         tablica = utworz_tablice(nazwa=nazwa, opis=opis, workspace_id=workspace_id)
#         board_id = tablica["id"]
#
#         # Utwórz kolumny statusów
#         listy: dict[str, str] = {}
#         for status_id in KOLEJNOSC_STATUSOW:
#             lista = utworz_liste(board_id, STATUS_MAP[status_id])
#             listy[status_id] = lista["id"]
#             time.sleep(0.1)
#
#         mapa[group_id] = {
#             "bitrix": projekt,
#             "trello": tablica,
#             "listy":  listy,
#         }
#         time.sleep(0.2)
#
#     print(f"✅ Utworzono {len(mapa)} tablic.")
#     return mapa
#
#
# def init_utworz_zadania(mapa_projektow: dict[str, dict]) -> int:
#     """
#     Dla każdego projektu w mapie pobiera zadania z Bitrix24
#     i tworzy odpowiednie karty w Trello.
#
#     Args:
#         mapa_projektow: Wynik zwrócony przez init_utworz_projekty().
#
#     Returns:
#         Łączna liczba dodanych kart.
#     """
#     lacznie = 0
#
#     for group_id, dane in mapa_projektow.items():
#         listy   = dane["listy"]
#         tablica = dane["trello"]
#         print(f"\n📌 Projekt: '{tablica['name']}' (GROUP_ID={group_id})")
#
#         zadania = pobierz_zadania_bitrix(int(group_id))
#         if not zadania:
#             print("  ℹ️  Brak zadań.")
#             continue
#
#         for z in zadania:
#             status_id = str(z.get("status", "1"))
#             list_id   = listy.get(status_id, listy["1"])
#
#             tytul    = z.get("title", "").strip() or f"Zadanie #{z.get('id')}"
#             opis_raw = z.get("description", "") or ""
#             opis     = f"**Bitrix ID:** {z.get('id')}\n\n{opis_raw}".strip()
#
#             dodaj_zadanie(list_id=list_id, nazwa=tytul, opis=opis)
#             print(f"    ✅ [{STATUS_MAP.get(status_id, '?')}] {tytul}")
#             lacznie += 1
#             time.sleep(0.1)
#
#     print(f"\n✅ Łącznie dodano {lacznie} zadań.")
#     return lacznie
#
#
# def init_synchronizacja(workspace_id: Optional[str] = None) -> None:
#     """
#     Punkt wejścia całej inicjalizacji:
#       1. Pobiera projekty z Bitrix24 i tworzy tablice Trello.
#       2. Pobiera zadania dla każdego projektu i tworzy karty.
#       3. Porównuje tablice Trello z projektami Bitrix24.
#     """
#     print("=" * 55)
#     print("🚀 START inicjalizacji Bitrix24 → Trello")
#     print("=" * 55)
#
#     # 1. Projekty → tablice
#     mapa = init_utworz_projekty(workspace_id=workspace_id)
#     if not mapa:
#         return
#
#     # 2. Zadania → karty
#     init_utworz_zadania(mapa)
#
#     # 3. Weryfikacja zgodności
#     porownaj_tablice_z_bitrixem(mapa)
#
#
# # ─────────────────────────────────────────────
# # WERYFIKACJA – porównanie tablic z projektami
# # ─────────────────────────────────────────────
#
# def porownaj_tablice_z_bitrixem(mapa_projektow: dict[str, dict]) -> None:
#     """
#     Porównuje tablice istniejące w Trello z projektami pobranymi z Bitrix24.
#     Wypisuje:
#       - tablice zgodne (nazwa pasuje do projektu Bitrix)
#       - tablice w Trello bez odpowiednika w Bitrix24
#       - projekty Bitrix24 bez tablicy w Trello
#     """
#     print("\n" + "=" * 55)
#     print("🔍 Weryfikacja zgodności tablic Trello ↔ Bitrix24")
#     print("=" * 55)
#
#     tablice_trello = pobierz_tablice_trello()
#
#     # Zbiór nazw projektów Bitrix (lowercase do porównania)
#     nazwy_bitrix: dict[str, str] = {
#         dane["bitrix"]["NAME"].strip().lower(): group_id
#         for group_id, dane in mapa_projektow.items()
#     }
#
#     # Nazwy tablic utworzonych przez init (po trello id)
#     trello_ids_z_mapy = {
#         dane["trello"]["id"] for dane in mapa_projektow.values()
#     }
#
#     zgodne       = []
#     tylko_trello = []
#
#     for t in tablice_trello:
#         nazwa_lower = t["name"].strip().lower()
#         if t["id"] in trello_ids_z_mapy or nazwa_lower in nazwy_bitrix:
#             zgodne.append(t)
#         else:
#             tylko_trello.append(t)
#
#     # Projekty Bitrix bez tablicy w Trello
#     nazwy_trello_lower = {t["name"].strip().lower() for t in tablice_trello}
#     tylko_bitrix = [
#         dane["bitrix"]
#         for dane in mapa_projektow.values()
#         if dane["bitrix"]["NAME"].strip().lower() not in nazwy_trello_lower
#     ]
#
#     print(f"\n✅ Zgodne ({len(zgodne)}):")
#     for t in zgodne:
#         print(f"   [{t['id']}] {t['name']}")
#
#     print(f"\n⚠️  Tylko w Trello – brak w Bitrix24 ({len(tylko_trello)}):")
#     for t in tylko_trello:
#         print(f"   [{t['id']}] {t['name']}")
#
#     print(f"\n❌ Tylko w Bitrix24 – brak tablicy Trello ({len(tylko_bitrix)}):")
#     for p in tylko_bitrix:
#         print(f"   [GROUP_ID={p['ID']}] {p['NAME']}")
#
#     print()
#
#
# # ─────────────────────────────────────────────
# # URUCHOMIENIE
# # ─────────────────────────────────────────────
#
# if __name__ == "__main__":
#     init_synchronizacja(workspace_id="6a18200189faaa62c4e14a49")

# import requests
# import config
# import time
# from typing import Optional
#
# TRELLO_API_KEY = config.ConfigTrello.TRELLO_API_KEY
# TRELLO_TOKEN = config.ConfigTrello.TRELLO_TOKEN
# BASE_URL = config.ConfigTrello.BASE_URL
# BITRIX_URL = config.ConfigBitrix.BITRIX_URL
# WORKSPACE_ID = "6a18200189faaa62c4e14a49"
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
# STATUS_ORDER = ["1", "2", "3", "4", "5", "6"]
#
#
# def _auth() -> dict:
#     return {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN}
#
#
# # ─────────────────────────────────────────────
# # TRELLO – boards
# # ─────────────────────────────────────────────
#
# def create_board(name: str, description: str = "", workspace_id: Optional[str] = None) -> dict:
#     """Creates a Trello board, optionally inside a workspace."""
#     payload = {**_auth(), "name": name, "desc": description, "defaultLists": "false"}
#     if workspace_id:
#         payload["idOrganization"] = workspace_id
#         payload["prefs_permissionLevel"] = "org"
#     resp = requests.post(f"{BASE_URL}/boards", params=payload)
#     resp.raise_for_status()
#     board = resp.json()
#     print(f"  ✅ Board created: '{board['name']}' | {board['shortUrl']}")
#     return board
#
#
# def update_board(board_id: str, name: Optional[str] = None, description: Optional[str] = None) -> dict:
#     """Updates name and/or description of an existing board."""
#     payload = {**_auth()}
#     if name is not None:
#         payload["name"] = name
#     if description is not None:
#         payload["desc"] = description
#     resp = requests.put(f"{BASE_URL}/boards/{board_id}", params=payload)
#     resp.raise_for_status()
#     board = resp.json()
#     print(f"  ✏️  Board updated: '{board['name']}'")
#     return board
#
#
# def get_trello_boards() -> list[dict]:
#     """Returns all boards on the account: id, name, desc, idOrganization, shortUrl."""
#     resp = requests.get(
#         f"{BASE_URL}/members/me/boards",
#         params={**_auth(), "fields": "id,name,desc,idOrganization,shortUrl"},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# def create_list(board_id: str, name: str) -> dict:
#     """Creates a column (list) on a board."""
#     resp = requests.post(
#         f"{BASE_URL}/lists",
#         params={**_auth(), "name": name, "idBoard": board_id},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# def get_board_lists(board_id: str) -> list[dict]:
#     """Returns all lists (columns) on a board."""
#     resp = requests.get(
#         f"{BASE_URL}/boards/{board_id}/lists",
#         params={**_auth(), "fields": "id,name"},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# def add_member_to_board(board_id: str, member_id: str, role: str = "normal") -> dict:
#     """
#     Adds a user to a board.
#     role: 'normal' | 'admin' | 'observer' (observer requires Trello Premium)
#     """
#     resp = requests.put(
#         f"{BASE_URL}/boards/{board_id}/members/{member_id}",
#         params={**_auth(), "type": role},
#     )
#     resp.raise_for_status()
#     print(f"  ✅ Member {member_id} added to board {board_id} as '{role}'")
#     return resp.json()
#
#
# # ─────────────────────────────────────────────
# # TRELLO – cards (tasks)
# # ─────────────────────────────────────────────
#
# def add_card(
#     list_id: str,
#     name: str,
#     description: str = "",
#     due: Optional[str] = None,
#     member_id: Optional[str] = None,
# ) -> dict:
#     """Creates a card (task) in the given list."""
#     payload = {**_auth(), "idList": list_id, "name": name, "desc": description}
#     if due:
#         payload["due"] = due
#     if member_id:
#         payload["idMembers"] = member_id
#     resp = requests.post(f"{BASE_URL}/cards", params=payload)
#     resp.raise_for_status()
#     return resp.json()
#
#
# def update_card(
#     card_id: str,
#     name: Optional[str] = None,
#     description: Optional[str] = None,
#     due: Optional[str] = None,
#     list_id: Optional[str] = None,
#     member_id: Optional[str] = None,
# ) -> dict:
#     """Updates any fields of an existing card."""
#     payload = {**_auth()}
#     if name        is not None: payload["name"]      = name
#     if description is not None: payload["desc"]      = description
#     if due         is not None: payload["due"]       = due
#     if list_id     is not None: payload["idList"]    = list_id
#     if member_id   is not None: payload["idMembers"] = member_id
#     resp = requests.put(f"{BASE_URL}/cards/{card_id}", params=payload)
#     resp.raise_for_status()
#     return resp.json()
#
#
# def get_board_cards(board_id: str) -> list[dict]:
#     """Returns all cards on a board: id, name, desc, idList."""
#     resp = requests.get(
#         f"{BASE_URL}/boards/{board_id}/cards",
#         params={**_auth(), "fields": "id,name,desc,idList"},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# def delete_card(card_id: str) -> None:
#     """Permanently deletes a card."""
#     resp = requests.delete(f"{BASE_URL}/cards/{card_id}", params=_auth())
#     resp.raise_for_status()
#     print(f"  🗑️  Card deleted: {card_id}")
#
#
# # ─────────────────────────────────────────────
# # TRELLO – members
# # ─────────────────────────────────────────────
#
# def get_member_id(username: str) -> str:
#     """Returns the Trello member ID for a given @username."""
#     resp = requests.get(
#         f"{BASE_URL}/members/{username}",
#         params={**_auth(), "fields": "id,fullName,username"},
#     )
#     resp.raise_for_status()
#     member = resp.json()
#     print(f"  👤 {member['fullName']} (@{member['username']}) → ID: {member['id']}")
#     return member["id"]
#
#
# def get_workspace_members(workspace_id: str) -> list[dict]:
#     """Returns all members of a workspace (requires admin access for email field)."""
#     resp = requests.get(
#         f"{BASE_URL}/organizations/{workspace_id}/members",
#         params={**_auth(), "fields": "id,fullName,username,email"},
#     )
#     resp.raise_for_status()
#     members = resp.json()
#     for m in members:
#         print(f"  [{m['id']}] {m['fullName']} (@{m['username']})")
#     return members
#
#
# def get_board_members(board_id: str) -> list[dict]:
#     """Returns all members of a specific board."""
#     resp = requests.get(
#         f"{BASE_URL}/boards/{board_id}/members",
#         params={**_auth(), "fields": "id,fullName,username"},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# # ─────────────────────────────────────────────
# # BITRIX – base call with retry
# # ─────────────────────────────────────────────
#
# def bitrix_call(method: str, params: dict = None) -> dict:
#     """Calls a Bitrix24 REST API method with up to 5 retries."""
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
#             print(f"  ⚠️  Attempt {attempt}/5: {e}")
#             if attempt < 5:
#                 time.sleep(4)
#             else:
#                 print("  ❌ Failed to connect to Bitrix24.")
#                 return {"error": str(e)}
#
#
# # ─────────────────────────────────────────────
# # BITRIX – users
# # ─────────────────────────────────────────────
#
# def fetch_bitrix_users() -> list[dict]:
#     """
#     Fetches all active Bitrix24 users with pagination (50 per page).
#     Returns list of dicts: {ID, NAME, LAST_NAME}.
#     """
#     users = []
#     start = 0
#     print("📥 Fetching Bitrix24 users...")
#
#     while True:
#         result = bitrix_call("user.get.json", {
#             "filter": {"ACTIVE": True},
#             "select": ["ID", "NAME", "LAST_NAME"],
#             "start": start,
#         })
#
#         if "error" in result:
#             print(f"  ❌ Bitrix error: {result['error']}")
#             break
#
#         batch = result.get("result", [])
#         if not batch:
#             break
#
#         users.extend(batch)
#         print(f"  Fetched {len(users)} users...")
#
#         total = result.get("total", 0)
#         start += 50
#         if start >= total:
#             break
#
#         time.sleep(0.3)
#
#     print(f"✅ Total Bitrix24 users fetched: {len(users)}")
#     return users
#
#
# # ─────────────────────────────────────────────
# # BITRIX – projects (groups)
# # ─────────────────────────────────────────────
#
# def fetch_bitrix_projects() -> list[dict]:
#     """
#     Fetches all Bitrix24 groups/projects with pagination (50 per page).
#     Returns list of dicts: {ID, NAME, DESCRIPTION}.
#     """
#     projects = []
#     start = 0
#     print("📥 Fetching Bitrix24 projects...")
#
#     while True:
#         result = bitrix_call("sonet_group.get.json", {
#             "select": ["ID", "NAME", "DESCRIPTION"],
#             "start": start,
#         })
#
#         if "error" in result:
#             print(f"  ❌ Bitrix error: {result['error']}")
#             break
#
#         batch = result.get("result", [])
#         if not batch:
#             break
#
#         projects.extend(batch)
#         print(f"  Fetched {len(projects)} projects...")
#
#         total = result.get("total", 0)
#         start += 50
#         if start >= total:
#             break
#
#         time.sleep(0.3)
#
#     print(f"✅ Total Bitrix24 projects fetched: {len(projects)}")
#     return projects
#
#
# # ─────────────────────────────────────────────
# # BITRIX – tasks
# # ─────────────────────────────────────────────
#
# def fetch_bitrix_tasks(group_id: int, exclude: bool = False) -> list[dict]:
#     """
#     Fetches all tasks for a Bitrix24 group with pagination (50 per page).
#     Returns list of dicts: {id, title, description, status, createdDate,
#                              closedDate, dateStart, createdBy, responsibleId}.
#
#     Args:
#         group_id: Bitrix24 group ID to filter by.
#         exclude:  If True, fetches tasks where GROUP_ID != group_id (filter key '!GROUP_ID').
#                   E.g. fetch_bitrix_tasks(0, exclude=True) returns all tasks not in any group.
#     """
#     tasks = []
#     start = 0
#     filter_key = "!GROUP_ID" if exclude else "GROUP_ID"
#     print(f"  📥 Fetching tasks where {filter_key}={group_id}...")
#
#     while True:
#         result = bitrix_call("tasks.task.list.json", {
#             "filter": {filter_key: group_id},
#             "select": [
#                 "ID", "TITLE", "DESCRIPTION", "STATUS",
#                 "CREATED_DATE", "CLOSED_DATE", "DATE_START",
#                 "CREATED_BY", "RESPONSIBLE_ID",
#             ],
#             "start": start,
#         })
#
#         if "error" in result:
#             print(f"  ❌ Bitrix error: {result['error']}")
#             break
#
#         batch = result.get("result", {}).get("tasks", [])
#         if not batch:
#             break
#
#         tasks.extend(batch)
#
#         # ✅ total jest na poziomie result, nie result.result
#         total = result.get("total", 0)
#         next_start = result.get("next")
#
#         print(f"    Fetched {len(tasks)}/{total} tasks...")
#
#         # ✅ jeśli Bitrix nie zwrócił "next", to już koniec
#         if next_start is None:
#             break
#
#         start = next_start
#         time.sleep(0.3)
#
#     print(f"  ✅ Total tasks fetched: {len(tasks)}")
#     return tasks
#
#
# # ─────────────────────────────────────────────
# # USER MATCHING – Bitrix ↔ Trello
# # ─────────────────────────────────────────────
# _PL_CHARS = str.maketrans(
#     "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
#     "acelnoszzACELNOSZZ",
# )
#
# def normalize(name: str) -> str:
#     """Lowercases and replaces Polish diacritics with ASCII equivalents."""
#     return name.strip().lower().translate(_PL_CHARS)
#
# def build_user_map(bitrix_users: list[dict], trello_members: list[dict]) -> dict[str, str]:
#     """
#     Tries to match Bitrix24 users with Trello members by full name.
#     Normalizes Polish diacritics on both sides before comparing,
#     so typos like 'n' vs 'ń' or 'l' vs 'ł' are handled.
#     Returns dict: {bitrix_user_id → trello_member_id}.
#     """
#     print("\n🔗 Matching Bitrix24 users with Trello members...")
#
#     # Build Trello lookup: normalized full name → member_id
#     trello_by_name: dict[str, str] = {}
#     for m in trello_members:
#         key = normalize(m.get("fullName", ""))
#         if key:
#             trello_by_name[key] = m["id"]
#
#     user_map: dict[str, str] = {}
#     unmatched: list[str] = []
#
#     for u in bitrix_users:
#         bitrix_id = str(u["ID"])
#         raw_name = f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip()
#         key = normalize(raw_name)
#         trello_id = trello_by_name.get(key)
#
#         if trello_id:
#             user_map[bitrix_id] = trello_id
#             print(f"  ✅ Matched: '{raw_name}' → Trello {trello_id}")
#         else:
#             unmatched.append(f"{raw_name} (Bitrix ID={bitrix_id})")
#
#     if unmatched:
#         print(f"\n  ⚠️  Unmatched Bitrix users ({len(unmatched)}):")
#         for name in unmatched:
#             print(f"    - {name}")
#
#     print(f"\n✅ User map built: {len(user_map)} matched, {len(unmatched)} unmatched.")
#     return user_map
#
#
# # ─────────────────────────────────────────────
# # CARD DESCRIPTION builder
# # ─────────────────────────────────────────────
#
# def build_card_description(task: dict, bitrix_users: list[dict]) -> str:
#     """
#     Builds a Trello card description from a Bitrix24 task.
#     Starts with the Bitrix ID, then task details on a new line.
#     """
#     # Build quick lookup: bitrix user id → full name
#     user_lookup = {
#         str(u["ID"]): f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip()
#         for u in bitrix_users
#     }
#
#     created_by     = user_lookup.get(str(task.get("createdBy", "")), task.get("createdBy", "—"))
#     responsible    = user_lookup.get(str(task.get("responsibleId", "")), task.get("responsibleId", "—"))
#     raw_desc       = (task.get("description", "") or "").strip()
#
#     lines = [
#         f"**Bitrix ID:** {task.get('id', '—')}",
#         "",
#         f"**Created by:** {created_by}",
#         f"**Responsible:** {responsible}",
#         f"**Created:** {task.get('createdDate', '—')}",
#         f"**Started:** {task.get('dateStart', '—')}",
#         f"**Closed:** {task.get('closedDate', '—')}",
#     ]
#
#     if raw_desc:
#         lines += ["", "---", "", raw_desc]
#
#     return "\n".join(lines)
#
#
# # ─────────────────────────────────────────────
# # INIT – boards (upsert)
# # ─────────────────────────────────────────────
#
# def init_upsert_boards(
#     projects: list[dict],
#     workspace_id: Optional[str] = None,
# ) -> dict[str, dict]:
#     """
#     For each Bitrix24 project, finds an existing Trello board by name or creates a new one.
#     Updates description if it differs.
#
#     Returns:
#         {bitrix_group_id → {"bitrix": project, "trello": board, "lists": {status_id: list_id}}}
#     """
#     print("\n📋 Upserting boards in Trello...")
#     existing_boards = get_trello_boards()
#     boards_by_name  = {b["name"].strip().lower(): b for b in existing_boards}
#
#     board_map: dict[str, dict] = {}
#
#     for project in projects:
#         group_id = str(project["ID"])
#         name     = project.get("NAME", f"Project #{group_id}").strip()
#         desc     = project.get("DESCRIPTION", "") or ""
#         key      = name.lower()
#
#         if key in boards_by_name:
#             board = boards_by_name[key]
#             # Update description if changed
#             if board.get("desc", "").strip() != desc.strip():
#                 board = update_board(board["id"], description=desc)
#             else:
#                 print(f"  ✔️  Board already up to date: '{name}'")
#         else:
#             board = create_board(name=name, description=desc, workspace_id=workspace_id)
#
#         board_id = board["id"]
#
#         # Ensure all status columns exist
#         existing_lists  = get_board_lists(board_id)
#         lists_by_name   = {l["name"].strip().lower(): l["id"] for l in existing_lists}
#         lists: dict[str, str] = {}
#
#         for status_id in STATUS_ORDER:
#             col_name = STATUS_MAP[status_id]
#             if col_name.lower() in lists_by_name:
#                 lists[status_id] = lists_by_name[col_name.lower()]
#             else:
#                 new_list = create_list(board_id, col_name)
#                 lists[status_id] = new_list["id"]
#             time.sleep(0.05)
#
#         board_map[group_id] = {
#             "bitrix": project,
#             "trello": board,
#             "lists":  lists,
#         }
#         time.sleep(0.15)
#
#     print(f"✅ Boards upserted: {len(board_map)}")
#     return board_map
#
#
# # ─────────────────────────────────────────────
# # INIT – tasks (upsert)
# # ─────────────────────────────────────────────
#
# def init_upsert_tasks(
#     board_map: dict[str, dict],
#     bitrix_users: list[dict],
#     user_map: dict[str, str],
# ) -> int:
#     """
#     For each project, fetches Bitrix24 tasks and upserts them as Trello cards.
#     Matches existing cards by 'Bitrix ID' in description; updates if changed, creates if new.
#
#     Returns total number of cards created or updated.
#     """
#     total = 0
#
#     for group_id, data in board_map.items():
#         lists   = data["lists"]
#         board   = data["trello"]
#         board_id = board["id"]
#         print(f"\n📌 Project: '{board['name']}' (GROUP_ID={group_id})")
#
#         tasks = fetch_bitrix_tasks(int(group_id))
#         if not tasks:
#             print("  ℹ️  No tasks.")
#             continue
#
#         # Build lookup of existing cards by Bitrix ID extracted from description
#         existing_cards = get_board_cards(board_id)
#         cards_by_bitrix_id: dict[str, dict] = {}
#         for card in existing_cards:
#             desc = card.get("desc", "") or ""
#             for line in desc.splitlines():
#                 if line.startswith("**Bitrix ID:**"):
#                     bid = line.replace("**Bitrix ID:**", "").strip()
#                     cards_by_bitrix_id[bid] = card
#                     break
#
#         for task in tasks:
#             bitrix_task_id = str(task.get("id", ""))
#             status_id      = str(task.get("status", "1"))
#             list_id        = lists.get(status_id, lists["1"])
#             title          = (task.get("title", "") or "").strip() or f"Task #{bitrix_task_id}"
#             description    = build_card_description(task, bitrix_users)
#             due            = task.get("closedDate") or None
#             trello_member  = user_map.get(str(task.get("responsibleId", "")))
#
#             existing = cards_by_bitrix_id.get(bitrix_task_id)
#
#             if existing:
#                 # Update only if something changed
#                 changed = (
#                     existing.get("name")   != title       or
#                     existing.get("desc")   != description or
#                     existing.get("idList") != list_id
#                 )
#                 if changed:
#                     update_card(
#                         card_id=existing["id"],
#                         name=title,
#                         description=description,
#                         due=due,
#                         list_id=list_id,
#                         member_id=trello_member,
#                     )
#                     print(f"    ✏️  Updated: [{STATUS_MAP.get(status_id, '?')}] {title}")
#                     total += 1
#                 else:
#                     print(f"    ✔️  No changes: {title}")
#             else:
#                 add_card(
#                     list_id=list_id,
#                     name=title,
#                     description=description,
#                     due=due,
#                     member_id=trello_member,
#                 )
#                 print(f"    ✅ Created: [{STATUS_MAP.get(status_id, '?')}] {title}")
#                 total += 1
#
#             time.sleep(0.1)
#
#     print(f"\n✅ Total cards created/updated: {total}")
#     return total
#
#
# # ─────────────────────────────────────────────
# # COMPARE – boards vs Bitrix projects
# # ─────────────────────────────────────────────
#
# def compare_boards_with_bitrix(board_map: dict[str, dict]) -> None:
#     """
#     Compares existing Trello boards against Bitrix24 projects.
#     Prints: matched | only in Trello | only in Bitrix24.
#     """
#     print("\n" + "=" * 55)
#     print("🔍 Board comparison: Trello ↔ Bitrix24")
#     print("=" * 55)
#
#     all_trello_boards = get_trello_boards()
#     bitrix_names      = {
#         data["bitrix"]["NAME"].strip().lower(): gid
#         for gid, data in board_map.items()
#     }
#     mapped_trello_ids = {data["trello"]["id"] for data in board_map.values()}
#
#     matched     = []
#     trello_only = []
#
#     for b in all_trello_boards:
#         if b["id"] in mapped_trello_ids or b["name"].strip().lower() in bitrix_names:
#             matched.append(b)
#         else:
#             trello_only.append(b)
#
#     trello_names_lower = {b["name"].strip().lower() for b in all_trello_boards}
#     bitrix_only = [
#         data["bitrix"]
#         for data in board_map.values()
#         if data["bitrix"]["NAME"].strip().lower() not in trello_names_lower
#     ]
#
#     print(f"\n✅ Matched ({len(matched)}):")
#     for b in matched:
#         print(f"   [{b['id']}] {b['name']}")
#
#     print(f"\n⚠️  Trello only – no Bitrix24 project ({len(trello_only)}):")
#     for b in trello_only:
#         print(f"   [{b['id']}] {b['name']}")
#
#     print(f"\n❌ Bitrix24 only – no Trello board ({len(bitrix_only)}):")
#     for p in bitrix_only:
#         print(f"   [GROUP_ID={p['ID']}] {p['NAME']}")
#     print()
#
#
# # ─────────────────────────────────────────────
# # ENTRY POINT
# # ─────────────────────────────────────────────
#
# def init_sync(workspace_id: Optional[str] = WORKSPACE_ID) -> None:
#     """
#     Full initialisation / sync flow:
#       1. Fetch Bitrix24 users and Trello workspace members, build user map.
#       2. Fetch Bitrix24 projects; upsert Trello boards (create or update).
#       3. Fetch tasks per project; upsert Trello cards (create or update).
#       4. Compare boards for discrepancies.
#     """
#     print("=" * 55)
#     print("🚀 Starting Bitrix24 → Trello sync")
#     print("=" * 55)
#
#     # 1. Users
#     bitrix_users   = fetch_bitrix_users()
#     trello_members = get_workspace_members(workspace_id)
#     user_map       = build_user_map(bitrix_users, trello_members)
#
#     # 2. Projects → boards
#     projects  = fetch_bitrix_projects()
#     board_map = init_upsert_boards(projects, workspace_id=workspace_id)
#
#     # 3. Tasks → cards
#     init_upsert_tasks(board_map, bitrix_users, user_map)
#     #fetch_bitrix_tasks(group_id=57)
#     fetch_bitrix_tasks(group_id=0, exclude=True)
#
#     # 4. Comparison report
#     compare_boards_with_bitrix(board_map)
#
#     print("=" * 55)
#     print("✅ Sync complete.")
#     print("=" * 55)
#
#
# if __name__ == "__main__":
#     init_sync()
#
# import requests
# import config
# import time
# from typing import Optional
#
# TRELLO_API_KEY = config.ConfigTrello.TRELLO_API_KEY
# TRELLO_TOKEN = config.ConfigTrello.TRELLO_TOKEN
# BASE_URL = config.ConfigTrello.BASE_URL
# BITRIX_URL = config.ConfigBitrix.BITRIX_URL
# WORKSPACE_ID = "6a18200189faaa62c4e14a49"
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
# STATUS_ORDER = ["1", "2", "3", "4", "5", "6"]
#
#
# def _auth() -> dict:
#     return {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN}
#
#
# # ─────────────────────────────────────────────
# # TRELLO – boards
# # ─────────────────────────────────────────────
#
# def create_board(name: str, description: str = "", workspace_id: Optional[str] = None) -> dict:
#     """Creates a Trello board, optionally inside a workspace."""
#     payload = {**_auth(), "name": name, "desc": description, "defaultLists": "false"}
#     if workspace_id:
#         payload["idOrganization"] = workspace_id
#         payload["prefs_permissionLevel"] = "org"
#     resp = requests.post(f"{BASE_URL}/boards", params=payload)
#     resp.raise_for_status()
#     board = resp.json()
#     print(f"  ✅ Board created: '{board['name']}' | {board['shortUrl']}")
#     return board
#
#
# def update_board(board_id: str, name: Optional[str] = None, description: Optional[str] = None) -> dict:
#     """Updates name and/or description of an existing board."""
#     payload = {**_auth()}
#     if name is not None:
#         payload["name"] = name
#     if description is not None:
#         payload["desc"] = description
#     resp = requests.put(f"{BASE_URL}/boards/{board_id}", params=payload)
#     resp.raise_for_status()
#     board = resp.json()
#     print(f"  ✏️  Board updated: '{board['name']}'")
#     return board
#
#
# def get_trello_boards() -> list[dict]:
#     """Returns all boards on the account: id, name, desc, idOrganization, shortUrl."""
#     resp = requests.get(
#         f"{BASE_URL}/members/me/boards",
#         params={**_auth(), "fields": "id,name,desc,idOrganization,shortUrl"},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# def create_list(board_id: str, name: str) -> dict:
#     """Creates a column (list) on a board."""
#     resp = requests.post(
#         f"{BASE_URL}/lists",
#         params={**_auth(), "name": name, "idBoard": board_id},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# def get_board_lists(board_id: str) -> list[dict]:
#     """Returns all lists (columns) on a board."""
#     resp = requests.get(
#         f"{BASE_URL}/boards/{board_id}/lists",
#         params={**_auth(), "fields": "id,name"},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# def add_member_to_board(board_id: str, member_id: str, role: str = "normal") -> dict:
#     """
#     Adds a user to a board.
#     role: 'normal' | 'admin' | 'observer' (observer requires Trello Premium)
#     """
#     resp = requests.put(
#         f"{BASE_URL}/boards/{board_id}/members/{member_id}",
#         params={**_auth(), "type": role},
#     )
#     resp.raise_for_status()
#     print(f"  ✅ Member {member_id} added to board {board_id} as '{role}'")
#     return resp.json()
#
#
# # ─────────────────────────────────────────────
# # TRELLO – cards (tasks)
# # ─────────────────────────────────────────────
#
# def add_card(
#     list_id: str,
#     name: str,
#     description: str = "",
#     start: Optional[str] = None,
#     due: Optional[str] = None,
#     due_complete: bool = False,
#     member_id: Optional[str] = None,
# ) -> dict:
#     """Creates a card (task) in the given list."""
#     payload = {**_auth(), "idList": list_id, "name": name, "desc": description}
#     if start:
#         payload["start"] = start
#     if due:
#         payload["due"] = due
#     if due_complete:
#         payload["dueComplete"] = "true"
#     if member_id:
#         payload["idMembers"] = member_id
#     resp = requests.post(f"{BASE_URL}/cards", params=payload)
#     resp.raise_for_status()
#     return resp.json()
#
#
# def update_card(
#     card_id: str,
#     name: Optional[str] = None,
#     description: Optional[str] = None,
#     start: Optional[str] = None,
#     due: Optional[str] = None,
#     due_complete: Optional[bool] = None,
#     list_id: Optional[str] = None,
#     member_id: Optional[str] = None,
# ) -> dict:
#     """Updates any fields of an existing card."""
#     payload = {**_auth()}
#     if name         is not None: payload["name"]        = name
#     if description  is not None: payload["desc"]        = description
#     if start        is not None: payload["start"]       = start
#     if due          is not None: payload["due"]         = due
#     if due_complete is not None: payload["dueComplete"] = "true" if due_complete else "false"
#     if list_id      is not None: payload["idList"]      = list_id
#     if member_id    is not None: payload["idMembers"]   = member_id
#     resp = requests.put(f"{BASE_URL}/cards/{card_id}", params=payload)
#     resp.raise_for_status()
#     return resp.json()
#
#
# def get_board_cards(board_id: str) -> list[dict]:
#     """Returns all cards on a board: id, name, desc, idList, due, dueComplete, start."""
#     resp = requests.get(
#         f"{BASE_URL}/boards/{board_id}/cards",
#         params={**_auth(), "fields": "id,name,desc,idList,due,dueComplete,start"},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# def delete_card(card_id: str) -> None:
#     """Permanently deletes a card."""
#     resp = requests.delete(f"{BASE_URL}/cards/{card_id}", params=_auth())
#     resp.raise_for_status()
#     print(f"  🗑️  Card deleted: {card_id}")
#
#
# # ─────────────────────────────────────────────
# # TRELLO – members
# # ─────────────────────────────────────────────
#
# def get_member_id(username: str) -> str:
#     """Returns the Trello member ID for a given @username."""
#     resp = requests.get(
#         f"{BASE_URL}/members/{username}",
#         params={**_auth(), "fields": "id,fullName,username"},
#     )
#     resp.raise_for_status()
#     member = resp.json()
#     print(f"  👤 {member['fullName']} (@{member['username']}) → ID: {member['id']}")
#     return member["id"]
#
#
# def get_workspace_members(workspace_id: str) -> list[dict]:
#     """Returns all members of a workspace (requires admin access for email field)."""
#     resp = requests.get(
#         f"{BASE_URL}/organizations/{workspace_id}/members",
#         params={**_auth(), "fields": "id,fullName,username,email"},
#     )
#     resp.raise_for_status()
#     members = resp.json()
#     for m in members:
#         print(f"  [{m['id']}] {m['fullName']} (@{m['username']})")
#     return members
#
#
# def get_board_members(board_id: str) -> list[dict]:
#     """Returns all members of a specific board."""
#     resp = requests.get(
#         f"{BASE_URL}/boards/{board_id}/members",
#         params={**_auth(), "fields": "id,fullName,username"},
#     )
#     resp.raise_for_status()
#     return resp.json()
#
#
# # ─────────────────────────────────────────────
# # BITRIX – base call with retry
# # ─────────────────────────────────────────────
#
# def bitrix_call(method: str, params: dict = None) -> dict:
#     """Calls a Bitrix24 REST API method with up to 5 retries."""
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
#             print(f"  ⚠️  Attempt {attempt}/5: {e}")
#             if attempt < 5:
#                 time.sleep(4)
#             else:
#                 print("  ❌ Failed to connect to Bitrix24.")
#                 return {"error": str(e)}
#
#
# # ─────────────────────────────────────────────
# # BITRIX – users
# # ─────────────────────────────────────────────
#
# def fetch_bitrix_users() -> list[dict]:
#     """
#     Fetches all active Bitrix24 users with pagination (50 per page).
#     Returns list of dicts: {ID, NAME, LAST_NAME}.
#     """
#     users = []
#     start = 0
#     print("📥 Fetching Bitrix24 users...")
#
#     while True:
#         result = bitrix_call("user.get.json", {
#             "filter": {"ACTIVE": True},
#             "select": ["ID", "NAME", "LAST_NAME"],
#             "start": start,
#         })
#
#         if "error" in result:
#             print(f"  ❌ Bitrix error: {result['error']}")
#             break
#
#         batch = result.get("result", [])
#         if not batch:
#             break
#
#         users.extend(batch)
#         print(f"  Fetched {len(users)} users...")
#
#         total = result.get("total", 0)
#         start += 50
#         if start >= total:
#             break
#
#         time.sleep(0.3)
#
#     print(f"✅ Total Bitrix24 users fetched: {len(users)}")
#     return users
#
#
# # ─────────────────────────────────────────────
# # BITRIX – projects (groups)
# # ─────────────────────────────────────────────
#
# def fetch_group_members(group_id: int) -> list[dict]:
#     """
#     Returns all members of a Bitrix24 workgroup.
#     Each entry contains USER_ID and ROLE ('A' = admin, 'E' = employee, 'K' = moderator).
#     """
#     result = bitrix_call("sonet_group.user.get.json", {"ID": group_id})
#
#     if "error" in result:
#         print(f"  ❌ Bitrix error fetching members for group {group_id}: {result['error']}")
#         return []
#
#     members = result.get("result", [])
#     print(f"  👥 Group {group_id}: {len(members)} member(s)")
#     return members
#
#
# def fetch_bitrix_projects(with_members: bool = True) -> list[dict]:
#     """
#     Fetches all Bitrix24 groups/projects with pagination (50 per page).
#     When with_members=True, enriches each project with a MEMBER_IDS list.
#     Returns list of dicts: {ID, NAME, DESCRIPTION, MEMBER_IDS}.
#     """
#     projects = []
#     start = 0
#     print("📥 Fetching Bitrix24 projects...")
#
#     while True:
#         result = bitrix_call("sonet_group.get.json", {
#             "select": ["ID", "NAME", "DESCRIPTION"],
#             "start": start,
#         })
#
#         if "error" in result:
#             print(f"  ❌ Bitrix error: {result['error']}")
#             break
#
#         batch = result.get("result", [])
#         if not batch:
#             break
#
#         projects.extend(batch)
#         print(f"  Fetched {len(projects)} projects...")
#
#         total = result.get("total", 0)
#         start += 50
#         if start >= total:
#             break
#
#         time.sleep(0.3)
#
#     print(f"✅ Total Bitrix24 projects fetched: {len(projects)}")
#
#     if with_members:
#         print("📥 Fetching group members...")
#         for project in projects:
#             members = fetch_group_members(int(project["ID"]))
#             project["MEMBER_IDS"] = [str(m["USER_ID"]) for m in members]
#             time.sleep(0.2)
#         print("✅ Group members fetched.")
#     else:
#         for project in projects:
#             project["MEMBER_IDS"] = []
#
#     return projects
#
#
# # ─────────────────────────────────────────────
# # BITRIX – tasks
# # ─────────────────────────────────────────────
#
# def fetch_bitrix_tasks(group_id: int, exclude: bool = False) -> list[dict]:
#     """
#     Fetches all tasks for a Bitrix24 group with cursor-based pagination.
#     Returns list of dicts: {id, title, description, status, createdDate,
#                              closedDate, dateStart, createdBy, responsibleId}.
#
#     Args:
#         group_id: Bitrix24 group ID to filter by.
#         exclude:  If True, fetches tasks where GROUP_ID != group_id (filter key '!GROUP_ID').
#                   E.g. fetch_bitrix_tasks(0, exclude=True) returns all tasks not in any group.
#     """
#     tasks = []
#     start = 0
#     filter_key = "!GROUP_ID" if exclude else "GROUP_ID"
#     print(f"  📥 Fetching tasks where {filter_key}={group_id}...")
#
#     while True:
#         result = bitrix_call("tasks.task.list.json", {
#             "filter": {filter_key: group_id},
#             "select": [
#                 "ID", "TITLE", "DESCRIPTION", "STATUS",
#                 "CREATED_DATE", "CLOSED_DATE", "DATE_START",
#                 "CREATED_BY", "RESPONSIBLE_ID",
#             ],
#             "start": start,
#         })
#
#         if "error" in result:
#             print(f"  ❌ Bitrix error: {result['error']}")
#             break
#
#         batch = result.get("result", {}).get("tasks", [])
#         if not batch:
#             break
#
#         tasks.extend(batch)
#
#         # 'total' sits at root level, not inside result.result
#         total      = result.get("total", 0)
#         next_start = result.get("next")
#
#         print(f"    Fetched {len(tasks)}/{total} tasks...")
#
#         # Bitrix omits 'next' on the last page
#         if next_start is None:
#             break
#
#         start = next_start
#         time.sleep(0.3)
#
#     print(f"  ✅ Total tasks fetched: {len(tasks)}")
#     return tasks
#
#
# # ─────────────────────────────────────────────
# # USER MATCHING – Bitrix ↔ Trello
# # ─────────────────────────────────────────────
#
# _PL_CHARS = str.maketrans(
#     "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
#     "acelnoszzACELNOSZZ",
# )
#
#
# def normalize(name: str) -> str:
#     """Lowercases and replaces Polish diacritics with ASCII equivalents."""
#     return name.strip().lower().translate(_PL_CHARS)
#
#
# def build_user_map(bitrix_users: list[dict], trello_members: list[dict]) -> dict[str, str]:
#     """
#     Tries to match Bitrix24 users with Trello members by full name.
#     Normalizes Polish diacritics on both sides before comparing,
#     so differences like 'n' vs 'ń' or 'l' vs 'ł' are handled.
#     Returns dict: {bitrix_user_id → trello_member_id}.
#     """
#     print("\n🔗 Matching Bitrix24 users with Trello members...")
#
#     trello_by_name: dict[str, str] = {}
#     for m in trello_members:
#         key = normalize(m.get("fullName", ""))
#         if key:
#             trello_by_name[key] = m["id"]
#
#     user_map: dict[str, str] = {}
#     unmatched: list[str] = []
#
#     for u in bitrix_users:
#         bitrix_id = str(u["ID"])
#         raw_name  = f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip()
#         key       = normalize(raw_name)
#         trello_id = trello_by_name.get(key)
#
#         if trello_id:
#             user_map[bitrix_id] = trello_id
#             print(f"  ✅ Matched: '{raw_name}' → Trello {trello_id}")
#         else:
#             unmatched.append(f"{raw_name} (Bitrix ID={bitrix_id})")
#
#     if unmatched:
#         print(f"\n  ⚠️  Unmatched Bitrix users ({len(unmatched)}):")
#         for name in unmatched:
#             print(f"    - {name}")
#
#     print(f"\n✅ User map built: {len(user_map)} matched, {len(unmatched)} unmatched.")
#     return user_map
#
#
# # ─────────────────────────────────────────────
# # CARD DESCRIPTION builder
# # ─────────────────────────────────────────────
#
# def build_card_description(task: dict, bitrix_users: list[dict]) -> str:
#     """
#     Builds a Trello card description from a Bitrix24 task.
#     Starts with the Bitrix ID, then task details on a new line.
#     """
#     user_lookup = {
#         str(u["ID"]): f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip()
#         for u in bitrix_users
#     }
#
#     created_by  = user_lookup.get(str(task.get("createdBy", "")),     task.get("createdBy",     "—"))
#     responsible = user_lookup.get(str(task.get("responsibleId", "")), task.get("responsibleId", "—"))
#     raw_desc    = (task.get("description", "") or "").strip()
#
#     lines = [
#         f"**Bitrix ID:** {task.get('id', '—')}",
#         "",
#         f"**Created by:** {created_by}",
#         f"**Responsible:** {responsible}",
#         f"**Created:** {task.get('createdDate', '—')}",
#         f"**Started:** {task.get('dateStart', '—')}",
#         f"**Closed:** {task.get('closedDate', '—')}",
#     ]
#
#     if raw_desc:
#         lines += ["", "---", "", raw_desc]
#
#     return "\n".join(lines)
#
#
# # ─────────────────────────────────────────────
# # INIT – boards (upsert)
# # ─────────────────────────────────────────────
#
# def init_upsert_boards(
#     projects: list[dict],
#     user_map: dict[str, str],
#     workspace_id: Optional[str] = None,
# ) -> dict[str, dict]:
#     """
#     For each Bitrix24 project, finds an existing Trello board by name or creates a new one.
#     Updates description if it differs.
#     Adds matched Bitrix group members to the board.
#
#     Returns:
#         {bitrix_group_id → {"bitrix": project, "trello": board, "lists": {status_id: list_id}}}
#     """
#     print("\n📋 Upserting boards in Trello...")
#     existing_boards = get_trello_boards()
#     boards_by_name  = {b["name"].strip().lower(): b for b in existing_boards}
#
#     board_map: dict[str, dict] = {}
#
#     for project in projects:
#         group_id = str(project["ID"])
#         name     = project.get("NAME", f"Project #{group_id}").strip()
#         desc     = project.get("DESCRIPTION", "") or ""
#         key      = name.lower()
#
#         if key in boards_by_name:
#             board = boards_by_name[key]
#             if board.get("desc", "").strip() != desc.strip():
#                 board = update_board(board["id"], description=desc)
#             else:
#                 print(f"  ✔️  Board already up to date: '{name}'")
#         else:
#             board = create_board(name=name, description=desc, workspace_id=workspace_id)
#
#         board_id = board["id"]
#
#         # Ensure all status columns exist
#         existing_lists = get_board_lists(board_id)
#         lists_by_name  = {l["name"].strip().lower(): l["id"] for l in existing_lists}
#         lists: dict[str, str] = {}
#
#         for status_id in STATUS_ORDER:
#             col_name = STATUS_MAP[status_id]
#             if col_name.lower() in lists_by_name:
#                 lists[status_id] = lists_by_name[col_name.lower()]
#             else:
#                 new_list = create_list(board_id, col_name)
#                 lists[status_id] = new_list["id"]
#             time.sleep(0.05)
#
#         # Add Bitrix group members to the Trello board
#         current_board_members = {m["id"] for m in get_board_members(board_id)}
#         for bitrix_user_id in project.get("MEMBER_IDS", []):
#             trello_member_id = user_map.get(bitrix_user_id)
#             if trello_member_id and trello_member_id not in current_board_members:
#                 try:
#                     add_member_to_board(board_id, trello_member_id)
#                     current_board_members.add(trello_member_id)
#                 except requests.exceptions.HTTPError as e:
#                     print(f"  ⚠️  Could not add member {trello_member_id} to board '{name}': {e}")
#                 time.sleep(0.1)
#
#         board_map[group_id] = {
#             "bitrix": project,
#             "trello": board,
#             "lists":  lists,
#         }
#         time.sleep(0.15)
#
#     print(f"✅ Boards upserted: {len(board_map)}")
#     return board_map
#
#
# # ─────────────────────────────────────────────
# # SYNC – board members only
# # ─────────────────────────────────────────────
#
# def sync_board_members(
#     board_map: dict[str, dict],
#     user_map: dict[str, str],
# ) -> None:
#     """
#     Checks every board in board_map and adds any Bitrix group members
#     that are missing from the corresponding Trello board.
#     Does not create or modify any boards or cards.
#     """
#     print("\n" + "=" * 55)
#     print("👥 Syncing board members: Bitrix24 → Trello")
#     print("=" * 55)
#
#     added_total = 0
#     already_total = 0
#
#     for group_id, data in board_map.items():
#         board    = data["trello"]
#         board_id = board["id"]
#         project  = data["bitrix"]
#
#         member_ids = project.get("MEMBER_IDS", [])
#         if not member_ids:
#             print(f"\n  [{board['name']}] no Bitrix members to sync")
#             continue
#
#         current_board_members = {m["id"] for m in get_board_members(board_id)}
#         added = already = 0
#
#         print(f"\n  [{board['name']}] checking {len(member_ids)} Bitrix member(s)...")
#
#         for bitrix_user_id in member_ids:
#             trello_member_id = user_map.get(bitrix_user_id)
#             if not trello_member_id:
#                 continue  # unmatched Bitrix user – no Trello account found
#
#             if trello_member_id in current_board_members:
#                 already += 1
#             else:
#                 try:
#                     add_member_to_board(board_id, trello_member_id)
#                     current_board_members.add(trello_member_id)
#                     added += 1
#                 except requests.exceptions.HTTPError as e:
#                     print(f"    ⚠️  Could not add member {trello_member_id}: {e}")
#                 time.sleep(0.1)
#
#         print(f"    added: {added} | already present: {already}")
#         added_total   += added
#         already_total += already
#
#     print(f"\n✅ Members sync complete — added: {added_total} | already present: {already_total}")
#
#
# # ─────────────────────────────────────────────
# # SYNC – tasks (compare → fill gaps → update)
# # ─────────────────────────────────────────────
#
# def _extract_bitrix_id_from_card(card: dict) -> Optional[str]:
#     """Extracts the Bitrix task ID stored in the first line of a card description."""
#     desc = card.get("desc", "") or ""
#     for line in desc.splitlines():
#         if line.startswith("**Bitrix ID:**"):
#             return line.replace("**Bitrix ID:**", "").strip()
#     return None
#
#
# def _collect_trello_cards(board_map: dict[str, dict]) -> dict[str, dict[str, dict]]:
#     """
#     Fetches all existing Trello cards for every board in board_map.
#
#     Returns:
#         {group_id → {bitrix_task_id → card}}
#     """
#     print("\n📥 Collecting existing Trello cards...")
#     trello_index: dict[str, dict[str, dict]] = {}
#
#     for group_id, data in board_map.items():
#         board_id = data["trello"]["id"]
#         cards    = get_board_cards(board_id)
#
#         cards_by_bitrix_id: dict[str, dict] = {}
#         for card in cards:
#             bid = _extract_bitrix_id_from_card(card)
#             if bid:
#                 cards_by_bitrix_id[bid] = card
#
#         trello_index[group_id] = cards_by_bitrix_id
#         print(f"  [{data['trello']['name']}] {len(cards_by_bitrix_id)} card(s) indexed")
#         time.sleep(0.05)
#
#     total_cards = sum(len(v) for v in trello_index.values())
#     print(f"✅ Trello cards collected: {total_cards} total across {len(board_map)} board(s)")
#     return trello_index
#
#
# def _collect_bitrix_tasks(board_map: dict[str, dict]) -> dict[str, list[dict]]:
#     """
#     Fetches all Bitrix24 tasks for every group in board_map.
#     Tasks with GROUP_ID=0 (no group) are skipped entirely.
#
#     Returns:
#         {group_id → [task, ...]}
#     """
#     print("\n📥 Collecting Bitrix24 tasks...")
#     bitrix_index: dict[str, list[dict]] = {}
#
#     for group_id in board_map:
#         if group_id == "0":
#             print(f"  ⏭️  Skipping GROUP_ID=0 (ungrouped tasks ignored)")
#             continue
#         tasks = fetch_bitrix_tasks(int(group_id))
#         bitrix_index[group_id] = tasks
#
#     total_tasks = sum(len(v) for v in bitrix_index.values())
#     print(f"✅ Bitrix24 tasks collected: {total_tasks} total across {len(bitrix_index)} group(s)")
#     return bitrix_index
#
#
# def sync_tasks(
#     board_map: dict[str, dict],
#     bitrix_users: list[dict],
#     user_map: dict[str, str],
#     sync_members: bool = False,
# ) -> None:
#     """
#     Syncs Bitrix24 tasks → Trello cards for all projects in board_map.
#
#     Steps:
#       1. Fetch all existing Trello cards (indexed by Bitrix ID) for every board.
#       2. Fetch all Bitrix24 tasks for every group (GROUP_ID=0 skipped).
#       3. For each task:
#            - Missing in Trello        → create card + optionally add responsible to board.
#            - Exists but changed       → update card + optionally add responsible to board.
#            - Unchanged                → skip.
#
#     Args:
#         sync_members: When True, also ensures the responsible member is added
#                       to the board whenever a card is created or updated.
#     """
#     print("\n" + "=" * 55)
#     print("🔄 Syncing tasks: Bitrix24 → Trello")
#     print("=" * 55)
#
#     # Step 1 – snapshot of what is already in Trello
#     trello_index = _collect_trello_cards(board_map)
#
#     # Step 2 – fetch fresh tasks from Bitrix24
#     bitrix_index = _collect_bitrix_tasks(board_map)
#
#     # Step 3 – compare and act
#     created_total = 0
#     updated_total = 0
#     skipped_total = 0
#
#     for group_id, tasks in bitrix_index.items():
#         data     = board_map[group_id]
#         lists    = data["lists"]
#         board    = data["trello"]
#         board_id = board["id"]
#
#         print(f"\n📌 [{board['name']}] — {len(tasks)} task(s) from Bitrix24")
#
#         existing_cards = trello_index.get(group_id, {})
#         created = updated = skipped = 0
#
#         # Cache current board members to avoid repeated API calls
#         board_member_ids: set[str] = (
#             {m["id"] for m in get_board_members(board_id)} if sync_members else set()
#         )
#
#         for task in tasks:
#             bitrix_task_id = str(task.get("id", ""))
#             status_id      = str(task.get("status", "1"))
#             list_id        = lists.get(status_id, lists["1"])
#             title          = (task.get("title", "") or "").strip() or f"Task #{bitrix_task_id}"
#             description    = build_card_description(task, bitrix_users)
#             start          = task.get("dateStart") or None
#             due            = task.get("closedDate") or None
#             due_complete   = status_id == "5"
#             responsible_id = str(task.get("responsibleId", ""))
#             trello_member  = user_map.get(responsible_id)
#
#             existing = existing_cards.get(bitrix_task_id)
#
#             if existing is None:
#                 # ── Card is missing in Trello → create it ──────────────────
#                 add_card(
#                     list_id=list_id,
#                     name=title,
#                     description=description,
#                     start=start,
#                     due=due,
#                     due_complete=due_complete,
#                     member_id=trello_member,
#                 )
#                 print(f"    ✅ Created: [{STATUS_MAP.get(status_id, '?')}] {title}")
#                 created += 1
#
#             else:
#                 # ── Card exists → check for changes ────────────────────────
#                 changed = (
#                     existing.get("name")        != title        or
#                     existing.get("desc")        != description  or
#                     existing.get("idList")      != list_id      or
#                     existing.get("due")         != due          or
#                     existing.get("start")       != start        or
#                     bool(existing.get("dueComplete")) != due_complete
#                 )
#
#                 if changed:
#                     update_card(
#                         card_id=existing["id"],
#                         name=title,
#                         description=description,
#                         start=start,
#                         due=due,
#                         due_complete=due_complete,
#                         list_id=list_id,
#                         member_id=trello_member,
#                     )
#                     print(f"    ✏️  Updated: [{STATUS_MAP.get(status_id, '?')}] {title}")
#                     updated += 1
#                 else:
#                     skipped += 1
#                     continue  # nothing changed, skip member check too
#
#             # ── Optionally ensure responsible is on the board ──────────────
#             if sync_members and trello_member and trello_member not in board_member_ids:
#                 try:
#                     add_member_to_board(board_id, trello_member)
#                     board_member_ids.add(trello_member)
#                 except requests.exceptions.HTTPError as e:
#                     print(f"      ⚠️  Could not add member {trello_member} to board: {e}")
#
#             time.sleep(0.1)
#
#         print(
#             f"  📊 [{board['name']}] created: {created} | "
#             f"updated: {updated} | unchanged: {skipped}"
#         )
#         created_total += created
#         updated_total += updated
#         skipped_total += skipped
#
#     print(
#         f"\n✅ Tasks sync complete — "
#         f"created: {created_total} | updated: {updated_total} | unchanged: {skipped_total}"
#     )
#
#
# # ─────────────────────────────────────────────
# # COMPARE – boards vs Bitrix projects
# # ─────────────────────────────────────────────
#
# def compare_boards_with_bitrix(board_map: dict[str, dict]) -> None:
#     """
#     Compares existing Trello boards against Bitrix24 projects.
#     Prints: matched | only in Trello | only in Bitrix24.
#     """
#     print("\n" + "=" * 55)
#     print("🔍 Board comparison: Trello ↔ Bitrix24")
#     print("=" * 55)
#
#     all_trello_boards = get_trello_boards()
#     bitrix_names      = {
#         data["bitrix"]["NAME"].strip().lower(): gid
#         for gid, data in board_map.items()
#     }
#     mapped_trello_ids = {data["trello"]["id"] for data in board_map.values()}
#
#     matched     = []
#     trello_only = []
#
#     for b in all_trello_boards:
#         if b["id"] in mapped_trello_ids or b["name"].strip().lower() in bitrix_names:
#             matched.append(b)
#         else:
#             trello_only.append(b)
#
#     trello_names_lower = {b["name"].strip().lower() for b in all_trello_boards}
#     bitrix_only = [
#         data["bitrix"]
#         for data in board_map.values()
#         if data["bitrix"]["NAME"].strip().lower() not in trello_names_lower
#     ]
#
#     print(f"\n✅ Matched ({len(matched)}):")
#     for b in matched:
#         print(f"   [{b['id']}] {b['name']}")
#
#     print(f"\n⚠️  Trello only – no Bitrix24 project ({len(trello_only)}):")
#     for b in trello_only:
#         print(f"   [{b['id']}] {b['name']}")
#
#     print(f"\n❌ Bitrix24 only – no Trello board ({len(bitrix_only)}):")
#     for p in bitrix_only:
#         print(f"   [GROUP_ID={p['ID']}] {p['NAME']}")
#     print()
#
#
# # ─────────────────────────────────────────────
# # ENTRY POINTS
# # ─────────────────────────────────────────────
#
# def full_sync(workspace_id: Optional[str] = WORKSPACE_ID) -> None:
#     """
#     Full sync flow:
#       1. Fetch users (Bitrix + Trello), build user map.
#       2. Fetch projects WITH member lists; upsert boards, columns and board members.
#       3. Sync tasks (create / update cards) + add responsible members to boards.
#       4. Compare boards for discrepancies.
#     """
#     print("=" * 55)
#     print("🚀 FULL SYNC — Bitrix24 → Trello")
#     print("=" * 55)
#
#     bitrix_users   = fetch_bitrix_users()
#     trello_members = get_workspace_members(workspace_id)
#     user_map       = build_user_map(bitrix_users, trello_members)
#
#     projects  = fetch_bitrix_projects(with_members=True)
#     board_map = init_upsert_boards(projects, user_map=user_map, workspace_id=workspace_id)
#
#     sync_tasks(board_map, bitrix_users, user_map, sync_members=True)
#
#     compare_boards_with_bitrix(board_map)
#
#     print("=" * 55)
#     print("✅ Full sync complete.")
#     print("=" * 55)
#
#
# def tasks_and_members_sync(workspace_id: Optional[str] = WORKSPACE_ID) -> None:
#     """
#     Lightweight sync — no board/column creation:
#       1. Fetch users (Bitrix + Trello), build user map.
#       2. Fetch projects WITHOUT fetching group members (faster).
#          Boards must already exist in Trello.
#       3. Sync tasks (create / update cards) + add responsible members to boards.
#       4. Sync board members from Bitrix group membership.
#     """
#     print("=" * 55)
#     print("🔄 TASKS + MEMBERS SYNC — Bitrix24 → Trello")
#     print("=" * 55)
#
#     bitrix_users   = fetch_bitrix_users()
#     trello_members = get_workspace_members(workspace_id)
#     user_map       = build_user_map(bitrix_users, trello_members)
#
#     # Fetch projects without member lists first (faster) — boards must already exist
#     projects = fetch_bitrix_projects(with_members=False)
#
#     existing_boards = get_trello_boards()
#     boards_by_name  = {b["name"].strip().lower(): b for b in existing_boards}
#
#     board_map: dict[str, dict] = {}
#     skipped_projects: list[str] = []
#
#     for project in projects:
#         group_id = str(project["ID"])
#         name     = project.get("NAME", f"Project #{group_id}").strip()
#         board    = boards_by_name.get(name.lower())
#
#         if not board:
#             skipped_projects.append(name)
#             continue
#
#         board_id       = board["id"]
#         existing_lists = get_board_lists(board_id)
#         lists_by_name  = {l["name"].strip().lower(): l["id"] for l in existing_lists}
#         lists: dict[str, str] = {}
#
#         for status_id in STATUS_ORDER:
#             col_name = STATUS_MAP[status_id]
#             lists[status_id] = lists_by_name.get(col_name.lower(), list(lists_by_name.values())[0])
#
#         board_map[group_id] = {
#             "bitrix": project,
#             "trello": board,
#             "lists":  lists,
#         }
#
#     if skipped_projects:
#         print(f"\n  ⚠️  Boards not found in Trello (skipped): {len(skipped_projects)}")
#         for name in skipped_projects:
#             print(f"    - {name}")
#
#     # Sync tasks (also adds responsible users to boards)
#     sync_tasks(board_map, bitrix_users, user_map, sync_members=True)
#
#     # Now fetch group members and sync board membership
#     print("\n📥 Fetching group members for member sync...")
#     for group_id, data in board_map.items():
#         members = fetch_group_members(int(group_id))
#         data["bitrix"]["MEMBER_IDS"] = [str(m["USER_ID"]) for m in members]
#         time.sleep(0.2)
#
#     sync_board_members(board_map, user_map)
#
#     print("=" * 55)
#     print("✅ Tasks + members sync complete.")
#     print("=" * 55)
#
#
# if __name__ == "__main__":
#     # Choose one:
#     # full_sync()
#     tasks_and_members_sync()