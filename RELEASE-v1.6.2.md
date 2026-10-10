# Maksymalne Ceny Paliw GOV.PL v1.6.2

Poprawka kompatybilności i stabilności publicznego wydania.

Zmiany:
- przywrócono kompatybilny import `voluptuous`, dzięki czemu Config Flow działa także na Home Assistant sprzed przejścia Core na Probatio
- minimalna wspierana wersja Home Assistant to `2025.8.0`
- usunięto nieużywany w custom integrations plik `strings.json`
- poprawiono czyszczenie ostrzeżeń Repairs po usunięciu telefonu
- wzmocniono ochronę przed podwójnym automatycznym powiadomieniem przy równoległych aktualizacjach
- dodano Hassfest i HACS Action do walidacji repozytorium
- dodano automatyczny test importu integracji na Home Assistant `2025.8.0` i `2026.10.1`
- zaktualizowano README i sekcję rozwiązywania problemów
