# Changelog

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
