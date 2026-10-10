# Maksymalne Ceny Paliw GOV.PL v1.5.2

Poprawka zapisywania konfiguracji telefonów.

Zmiany:
- usunięto podwójny mechanizm przeładowania integracji po zapisie opcji
- integracja korzysta teraz wyłącznie z automatycznego reloadu `OptionsFlowWithReload`
- zabezpieczono wybór pojedynczego telefonu, gdy Home Assistant zwróci wartość jako tekst zamiast listy
- odrzucane są nieznane cele powiadomień, których nie ma na liście dostępnych telefonów
- dodano testy regresyjne konfiguracji telefonów
- bez zmian w istniejących encjach i ustawieniach użytkownika
