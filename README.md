# Maksymalne Ceny Paliw GOV.PL

Niestandardowa integracja Home Assistant autorstwa **Q-Tronic**. Pobiera maksymalne detaliczne ceny paliw publikowane przez Ministerstwo Energii na gov.pl, tworzy encje dla cen dzisiejszych i jutrzejszych, prowadzi lokalną historię oraz wysyła konfigurowalne powiadomienia na telefony z aplikacją Home Assistant Companion.

Aktualna wersja: **v1.5.0**.

## Najważniejsze funkcje

Integracja obsługuje PB95, PB98 i ON. Domyślnie gov.pl jest sprawdzane co 30 minut. Interwał można zmienić przez `Reconfigure` integracji.

Podstawowe encje cen:

```text
sensor.cena_pb95_dzisiaj
sensor.cena_pb95_jutro
sensor.pb95_zmiana_ceny
sensor.cena_pb98_dzisiaj
sensor.cena_pb98_jutro
sensor.pb98_zmiana_ceny
sensor.cena_on_dzisiaj
sensor.cena_on_jutro
sensor.on_zmiana_ceny
```

Jeżeli cena na jutro nie została jeszcze opublikowana, encja pokazuje:

```text
Nie opublikowano
```

Encja zmiany ceny pokazuje na przykład:

```text
drożej o 7gr
taniej o 2gr
bez zmian
Nie opublikowano
```

Ikony encji zmiany ceny reagują na trend. Wzrost pokazuje ikonę wzrostu, spadek ikonę spadku, brak zmiany ikonę neutralną, a brak publikacji ikonę informacyjną.

## Nowości w v1.5.0

### Przycisk wysyłki dla każdego telefonu

Każdy telefon dodany przez administratora otrzymuje dodatkową encję przycisku:

```text
button.<nazwa_telefonu>_wyslij_powiadomienie_teraz
```

Naciśnięcie przycisku odświeża dane GOV.PL i wysyła na ten telefon normalne powiadomienie dzienne z jego indywidualnie wybranymi paliwami.

### Status ostatniego powiadomienia dla każdego telefonu

Każdy telefon otrzymuje sensor diagnostyczny:

```text
sensor.<nazwa_telefonu>_status_ostatniego_powiadomienia
```

Możliwe stany obejmują:

```text
Brak wysyłki
Oczekuje na publikację
Wysłano
Błąd
Pominięto filtrem
```

Ikona sensora zmienia się zależnie od statusu.

### Czas ostatniego wysłanego powiadomienia

Każdy telefon otrzymuje sensor czasu:

```text
sensor.<nazwa_telefonu>_ostatnie_powiadomienie
```

Sensor zapisuje czas ostatniej poprawnie wysłanej wiadomości. Informacja jest przechowywana w pamięci trwałej integracji i pozostaje dostępna po restarcie Home Assistanta.

### Ostatnie udane pobranie GOV.PL

Dodano diagnostyczny sensor czasu:

```text
sensor.ostatnie_udane_pobranie_gov_pl
```

Sensor pozwala łatwo rozróżnić problem z publikacją od problemu z połączeniem albo parserem.

### Trwała ochrona przed duplikatami

Integracja zapisuje identyfikator konkretnej publikacji wraz z dniem, którego dotyczy wiadomość, osobno dla każdego telefonu. Jeżeli Home Assistant zostanie uruchomiony ponownie po wysłaniu wiadomości, ten sam komunikat dla tego samego dnia nie zostanie automatycznie wysłany ponownie na ten sam telefon. Publikacje weekendowe nadal mogą wygenerować osobne wiadomości w kolejnych dniach, ponieważ zmienia się dzień docelowy.

Ręczne użycie przycisku `Wyślij powiadomienie teraz` nadal zawsze wykonuje żądaną wysyłkę. Jeżeli aktualne ceny na jutro są już opublikowane, ręczna wysyłka oznacza tę publikację jako dostarczoną dla danego telefonu, dzięki czemu późniejszy harmonogram nie wyśle jej drugi raz automatycznie.

