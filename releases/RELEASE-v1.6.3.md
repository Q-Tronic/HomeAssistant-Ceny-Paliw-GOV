# Maksymalne Ceny Paliw GOV.PL v1.6.3

Wydanie naprawcze po audycie v1.6.2.

- naprawiono błąd testów związany z pozostawionym `strings.json`
- uporządkowano klucze `manifest.json` zgodnie z Hassfest
- poprawiono środowisko CI dla Home Assistant 2025.8.0 przez zgodne zależności DNS
- sensory binarne mają stan `unknown`, gdy brakuje ceny do porównania
- dodano usuwanie historii i stanu powiadomień po usunięciu integracji
- zachowano wyłączenie powiadomień przy bezpośredniej migracji ze starej konfiguracji globalnej
- zabezpieczono równoległą edycję telefonów w Options Flow i na dashboardzie
- rozszerzono detekcję nierozpoznanych nowych publikacji GOV.PL
- nieprawidłowy szablon powiadomienia nie blokuje awaryjnej treści domyślnej
- dodano testy regresyjne napraw v1.6.3
- zachowano bez zmian dotychczasowe ikony PNG i SVG

Wymagania: Home Assistant 2025.8.0 lub nowszy.

Uwaga: lokalne testy modułowe nie zastępują pełnego uruchomienia w HA.
