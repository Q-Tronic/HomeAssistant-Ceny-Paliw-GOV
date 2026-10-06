# Ceny paliw GOV.PL

Niestandardowa integracja Home Assistant autorstwa **Q-Tronic**. Pobiera maksymalne detaliczne ceny paliw publikowane przez Ministerstwo Energii na gov.pl, tworzy encje dla cen dzisiejszych i jutrzejszych, prowadzi lokalną historię i może wysyłać powiadomienia na telefony z aplikacją Home Assistant Companion.

Aktualna wersja: **1.3.0**.

## Najważniejsze funkcje

Integracja obsługuje PB95, PB98 i ON. Ceny są sprawdzane automatycznie co 30 minut.

Podstawowe encje:

- `sensor.cena_pb95_dzisiaj`
- `sensor.cena_pb95_jutro`
- `sensor.pb95_zmiana_ceny`
- `sensor.cena_pb98_dzisiaj`
- `sensor.cena_pb98_jutro`
- `sensor.pb98_zmiana_ceny`
- `sensor.cena_on_dzisiaj`
- `sensor.cena_on_jutro`
- `sensor.on_zmiana_ceny`

Jeżeli cena na jutro nie została jeszcze opublikowana, encja pozostaje czytelna i pokazuje:

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

Atrybuty encji zmiany zawierają także różnicę w złotych, groszach i procentach oraz pole `trend` o wartości `up`, `down`, `equal` albo `not_published`.

## Nowości w 1.3.0

### Status publikacji

Nowa encja:

```text
sensor.status_publikacji_cen_paliw
```

Możliwe stany:

```text
Opublikowano
Oczekiwanie na publikację
Błąd pobierania
Dane nieaktualne
```

Atrybuty pokazują między innymi ostatnie pobranie, ostatni błąd, liczbę znalezionych publikacji, źródło oraz ewentualne niedostępne cele powiadomień.

### Przyciski

Integracja dodaje dwa przyciski Home Assistant:

```text
button.sprawdz_ceny_teraz
button.wyslij_wszystkim_teraz
```

`Sprawdź ceny teraz` wymusza natychmiastowe pobranie danych z gov.pl.

`Wyślij wszystkim teraz` odświeża dane i wysyła bieżący komunikat dzienny do wszystkich włączonych telefonów. Ręczne wysłanie nie zmienia informacji o tym, czy automatyczne powiadomienie zostało już wysłane danego dnia.

### Historia 7, 30 i 90 dni

Integracja prowadzi lokalną historię cen i tworzy sensory średnich dla każdego paliwa:

```text
sensor.srednia_pb95_7_dni
sensor.srednia_pb95_30_dni
sensor.srednia_pb95_90_dni
sensor.srednia_pb98_7_dni
sensor.srednia_pb98_30_dni
sensor.srednia_pb98_90_dni
sensor.srednia_on_7_dni
sensor.srednia_on_30_dni
sensor.srednia_on_90_dni
```

Każdy sensor ma atrybuty z minimum, maksimum, liczbą próbek, pierwszą i ostatnią ceną oraz zmianą procentową.

Historia jest przechowywana lokalnie przez integrację do 120 dni. Przy pierwszym uruchomieniu integracja zapisuje okresy cenowe dostępne na aktualnie pobranej stronie gov.pl, a następnie uzupełnia historię przy kolejnych aktualizacjach. Jeżeli gov.pl nie udostępnia na bieżącej stronie pełnych 90 dni danych, pełne okno 90 dni zapełni się z czasem.

### Encje binarne drożej jutro

Dla każdego paliwa dostępna jest encja binarna:

```text
binary_sensor.pb95_jutro_drozej
binary_sensor.pb98_jutro_drozej
binary_sensor.on_jutro_drozej
```

Stan `on` oznacza, że cena jutro jest wyższa niż dzisiaj. Atrybuty pokazują różnicę oraz informację, czy dane na jutro zostały opublikowane.

### Zdarzenie aktualizacji

Gdy podczas działania Home Assistanta integracja wykryje zmianę danych, emituje zdarzenie:

```text
ceny_paliw_gov_pl_updated
```

Przykład automatyzacji znajduje się w:

```text
examples/automation-event.yaml
```

### Repairs

Jeżeli układ strony gov.pl zmieni się i parser przestanie rozpoznawać publikacje, integracja tworzy ostrzeżenie w sekcji Naprawy Home Assistanta.

Jeżeli skonfigurowany telefon przestanie istnieć jako `notify.mobile_app_*`, integracja również tworzy ostrzeżenie zamiast jedynie pomijać błąd wysyłki.

## Powiadomienia

Konfigurację znajdziesz w:

```text
Ustawienia > Urządzenia i usługi > Ceny paliw GOV.PL > Konfiguruj
```

Menu konfiguracji jest podzielone na sekcje:

- `Powiadomienia: harmonogram`
- `Powiadomienia: treść i paliwa`
- `Powiadomienia: filtry zmian`
- `Telefony`
- `Diagnostyka i akcje`
- `Zapisz i zakończ`