### Rozszerzone Repairs

Integracja wykrywa sytuację, w której na GOV.PL pojawia się świeża publikacja z kompletem cen, ale parser nie potrafi rozpoznać jej zakresu obowiązywania. W takiej sytuacji tworzony jest problem w sekcji Naprawy Home Assistanta.

Mechanizm wykrywa również brak skonfigurowanego celu `notify.mobile_app_*` dla włączonego telefonu.

### GitHub Actions

Repozytorium zawiera workflow:

```text
.github/workflows/validate.yml
```

Przy każdym pushu i pull requeście automatycznie wykonywane są:

- sprawdzenie składni Python
- testy parsera
- walidacja JSON i YAML
- kontrola zgodności numeru wersji

Workflow używa `actions/checkout@v7` i `actions/setup-python@v7`.

### Automatyczna kontrola wersji

Skrypt:

```text
scripts/check_version_consistency.py
```

sprawdza zgodność wersji pomiędzy:

```text
custom_components/ceny_paliw_gov_pl/manifest.json
custom_components/ceny_paliw_gov_pl/const.py
CHANGELOG.md
README.md
RELEASE-vX.Y.Z.md
```

Dzięki temu błędny release z innym numerem wersji powinien zostać wykryty przez GitHub Actions przed publikacją.

## Ustawienia telefonu dostępne na dashboardzie

Administrator najpierw dodaje telefon w konfiguracji integracji. Dla każdego telefonu tworzone są encje:

```text
switch.<nazwa_telefonu>_powiadomienia
time.<nazwa_telefonu>_godzina_powiadomienia
select.<nazwa_telefonu>_paliwa_w_powiadomieniu
button.<nazwa_telefonu>_wyslij_powiadomienie_teraz
sensor.<nazwa_telefonu>_status_ostatniego_powiadomienia
sensor.<nazwa_telefonu>_ostatnie_powiadomienie
```

Dokładny `entity_id` zależy od nazwy telefonu i istniejących encji w danej instalacji Home Assistant.

`switch` pozwala użytkownikowi włączyć albo wyłączyć automatyczne powiadomienia dla swojego telefonu.

`time` ustawia indywidualną godzinę wysyłki.

`select` pozwala wybrać:

```text
PB95
PB98
ON
PB95 + PB98
PB95 + ON
PB98 + ON
PB95 + PB98 + ON
```

`button` wysyła aktualne powiadomienie natychmiast.

Sensory statusu i czasu ostatniej wysyłki pozwalają użytkownikowi sprawdzić, co ostatnio zrobiła integracja.

Zmiany `switch`, `time` i `select` są zapisywane bez konieczności ponownego uruchamiania Home Assistanta.

## Indywidualna godzina i oczekiwanie na publikację

Każdy telefon ma własny harmonogram.

Jeżeli o ustawionej godzinie ceny na jutro są już opublikowane, wiadomość zostanie wysłana od razu.

Jeżeli ceny nie zostały jeszcze opublikowane, telefon otrzymuje status:

```text
Oczekuje na publikację
```

Po wykryciu publikacji wiadomość zostanie wysłana automatycznie tylko do telefonów, których ustawiona godzina już minęła.

Telefon ustawiony na późniejszą godzinę czeka do swojej własnej godziny, nawet jeżeli publikacja pojawiła się wcześniej.

## Reconfigure flow

Integracja posiada osobny `Reconfigure` flow. Pozwala zmienić częstotliwość automatycznego sprawdzania gov.pl bez usuwania i ponownego dodawania integracji.

Dostępne interwały:

```text
5 min
10 min
15 min
30 min
60 min
```

## Encje diagnostyczne

Techniczne informacje są oznaczone jako encje diagnostyczne, dzięki czemu nie zaśmiecają głównego widoku urządzenia.

Dotyczy to między innymi:

