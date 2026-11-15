# Ceny paliw GOV.PL v1.3.1

Poprawka pobierania weekendowych cen paliw.

Najważniejsze zmiany:

- naprawiono rozpoznawanie publikacji GOV.PL z zakresem zapisanym jako `w dniach`, np. `10-12 października 2026 r.`
- zachowano obsługę publikacji z zakresem `w okresie`
- dodano test regresyjny dla formatu użytego przez Ministerstwo Energii 9 października 2026 r.
- bez zmian w konfiguracji i istniejących encjach

Po aktualizacji wymagany jest restart Home Assistant.
