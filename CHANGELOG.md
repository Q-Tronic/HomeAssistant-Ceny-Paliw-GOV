# Changelog

## 1.6.3

- naprawiono błędy testów, zgodność Hassfest i problem zależności DNS w CI dla HA 2025.8.0
- poprawiono brakujące dane binarnych sensorów trendu oraz czyszczenie `.storage` przy usuwaniu integracji
- zabezpieczono migrację wyłączonych starych powiadomień i równoległe edytowanie ustawień telefonów
- ulepszono wykrywanie niezrozumiałych nowych publikacji i awaryjną obsługę szablonów
- dodano testy regresyjne i zachowano dotychczasowe ikony

## 1.6.2

- zmieniono bezpośredni import `probatio` na kompatybilny `voluptuous as vol`
- zabezpieczono Reconfigure przed nieprawidłową lub starszą wartością interwału zapisaną w config entry
- ustawiono minimalną wspieraną wersję Home Assistant na `2025.8.0` w `hacs.json`
- usunięto `strings.json` i pozostawiono tłumaczenia w katalogu `translations`
- zmieniono import `EntityCategory` na publiczny import z `homeassistant.const`
- poprawiono czyszczenie Repairs po usunięciu telefonu z konfiguracji
- po usunięciu telefonu czyszczony jest także jego zapisany stan powiadomień, identyfikatory dostarczenia i czas ostatniej wysyłki
- dodano ponowną ochronę przed duplikatem już wewnątrz blokady wysyłki
- równoległa próba automatyczna, która po oczekiwaniu na blokadę nie ma już nic do wysłania, nie nadpisuje statusu ostatniej wysyłki
- poprawiono wnioskowanie roku dla publikacji bez roku w tytule na przełomie grudnia i stycznia
- poprawiono wynik ręcznego sprawdzania cen, aby błąd odświeżenia koordynatora nie był raportowany jako sukces
- poprawiono priorytet nakładających się publikacji w historii, aby nowsza korekta nie była nadpisywana starszą
- zabezpieczono konfigurację przed zduplikowanymi wpisami tego samego telefonu
- rozszerzono GitHub Actions o Hassfest, HACS Action i test importu na Home Assistant `2025.8.0` oraz `2026.10.1`
- dodano testy regresyjne kompatybilności i bezpieczeństwa wysyłki
- dodano nową ikonę integracji w `brand/icon.png` 256x256 oraz `brand/icon@2x.png` 512x512 z przezroczystością
- zachowano edytowalne źródło ikony w `assets/icon.svg`
- dodano test integralności i wymiarów plików brandingu
- rozszerzono test kompatybilności CI o import wszystkich modułów integracji
- uproszczono README, dodano wymagania, rozwiązywanie problemów i klikalny spis treści

## 1.6.1

- poprawiono ręczne wysyłanie powiadomienia do telefonu dodanego w Options Flow przed końcowym zapisem konfiguracji
- akcja `Wyślij wszystkim teraz` w konfiguracji korzysta teraz z aktualnych, również jeszcze niezapisanych ustawień telefonów
- usunięto z testów przykładowe nazwy i identyfikatory przypominające dane prawdziwych użytkowników
- dodano testy regresyjne dla ręcznych akcji wykonywanych przed zapisaniem Options Flow
- bez zmian w istniejących encjach, trybach automatycznych i zapisanych ustawieniach

## 1.6.0

- dodano osobny tryb wysyłki powiadomień dla każdego telefonu
- dodano tryby `O ustalonej godzinie`, `Po publikacji` oraz `Po publikacji tylko gdy cena się zmieni`
- istniejące i nowe telefony domyślnie używają trybu `O ustalonej godzinie`
- tryby publikacyjne ignorują godzinę i reagują po wykryciu nowej publikacji GOV.PL
- tryb publikacyjny ze zmianą używa wybranych paliw oraz wspólnego minimalnego progu zmiany ceny
- publikacja weekendowa jest w trybach publikacyjnych wysyłana tylko raz dla całego zakresu obowiązywania
- rozbudowano trwałą ochronę przed duplikatami o identyfikator publikacji źródłowej
- dodano encję `select` trybu wysyłki dla każdego telefonu
- zaktualizowano konfigurację, diagnostykę, przykłady dashboardu i dokumentację
- dodano testy regresyjne migracji i trybów powiadomień

## 1.5.4

- usunięto pustą linię z domyślnego powiadomienia z cenami
- usunięto pustą linię z komunikatu o braku publikacji cen na jutro
- ujednolicono bardziej kompaktowy wygląd powiadomień na Androidzie i iOS
- dodano test regresyjny formatu domyślnej wiadomości

## 1.5.3