```text
sensor.status_publikacji_cen_paliw
sensor.ostatnie_udane_pobranie_gov_pl
sensor.<telefon>_status_ostatniego_powiadomienia
sensor.<telefon>_ostatnie_powiadomienie
```

## Status publikacji

Encja:

```text
sensor.status_publikacji_cen_paliw
```

może mieć stany:

```text
Opublikowano
Oczekiwanie na publikację
Błąd pobierania
Dane nieaktualne
```

Jej atrybuty zawierają między innymi czas ostatniego pobrania, ostatni błąd, liczbę znalezionych publikacji, źródło oraz niedostępne cele powiadomień.

## Powiadomienia

Konfigurację administratora znajdziesz w:

```text
Ustawienia > Urządzenia i usługi > Maksymalne Ceny Paliw GOV.PL > Konfiguruj
```

Menu zawiera:

- `Telefony`
- `Powiadomienia: treść`
- `Powiadomienia: filtry zmian`
- `Diagnostyka i akcje`
- `Zapisz i zakończ`

Każdy telefon ma osobne podmenu. Administrator może:

- nadać własną nazwę
- włączyć albo wyłączyć automatyczne powiadomienia
- ustawić początkową godzinę
- wybrać początkowy zakres paliw
- wysłać test
- wysłać normalne powiadomienie natychmiast

### Przykład domyślnego powiadomienia

```text
Maksymalne ceny paliw na jutro, 11.10.2026

PB95: dziś 6,90 zł/l, jutro 6,97 zł/l, drożej o 7gr
PB98: dziś 7,80 zł/l, jutro 7,85 zł/l, drożej o 5gr
ON: dziś 8,08 zł/l, jutro 8,06 zł/l, taniej o 2gr
```

Każdy telefon otrzymuje tylko paliwa wybrane w jego encji `select`.

## Własny tytuł i treść

Można pozostawić format domyślny albo podać globalny własny szablon Home Assistant.

Dostępne zmienne:

```text
today_date
tomorrow_date
published
pb95
pb98
on
```

Dla każdego paliwa dostępne są między innymi:

```text
pb95.today
pb95.tomorrow
pb95.today_text
pb95.tomorrow_text
pb95.change
pb95.difference_grosz
```

## Filtr zmian

Można włączyć wysyłkę tylko wtedy, gdy co najmniej jedno paliwo wybrane dla konkretnego telefonu zmieni cenę.

Można również ustawić minimalną zmianę w groszach. Przykład: `5gr` oznacza, że wiadomość zostanie wysłana tylko wtedy, gdy co najmniej jedno wybrane paliwo zmieni cenę o minimum 5gr.

## Przyciski globalne

Integracja udostępnia:

```text
button.sprawdz_ceny_teraz
button.wyslij_wszystkim_teraz
```

`Sprawdź ceny teraz` wymusza natychmiastowe pobranie danych z gov.pl.

`Wyślij wszystkim teraz` wysyła bieżący komunikat do wszystkich aktualnie włączonych telefonów. Każdy telefon otrzymuje własny zakres paliw.

## Historia cen

Integracja prowadzi lokalną historię do 120 dni i tworzy średnie dla 7, 30 i 90 dni osobno dla PB95, PB98 oraz ON.

Przykładowe encje:

```text
sensor.srednia_pb95_7_dni
sensor.srednia_pb95_30_dni
sensor.srednia_pb95_90_dni
```

Każdy sensor historii zawiera minimum, maksimum, liczbę próbek, pierwszą i ostatnią cenę oraz zmianę procentową.

## Encje binarne trendu

Dla każdego paliwa dostępna jest encja informująca, czy jutro będzie drożej:

```text
binary_sensor.pb95_jutro_drozej
binary_sensor.pb98_jutro_drozej
binary_sensor.on_jutro_drozej
```

Ikona encji zależy od aktualnego trendu ceny.

## Gotowe przykłady dashboardu

W katalogu `examples` znajdują się gotowe pliki:

