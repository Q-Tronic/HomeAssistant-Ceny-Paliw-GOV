# Maksymalne Ceny Paliw GOV.PL v1.5.0

Rozbudowana aktualizacja powiadomień, diagnostyki i jakości repozytorium.

Nowości:

- osobny przycisk `Wyślij powiadomienie teraz` dla każdego telefonu
- sensor statusu ostatniego powiadomienia dla każdego telefonu
- sensor czasu ostatniego poprawnie wysłanego powiadomienia dla każdego telefonu
- sensor ostatniego udanego pobrania danych z GOV.PL
- trwała ochrona przed podwójną automatyczną wysyłką tej samej publikacji po restarcie Home Assistanta
- rozszerzone Repairs wykrywające świeżą publikację, której formatu zakresu dat parser nie rozpoznaje
- GitHub Actions uruchamiane przy każdym pushu i pull requeście
- automatyczna walidacja Python, parsera, JSON, YAML i zgodności numeru wersji
- kompletny przykład dashboardu
- przykład kolorowych kart zależnych od trendu ceny
- lepsze ikony zależne od aktualnego stanu encji
- rozbudowana diagnostyka telefonów

Wersja zachowuje dotychczasową konfigurację telefonów, indywidualne godziny wysyłki, wybór paliw i mechanizm oczekiwania na publikację.
