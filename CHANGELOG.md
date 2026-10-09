# Changelog

## 1.3.1

- Naprawiono pobieranie cen weekendowych, gdy GOV.PL używa w tytule zwrotu `w dniach`, np. `10-12 października 2026 r.`.
- Zachowano obsługę wcześniejszego wariantu `w okresie`.
- Dodano test regresyjny na rzeczywistym formacie publikacji z 9 października 2026 r.

## 1.3.0

- Dodano menu konfiguracji podzielone na harmonogram, treść, filtry, telefony i diagnostykę.
- Dodano wybór paliw widocznych w powiadomieniach.
- Dodano własny tytuł i treść powiadomień z obsługą szablonów Home Assistant.
- Dodano opcję wysyłania tylko przy zmianie ceny.
- Dodano minimalny próg zmiany w groszach.
- Dodano sensor statusu publikacji i pobierania danych.
- Dodano przycisk `Sprawdź ceny teraz`.
- Dodano przycisk `Wyślij wszystkim teraz`.
- Dodano lokalną historię cen do 120 dni.
- Dodano sensory średnich cen dla 7, 30 i 90 dni dla PB95, PB98 i ON.
- Dodano minimum, maksimum, liczbę próbek i zmianę procentową w atrybutach statystyk.
- Dodano binarne sensory informujące, czy dane paliwo będzie jutro droższe.
- Dodano atrybut `trend` i procentową zmianę ceny do encji porównawczych.
- Dodano zdarzenie `ceny_paliw_gov_pl_updated` przy zmianie pobranych danych.
- Dodano ostrzeżenie Repairs, gdy parser gov.pl przestanie rozpoznawać publikacje.
- Dodano ostrzeżenie Repairs dla niedostępnego skonfigurowanego telefonu.
- Rozbudowano standardową diagnostykę Home Assistanta.
- Dodano gotowy przykład karty Lovelace.
- Dodano przykładową automatyzację reagującą na zdarzenie aktualizacji.
- Zachowano indywidualne podmenu telefonów, test powiadomienia oraz ręczne wysyłanie bieżącej wiadomości.

## 1.2.1

- Poprawne wydanie zmian interfejsu powiadomień z linii 1.2.

## 1.2.0

- Dodano menu i podmenu konfiguracji telefonów.
- Dodano ręczne wysłanie testu oraz bieżącego powiadomienia.

## 1.1.0

- Dodano konfigurowalne powiadomienia mobilne.

## 1.0.0

- Pierwsze publiczne wydanie.