```text
examples/dashboard-phone.yaml
examples/dashboard-complete.yaml
examples/dashboard-colored.yaml
examples/lovelace-card.yaml
```

`dashboard-phone.yaml` zawiera konfigurację jednego telefonu, w tym przycisk wysyłki, status i czas ostatniego powiadomienia.

`dashboard-complete.yaml` jest przykładem kompletnego widoku zawierającego ceny, historię, sterowanie telefonem i akcje.

`dashboard-colored.yaml` pokazuje wbudowane karty Home Assistant, które zmieniają kolor zależnie od trendu:

```text
czerwony: drożej
zielony: taniej
szary: bez zmian
bursztynowy: brak publikacji
```

Przykłady używają wyłącznie wbudowanych kart Home Assistant. Nie wymagają dodatkowej karty z HACS.

Po wklejeniu YAML podmień przykładowe identyfikatory telefonu na encje istniejące w Twoim Home Assistant.

### Szybki przykład karty użytkownika

```yaml
type: entities
title: Powiadomienia paliwowe
entities:
  - entity: switch.telefon_uzytkownika_powiadomienia
    name: Powiadomienia
  - entity: time.telefon_uzytkownika_godzina_powiadomienia
    name: Godzina
  - entity: select.telefon_uzytkownika_paliwa_w_powiadomieniu
    name: Paliwa
  - entity: sensor.telefon_uzytkownika_status_ostatniego_powiadomienia
    name: Status
  - entity: sensor.telefon_uzytkownika_ostatnie_powiadomienie
    name: Ostatnio wysłano
  - entity: button.telefon_uzytkownika_wyslij_powiadomienie_teraz
    name: Wyślij powiadomienie teraz
```

## Zdarzenie aktualizacji

Gdy integracja wykryje zmianę danych, emituje zdarzenie:

```text
ceny_paliw_gov_pl_updated
```

Przykład automatyzacji znajduje się w:

```text
examples/automation-event.yaml
```

## Repairs

Integracja tworzy problem w sekcji Naprawy Home Assistanta, gdy:

- strona GOV.PL nie daje się poprawnie sparsować
- pojawi się świeża publikacja z cenami, ale nowy format zakresu dat nie zostanie rozpoznany
- skonfigurowany i włączony telefon przestanie istnieć jako `notify.mobile_app_*`

## Obsługa publikacji weekendowych

Parser obsługuje publikacje dla pojedynczego dnia oraz zakresy kilku dni, w tym warianty tytułów zawierające `w okresie` oraz `w dniach`.

## Źródło danych

Oficjalna strona Ministerstwa Energii:

```text
https://www.gov.pl/web/energia/wiadomosci
```

## Instalacja przez HACS

1. Otwórz HACS.
2. Wejdź w Integracje.
3. Dodaj niestandardowe repozytorium:

```text
https://github.com/Q-Tronic/HomeAssistant-Ceny-Paliw-GOV
```

4. Typ repozytorium: `Integration`.
5. Zainstaluj `Maksymalne Ceny Paliw GOV.PL`.
6. Uruchom ponownie Home Assistant.
7. Wejdź w `Ustawienia > Urządzenia i usługi > Dodaj integrację`.
8. Wyszukaj `Maksymalne Ceny Paliw GOV.PL` i dodaj integrację.

## Aktualizacja przez HACS

Po opublikowaniu nowego GitHub Release HACS powinien wykryć nową wersję. Jeżeli chcesz wymusić sprawdzenie, użyj `Update information` w menu repozytorium HACS. Po pobraniu nowej wersji uruchom ponownie Home Assistant.

## Instalacja ręczna

Skopiuj katalog:

```text
custom_components/ceny_paliw_gov_pl
```

do katalogu:

```text
/config/custom_components/ceny_paliw_gov_pl
```

Następnie uruchom ponownie Home Assistant i dodaj integrację z interfejsu.

## Autor

Q-Tronic

## Licencja

MIT
