# Changelog

## 1.1.0

- Dodano konfigurowalne powiadomienia na telefony z Home Assistant Companion.
- Dodano wybór jednego lub wielu celów `notify.mobile_app_*`.
- Dodano edytowalną listę telefonów.
- Dodano własną nazwę każdego telefonu z automatyczną nazwą domyślną.
- Dodano osobne włączenie lub wyłączenie każdego telefonu bez usuwania go z listy.
- Dodano test powiadomienia dla każdego wybranego telefonu.
- Dodano wybór godziny wysyłki.
- Dodano trzy tryby wysyłki.
- Tryb domyślny wysyła o ustawionej godzinie, a jeżeli ceny na jutro nie są jeszcze opublikowane, czeka i wysyła je natychmiast po wykryciu publikacji.
- Powiadomienie zawiera ceny PB95, PB98 i ON na dzisiaj i jutro oraz informację `drożej o Xgr`, `taniej o Xgr` albo `bez zmian`.
- Wszystkie powiadomienia mobilne używają `ttl: 0` i `priority: high`.
- Dodano pamiętanie dostarczenia osobno dla każdego telefonu, aby przy ponowieniu nie dublować wiadomości na urządzeniach, które już ją otrzymały.
- Dodano konfigurację powiadomień w Options Flow Home Assistanta.
- Dodano `country: PL` do `hacs.json`.
- Zaktualizowano dokumentację i tłumaczenia.

## 1.0.0

- Pierwsze wydanie integracji.
- Obsługa PB95, PB98 i ON.
- Osobne encje ceny na dzisiaj i jutro.
- Encje zmiany ceny z tekstem `drożej o Xgr`, `taniej o Xgr`, `bez zmian` lub `Nie opublikowano`.
- Obsługa publikacji jednodniowych oraz zakresów obejmujących kilka dni.
- Automatyczne sprawdzanie danych co 30 minut.
- Konfiguracja z interfejsu Home Assistant.
- Instalacja przez HACS jako niestandardowe repozytorium.
- Diagnostyka integracji.