### Harmonogram

Dostępne są trzy tryby:

1. `O ustawionej godzinie`
2. `Natychmiast po publikacji nowych cen`
3. `O ustawionej godzinie, a jeśli brak cen, od razu po publikacji`

Trzeci tryb jest domyślny. Jeżeli o ustawionej godzinie ceny na jutro nie są jeszcze dostępne, integracja czeka i wysyła wiadomość po wykryciu publikacji.

### Wybór paliw

Możesz zdecydować, które paliwa mają znaleźć się w wiadomości. Domyślnie zaznaczone są PB95, PB98 i ON.

### Własny tytuł i treść

Możesz pozostawić domyślny format albo podać własne szablony Home Assistant.

Dostępne zmienne:

```text
today_date
tomorrow_date
published
pb95
pb98
on
```

Dla każdego paliwa, na przykład `pb95`, dostępne są:

```text
pb95.today
pb95.tomorrow
pb95.today_text
pb95.tomorrow_text
pb95.change
pb95.difference_grosz
```

Przykład własnej treści:

```jinja2
PB95: {{ pb95.today_text }} -> {{ pb95.tomorrow_text }}
Zmiana: {{ pb95.change }}
```

Jeżeli szablon jest błędny, integracja zapisze błąd w logu i użyje treści domyślnej.

### Filtr zmian

Możesz włączyć opcję wysyłki tylko wtedy, gdy przynajmniej jedno z wybranych paliw zmieni cenę.

Możesz też ustawić minimalną zmianę w groszach. Przykład: `5gr` oznacza, że automatyczna wiadomość zostanie wysłana tylko wtedy, gdy co najmniej jedno wybrane paliwo zmieni cenę o minimum 5gr.

### Telefony

Telefony są wybierane z akcji `notify.mobile_app_*` udostępnianych przez Home Assistant Companion.

Każdy telefon ma osobne podmenu. Możesz:

- nadać własną nazwę
- włączyć lub wyłączyć automatyczne powiadomienia
- wybrać `Wyślij test`
- wybrać `Wyślij powiadomienie teraz`

Ręczne wysłanie na pojedynczy telefon działa niezależnie od przełącznika automatycznych powiadomień.

### Przykład domyślnego powiadomienia

```text
Ceny paliw na jutro, 07.10.2026

PB95: dziś 6,79 zł/l, jutro 6,86 zł/l, drożej o 7gr
PB98: dziś 7,54 zł/l, jutro 7,49 zł/l, taniej o 5gr
ON: dziś 7,82 zł/l, jutro 7,82 zł/l, bez zmian
```

## Diagnostyka

W menu `Diagnostyka i akcje` zobaczysz:

- stan publikacji na jutro
- czas ostatniego pobrania
- liczbę znalezionych publikacji
- liczbę zapisanych dni historii
- ostatni błąd
- niedostępne cele powiadomień

Z tego menu można również ręcznie sprawdzić ceny oraz wysłać wiadomość do wszystkich włączonych telefonów.

Home Assistant udostępnia także standardowe pobieranie diagnostyki integracji.

## Dashboard

Gotowy przykład karty znajduje się w:

```text
examples/lovelace-card.yaml
```

Identyfikatory encji mogą różnić się, jeżeli Home Assistant musiał dodać sufiks z powodu istniejącej encji o tej samej nazwie.

## Źródło danych

Oficjalna strona Ministerstwa Energii:

```text
https://www.gov.pl/web/energia/wiadomosci
```

Integracja obsługuje publikacje dla pojedynczego dnia oraz publikacje obejmujące kilka dni, na przykład weekend lub okres świąteczny.

## Instalacja przez HACS

1. Otwórz HACS.
2. Wejdź w Integracje.
3. Dodaj niestandardowe repozytorium:

```text
https://github.com/Q-Tronic/HomeAssistant-Ceny-Paliw-GOV
```

4. Typ repozytorium: `Integration`.
5. Zainstaluj `Ceny paliw GOV.PL`.
6. Uruchom ponownie Home Assistant.
7. Wejdź w `Ustawienia > Urządzenia i usługi > Dodaj integrację`.
8. Wyszukaj `Ceny paliw GOV.PL` i dodaj integrację.

## Aktualizacja przez HACS

Po opublikowaniu nowego GitHub Release HACS powinien wykryć nową wersję. Aby wymusić sprawdzenie:

1. Otwórz HACS i znajdź `Ceny paliw GOV.PL`.
2. Otwórz menu z trzema kropkami.
3. Wybierz `Update information`.
4. Jeżeli aktualizacja nie pojawi się od razu, wybierz `Redownload` i wskaż najnowszą wersję.
5. Po pobraniu uruchom ponownie Home Assistant.

## Instalacja ręczna

Skopiuj katalog:

```text
custom_components/ceny_paliw_gov_pl
```

do katalogu:

```text
/config/custom_components/ceny_paliw_gov_pl
```

Następnie uruchom ponownie Home Assistant i dodaj integrację z poziomu interfejsu.

## Autor

Q-Tronic

## Licencja

MIT
