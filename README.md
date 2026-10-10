# Maksymalne Ceny Paliw GOV.PL

Niestandardowa integracja Home Assistant autorstwa **Q-Tronic**. Pobiera maksymalne detaliczne ceny paliw publikowane przez Ministerstwo Energii na gov.pl, tworzy encje dla cen dzisiejszych i jutrzejszych, prowadzi lokalną historię oraz wysyła konfigurowalne powiadomienia na telefony z aplikacją Home Assistant Companion.

Aktualna wersja: **1.4.0**.

## Najważniejsze funkcje

Integracja obsługuje PB95, PB98 i ON. Domyślnie gov.pl jest sprawdzane co 30 minut. Interwał można zmienić przez opcję `Reconfigure` integracji.

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

## Nowości w 1.4.0

### Osobne ustawienia każdego telefonu jako encje Home Assistant

Administrator najpierw dodaje telefon w konfiguracji integracji. Po zapisaniu integracja tworzy dla każdego telefonu trzy encje przeznaczone do sterowania z dashboardu:

```text
switch.<nazwa_telefonu>_powiadomienia
time.<nazwa_telefonu>_godzina_powiadomienia
select.<nazwa_telefonu>_paliwa_w_powiadomieniu
```

Dokładny `entity_id` zależy od nazwy telefonu i istniejących encji w danej instalacji Home Assistant.

`switch` pozwala użytkownikowi samodzielnie włączyć lub wyłączyć automatyczne wiadomości dla swojego telefonu.

`time` ustawia osobną godzinę wysyłki dla tego telefonu.

`select` pozwala wybrać jeden z wariantów:

```text
PB95
PB98
ON
PB95 + PB98
PB95 + ON
PB98 + ON
PB95 + PB98 + ON
```

Zmiany wykonane z dashboardu są zapisywane bez konieczności ponownego uruchamiania Home Assistanta.

### Indywidualna godzina i oczekiwanie na publikację

Każdy telefon ma własny harmonogram.

Jeżeli o ustawionej dla telefonu godzinie ceny na jutro są już opublikowane, wiadomość zostanie wysłana od razu.

Jeżeli ceny nie zostały jeszcze opublikowane, integracja oznacza tylko ten telefon jako oczekujący. Gdy później wykryje publikację, wiadomość zostanie wysłana właśnie na telefony, których godzina już minęła i które czekały na dane.

Telefon ustawiony na późniejszą godzinę nadal czeka do swojej własnej godziny, nawet jeżeli publikacja pojawiła się wcześniej.

### Konfiguracja administratora i konfiguracja użytkownika

Administrator decyduje, które telefony są dodane do integracji. Użytkownik dashboardu może następnie dla swojego telefonu zmieniać:

- włączenie lub wyłączenie powiadomień
- godzinę wysyłki
- paliwa obecne w wiadomości

Nazwa telefonu, dodawanie i usuwanie telefonu oraz akcje testowe nadal są dostępne w menu `Konfiguruj` integracji.

### Reconfigure flow

Integracja posiada osobny `Reconfigure` flow. Pozwala zmienić częstotliwość automatycznego sprawdzania gov.pl bez usuwania i ponownego dodawania integracji.

Dostępne interwały:

```text
5 min
10 min
15 min
30 min
60 min
```

### Lepsze uporządkowanie encji technicznych

Sensor `Status publikacji cen paliw` jest oznaczony jako encja diagnostyczna Home Assistanta. Dzięki temu dane techniczne pozostają dostępne, ale nie mieszają się z głównymi encjami użytkowymi urządzenia.

### Migracja ustawień z 1.3.x

Przy pierwszym uruchomieniu 1.4.0 istniejące telefony automatycznie dostają własne ustawienia godziny i paliw. Integracja użyje jako wartości startowych dotychczasowej wspólnej godziny i wspólnego wyboru paliw.

Po migracji każdy telefon można ustawiać niezależnie.

## Status publikacji

Encja:

```text
sensor.status_publikacji_cen_paliw
```

jest encją diagnostyczną i może mieć stany:

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
- włączyć lub wyłączyć automatyczne powiadomienia
- ustawić początkową godzinę
- wybrać początkowy zakres paliw
- wybrać `Wyślij test`
- wybrać `Wyślij powiadomienie teraz`

Po zapisaniu trzy podstawowe ustawienia telefonu są dostępne również jako encje dashboardu.

### Przykład domyślnego powiadomienia

```text
Maksymalne ceny paliw na jutro, 11.10.2026

PB95: dziś 6,90 zł/l, jutro 6,97 zł/l, drożej o 7gr
PB98: dziś 7,80 zł/l, jutro 7,85 zł/l, drożej o 5gr
ON: dziś 8,08 zł/l, jutro 8,06 zł/l, taniej o 2gr
```

Każdy telefon otrzymuje tylko te paliwa, które są wybrane w jego własnej encji `select`.

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

Jeżeli używasz własnej treści szablonu, sam decydujesz, które zmienne znajdą się w wiadomości. Automatyczne ograniczenie wiadomości do paliw wybranych dla telefonu dotyczy domyślnej treści.

## Filtr zmian

Można włączyć wysyłkę tylko wtedy, gdy co najmniej jedno paliwo wybrane dla konkretnego telefonu zmieni cenę.

Można również ustawić minimalną zmianę w groszach. Przykład: `5gr` oznacza, że wiadomość dla danego telefonu zostanie wysłana tylko wtedy, gdy co najmniej jedno z paliw wybranych dla tego telefonu zmieni cenę o minimum 5gr.

## Przyciski

Integracja udostępnia:

```text
button.sprawdz_ceny_teraz
button.wyslij_wszystkim_teraz
```

`Sprawdź ceny teraz` wymusza natychmiastowe pobranie danych z gov.pl.

`Wyślij wszystkim teraz` wysyła bieżący komunikat do wszystkich aktualnie włączonych telefonów. Każdy telefon dostaje własny zakres paliw.

## Dashboard telefonu

Przykład karty z trzema ustawieniami jednego telefonu znajduje się w:

```text
examples/dashboard-phone.yaml
```

Po dodaniu telefonu w konfiguracji integracji odszukaj jego trzy encje i podmień przykładowe identyfikatory w YAML.

## Historia cen

Integracja prowadzi lokalną historię do 120 dni i tworzy średnie dla 7, 30 i 90 dni osobno dla PB95, PB98 oraz ON.

Przykładowe encje:

```text
sensor.srednia_pb95_7_dni
sensor.srednia_pb95_30_dni
sensor.srednia_pb95_90_dni
```

Każdy sensor historii zawiera minimum, maksimum, liczbę próbek, pierwszą i ostatnią cenę oraz zmianę procentową.

## Encje binarne

Dla każdego paliwa dostępna jest encja informująca, czy jutro będzie drożej:

```text
binary_sensor.pb95_jutro_drozej
binary_sensor.pb98_jutro_drozej
binary_sensor.on_jutro_drozej
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

Jeżeli układ strony gov.pl zmieni się i parser przestanie rozpoznawać publikacje, integracja tworzy ostrzeżenie w sekcji Naprawy Home Assistanta.

Jeżeli skonfigurowany i włączony telefon przestanie istnieć jako `notify.mobile_app_*`, integracja również tworzy ostrzeżenie.

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
