# Maksymalne Ceny Paliw GOV.PL v1.6.4

Wydanie naprawcze eliminujące błędy sensorów numerycznych przy braku danych.

- Naprawiono `ValueError` podczas dodawania sensorów cen na jutro, gdy GOV.PL nie opublikował jeszcze danych.
- Poprawiono średnie cen z pustą historią: numeryczne sensory nie zwracają już komunikatu tekstowego.
- Zachowano status braku danych w atrybutach sensorów i poprawiono rozpoznawanie brakującej ceny konkretnego paliwa.
- Dodano testy regresyjne obejmujące nieopublikowane ceny, częściowe dane i pustą historię.
- Bez zmian w identyfikatorach encji, ikonach, ustawieniach i powiadomieniach.

**Uwaga:** brak danych w sensorze numerycznym jest reprezentowany przez `None`, czyli stan `unknown` w Home Assistant. Tekst `Nie opublikowano` pozostaje w sensorach opisowych i powiadomieniach. Minimalna wersja HA: `2025.8.0`.