- poprawiono błąd formatowania tłumaczenia po wybraniu telefonu
- usunięto dynamiczny placeholder `{device}` z tytułów kroków Options Flow
- nazwa telefonu jest teraz wyświetlana w opisie kroku, gdzie Home Assistant obsługuje `description_placeholders`
- dodano test regresyjny dla placeholderów w tytułach konfiguracji

## 1.5.2

- poprawiono zapisywanie konfiguracji telefonów
- usunięto konflikt podwójnego przeładowania integracji po zmianie opcji
- dodano bezpieczną normalizację wyboru jednego lub wielu telefonów
- dodano testy regresyjne dla konfiguracji telefonów


## 1.5.1

- Zwiększono prywatność danych diagnostycznych.
- Nazwy telefonów są maskowane w diagnostyce.
- Identyfikatory usług `notify.mobile_app_*` są maskowane w diagnostyce.
- Lista brakujących celów powiadomień została zastąpiona samą liczbą brakujących celów.
- Dodano test regresyjny chroniący przed ponownym ujawnieniem nazw i identyfikatorów telefonów w diagnostyce.
- Bez zmian w działaniu powiadomień, harmonogramów i encji użytkownika.

## 1.5.0

- Dodano przycisk `Wyślij powiadomienie teraz` jako osobną encję `button` dla każdego skonfigurowanego telefonu.
- Dodano diagnostyczny sensor statusu ostatniego powiadomienia dla każdego telefonu.
- Dodano diagnostyczny sensor czasu ostatniego poprawnie wysłanego powiadomienia dla każdego telefonu.
- Dodano diagnostyczny sensor ostatniego udanego pobrania danych z GOV.PL.
- Dodano trwały identyfikator dostarczonej publikacji osobno dla każdego telefonu, co chroni przed ponowną automatyczną wysyłką po restarcie Home Assistanta.
- Rozszerzono Repairs o wykrywanie świeżej publikacji z cenami, której nowego formatu zakresu dat parser nie potrafi rozpoznać.
- Dodano GitHub Actions uruchamiane przy każdym pushu i pull requeście.
- Dodano automatyczną kontrolę składni Python, testów parsera, JSON, YAML oraz spójności wersji.
- Dodano skrypt `scripts/check_version_consistency.py`, który porównuje wersję w `manifest.json`, `const.py`, `CHANGELOG.md`, `README.md` i pliku Release.
- Dodano kompletny przykład dashboardu.
- Dodano przykład kolorowych kart dashboardu zależnych od trendu ceny.
- Rozszerzono przykład dashboardu telefonu o status, czas ostatniej wysyłki i przycisk ręcznej wysyłki.
- Rozszerzono dynamiczne ikony encji dla trendów, statusów i przełączników powiadomień.
- Zaktualizowano diagnostykę integracji o stan każdego telefonu.

## 1.4.0

- Zmieniono nazwę integracji na `Maksymalne Ceny Paliw GOV.PL`.
- Dodano osobny `switch` dla każdego telefonu, który włącza lub wyłącza automatyczne powiadomienia z dashboardu.
- Dodano osobną encję `time` dla każdego telefonu do ustawiania godziny codziennej wiadomości.
- Dodano osobną encję `select` dla każdego telefonu do wyboru PB95, PB98, ON, dwóch paliw albo wszystkich trzech.
- Przebudowano scheduler powiadomień na harmonogram per telefon.
- Jeżeli cena nie jest opublikowana o godzinie danego telefonu, tylko ten telefon czeka na publikację i dostaje wiadomość po jej wykryciu.
- Telefon z późniejszą godziną czeka do swojej godziny, nawet gdy publikacja pojawiła się wcześniej.
- Ustawienia zmieniane przez encje dashboardu są zapisywane od razu, bez restartu Home Assistanta.
- Dodano migrację ustawień telefonów z wersji 1.3.x do modelu per telefon.
- Dodano prawdziwy reconfigure flow dla interwału sprawdzania gov.pl.
- Dostępne interwały sprawdzania: 5, 10, 15, 30 i 60 minut.
- Sensor statusu publikacji oznaczono kategorią `diagnostic`.
- Zaktualizowano diagnostykę, menu konfiguracji, tłumaczenia i README.
- Usunięto z paczki plik `AKTUALIZACJA-GITHUB-DESKTOP.md`.

## 1.3.1

- Poprawiono wykrywanie weekendowych publikacji GOV.PL zapisanych jako `obowiązująca w dniach`.
- Zachowano obsługę wariantu `w okresie`.
- Dodano test regresyjny dla publikacji weekendowej.

## 1.3.0

- Dodano historię i statystyki cen z 7, 30 i 90 dni.
- Dodano status publikacji, przyciski akcji, diagnostykę, Repairs, event aktualizacji i sensory binarne trendu.
- Rozbudowano konfigurację powiadomień i obsługę telefonów.