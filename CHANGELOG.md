# Changelog

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
