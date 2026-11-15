# Maksymalne Ceny Paliw GOV.PL

<p align="center">
  <img src="custom_components/ceny_paliw_gov_pl/brand/icon@2x.png" width="128" height="128" alt="Maksymalne Ceny Paliw GOV.PL">
</p>

Niestandardowa integracja Home Assistant autorstwa **Q-Tronic**. Pobiera maksymalne detaliczne ceny paliw publikowane przez Ministerstwo Energii na gov.pl, tworzy encje dla cen dzisiejszych i jutrzejszych, prowadzi lokalną historię oraz wysyła konfigurowalne powiadomienia na telefony z aplikacją Home Assistant Companion.

Aktualna wersja: **v1.6.6**.

## Spis treści

- [Najważniejsze funkcje](#najważniejsze-funkcje)
- [Poprawki w v1.6.6](#poprawki-w-v166)
- [Poprawki w v1.6.5](#poprawki-w-v165)
- [Poprawki w v1.6.4](#poprawki-w-v164)
- [Tryby i bezpieczeństwo powiadomień](#tryby-i-bezpieczeństwo-powiadomień)
- [Bezpieczna diagnostyka](#bezpieczna-diagnostyka)
- [Dodatkowe encje i zabezpieczenia](#dodatkowe-encje-i-zabezpieczenia)
- [Ustawienia telefonu dostępne na dashboardzie](#ustawienia-telefonu-dostępne-na-dashboardzie)
- [Indywidualny tryb, godzina i oczekiwanie na publikację](#indywidualny-tryb-godzina-i-oczekiwanie-na-publikację)
- [Encje diagnostyczne](#encje-diagnostyczne)
- [Status publikacji](#status-publikacji)
- [Powiadomienia](#powiadomienia)
- [Filtr zmian](#filtr-zmian)
- [Historia cen](#historia-cen)
- [Gotowe przykłady dashboardu](#gotowe-przykłady-dashboardu)
- [Zdarzenie aktualizacji](#zdarzenie-aktualizacji)
- [Repairs](#repairs)
- [Źródło danych](#źródło-danych)
- [Wymagania](#wymagania)
- [Rozwiązywanie problemów](#rozwiązywanie-problemów)
- [Instalacja przez Katalog społeczności (Marketplace)](#instalacja-przez-katalog-społeczności-marketplace)
- [Aktualizacja przez Katalog społeczności](#aktualizacja-przez-katalog-społeczności)
- [Instalacja przez HACS w starszych wersjach HA](#instalacja-przez-hacs-w-starszych-wersjach-ha)
- [Instalacja ręczna](#instalacja-ręczna)
- [Autor](#autor)
- [Licencja](#licencja)

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

Jeżeli cena na jutro nie została jeszcze opublikowana, numeryczny sensor ceny
ma stan `unknown` (bez wartości), zamiast zwracać tekst i powodować błąd
Home Assistanta. Informacja o publikacji pozostaje w atrybucie `status_danych`
(`nie_opublikowano` albo `opublikowano`). Tak samo zachowują się średnie cen,
gdy nie ma jeszcze historii. Tekst `Nie opublikowano` nadal może pojawiać się
w encjach tekstowych zmiany ceny i w powiadomieniach.

Encja zmiany ceny pokazuje na przykład:

```text
drożej o 7gr
taniej o 2gr
bez zmian
Nie opublikowano
```

Ikony encji zmiany ceny reagują na trend. Wzrost pokazuje ikonę wzrostu, spadek ikonę spadku, brak zmiany ikonę neutralną, a brak publikacji ikonę informacyjną.

## Poprawki w v1.6.6

Integracja sprawdza dostępność skonfigurowanych usług `notify.mobile_app_*`
dopiero po zakończeniu startu Home Assistanta. Zapobiega to ostrzeżeniom
Naprawy wywołanym wyłącznie kolejnością rejestracji usług podczas restartu.
Jeśli usługa pojawi się później, ostrzeżenie jest usuwane od razu po
zarejestrowaniu jej w HA. Gdy integracja zostanie przeładowana w już
uruchomionym Home Assistancie, kontrola odbywa się od razu.
Nie zmienia to ustawień telefonów, sposobów wysyłania wiadomości ani
identyfikatorów encji.

## Poprawki w v1.6.5

Po lokalnej północy (00:00:01) encje natychmiast przechodzą na nową datę
obowiązywania. Odpowiednie ceny są wybierane z już pobranych publikacji,
również z zakresów weekendowych i świątecznych. Ceny, których zakres nie
obejmuje nowego dnia, nie są używane ponownie. Następnie integracja od razu
podejmuje próbę odświeżenia GOV.PL; źródłowy czas pobrania nie jest fałszowany.

Istniejące identyfikatory encji oraz ich typy nie ulegają zmianie. Brak ceny
na jutro w sensorze numerycznym oznacza `unknown`, natomiast w opcjonalnym
przykładzie dashboardu jest wyświetlany jako **„—”** z dopiskiem
„Nie opublikowano”. Nie jest to nowy stan sensora — automatyzacje powinny
nadal obsługiwać `unknown` / `unavailable`.

## Poprawki w v1.6.4

Poprawiono błąd `ValueError` przy tworzeniu sensorów cen PB95, PB98 i ON,
gdy brak danych na jutro. Numeryczne sensory cen i średnich historycznych
zwracają teraz `unknown` zamiast tekstu, kiedy nie mają wartości liczbowej.
Status braku publikacji można nadal odczytać z atrybutów; tekstowe sensory
zmiany ceny zachowują dotychczasowe komunikaty. Nie zmieniono identyfikatorów
encji, ustawień telefonów ani działania powiadomień.

## Tryby i bezpieczeństwo powiadomień

### Tryb wysyłki osobno dla każdego telefonu

Każdy skonfigurowany telefon otrzymuje dodatkową encję `select`, która pozwala użytkownikowi wybrać sposób automatycznej wysyłki:

```text
O ustalonej godzinie
Po publikacji
Po publikacji tylko gdy cena się zmieni
```

`O ustalonej godzinie` działa tak jak wcześniejsze wersje integracji. Telefon czeka do swojej godziny. Jeśli ceny na jutro nie są jeszcze opublikowane, integracja czeka i wysyła wiadomość po wykryciu publikacji.

`Po publikacji` ignoruje godzinę i wysyła wiadomość od razu po wykryciu nowej publikacji GOV.PL.

`Po publikacji tylko gdy cena się zmieni` również reaguje od razu na nową publikację, ale wiadomość jest wysyłana tylko wtedy, gdy co najmniej jedno paliwo wybrane dla telefonu zmieni cenę. Używany jest ten sam minimalny próg zmiany ceny, który można ustawić w filtrach powiadomień.

Istniejące telefony po aktualizacji zachowują tryb `O ustalonej godzinie`. Nowo dodawane telefony również domyślnie używają tego trybu.

### Publikacje weekendowe

W trybach publikacyjnych jedna publikacja obejmująca kilka dni jest traktowana jako jedna publikacja. Przykładowo publikacja obejmująca sobotę, niedzielę i poniedziałek powoduje jedną automatyczną wiadomość po jej wykryciu, a nie kolejną wiadomość każdego dnia.

Tryb `O ustalonej godzinie` zachowuje dotychczasowe działanie dzienne.

### Ochrona przed duplikatami

Integracja zapisuje osobno identyfikator dziennej wysyłki oraz identyfikator publikacji źródłowej. Dzięki temu restart Home Assistanta nie powoduje ponownego wysłania tej samej publikacji w trybach publikacyjnych.

### Tryb skupienia telefonu

Integracja przekazuje powiadomienie do Home Assistant Companion w chwili wynikającej z wybranego trybu. To, czy telefon pokaże je natychmiast przy aktywnym trybie skupienia, zależy od ustawień Androida lub iOS. Integracja nie wymusza powiadomień krytycznych.

## Bezpieczna diagnostyka

### Prywatniejsza diagnostyka

Dane diagnostyczne nie zawierają już własnych nazw telefonów ani identyfikatorów usług `notify.mobile_app_*`. Te wartości są maskowane przed wygenerowaniem pliku diagnostycznego.

Lista brakujących celów powiadomień została zastąpiona liczbą brakujących urządzeń, dzięki czemu diagnostyka nadal pomaga w szukaniu problemów bez ujawniania identyfikatorów telefonów.

## Dodatkowe encje i zabezpieczenia

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

## Ustawienia telefonu dostępne na dashboardzie

Administrator najpierw dodaje telefon w konfiguracji integracji. Dla każdego telefonu tworzone są encje:

```text
switch.<nazwa_telefonu>_powiadomienia
select.<nazwa_telefonu>_tryb_wysylki_powiadomien
time.<nazwa_telefonu>_godzina_powiadomienia
select.<nazwa_telefonu>_paliwa_w_powiadomieniu
button.<nazwa_telefonu>_wyslij_powiadomienie_teraz
sensor.<nazwa_telefonu>_status_ostatniego_powiadomienia
sensor.<nazwa_telefonu>_ostatnie_powiadomienie
```

Dokładny `entity_id` zależy od nazwy telefonu i istniejących encji w danej instalacji Home Assistant.

`switch` pozwala użytkownikowi włączyć albo wyłączyć automatyczne powiadomienia dla swojego telefonu.

`select` trybu wysyłki pozwala wybrać wysyłkę godzinową, natychmiast po publikacji albo po publikacji tylko przy zmianie ceny.

`time` ustawia indywidualną godzinę używaną przez tryb `O ustalonej godzinie`. W trybach publikacyjnych ta godzina jest ignorowana.

`select` paliw pozwala wybrać:

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

Zmiany `switch`, `time` i obu encji `select` są zapisywane bez konieczności ponownego uruchamiania Home Assistanta.

## Indywidualny tryb, godzina i oczekiwanie na publikację

Każdy telefon ma własny tryb wysyłki.

W trybie `O ustalonej godzinie`, jeśli ceny na jutro są już opublikowane o wybranej godzinie, wiadomość zostanie wysłana od razu. Jeśli publikacji jeszcze nie ma, telefon otrzymuje status `Oczekuje na publikację` i wiadomość zostanie wysłana po jej wykryciu.

W trybie `Po publikacji` wiadomość jest wysyłana po wykryciu nowej publikacji bez czekania na ustawioną godzinę.

W trybie `Po publikacji tylko gdy cena się zmieni` integracja dodatkowo sprawdza wybrane dla telefonu paliwa i minimalny próg zmiany. Jeśli warunek nie jest spełniony, publikacja jest oznaczana jako obsłużona i nie jest sprawdzana ponownie przy każdym odświeżeniu.

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
- ustawić tryb wysyłki
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

Globalny filtr zmian może ograniczać wiadomości w trybie `O ustalonej godzinie` oraz w zwykłym trybie `Po publikacji`.

Tryb `Po publikacji tylko gdy cena się zmieni` zawsze wymaga zmiany co najmniej jednego paliwa wybranego dla danego telefonu.

Można ustawić minimalną zmianę w groszach. Przykład: `5gr` oznacza, że warunek jest spełniony, gdy co najmniej jedno wybrane paliwo zmieni cenę o minimum 5gr.

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
examples/dashboard-unpublished-dash.yaml
examples/lovelace-card.yaml
```

`dashboard-phone.yaml` zawiera konfigurację jednego telefonu, w tym tryb wysyłki, godzinę, paliwa, przycisk wysyłki, status i czas ostatniego powiadomienia.

`dashboard-complete.yaml` jest przykładem kompletnego widoku zawierającego ceny, historię, sterowanie telefonem i akcje.

`dashboard-colored.yaml` pokazuje wbudowane karty Home Assistant, które zmieniają kolor zależnie od trendu:

```text
czerwony: drożej
zielony: taniej
szary: bez zmian
bursztynowy: brak publikacji
```

`dashboard-unpublished-dash.yaml` zawiera opcjonalną kartę Markdown
wyświetlającą `—` dla nieopublikowanych cen na jutro. Podmień w niej
identyfikatory encji na używane w swojej instalacji, jeśli są inne.
Nie zmienia ona encji ani innych kart użytkownika.

Przykłady używają wyłącznie wbudowanych kart Home Assistant. Nie wymagają instalowania żadnej dodatkowej karty z Katalogu społeczności (dawniej HACS).

Po wklejeniu YAML podmień przykładowe identyfikatory telefonu na encje istniejące w Twoim Home Assistant.

### Szybki przykład karty użytkownika

```yaml
type: entities
title: Powiadomienia paliwowe
entities:
  - entity: switch.telefon_uzytkownika_powiadomienia
    name: Powiadomienia
  - entity: select.telefon_uzytkownika_tryb_wysylki_powiadomien
    name: Tryb wysyłki
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
- po zakończeniu uruchamiania HA skonfigurowany i włączony telefon nie ma dostępnej usługi `notify.mobile_app_*`. Ostrzeżenie znika po zarejestrowaniu usługi

## Obsługa publikacji weekendowych

Parser obsługuje publikacje dla pojedynczego dnia oraz zakresy kilku dni, w tym warianty tytułów zawierające `w okresie` oraz `w dniach`.

## Źródło danych

Oficjalna strona Ministerstwa Energii:

```text
https://www.gov.pl/web/energia/wiadomosci
```

## Wymagania

- Home Assistant Core `2025.8.0` lub nowszy. Minimalna wersja nie została podniesiona.
- Home Assistant `2026.11` lub nowszy: wbudowany **Katalog społeczności (Marketplace)** w Ustawieniach. Nie instaluj osobno HACS.
- Home Assistant `2026.10` lub starszy (ale nie starszy niż `2025.8.0`): dotychczasowa instalacja przez HACS lub ręczna.
- aplikacja Home Assistant Companion na telefonie, jeśli mają być używane powiadomienia mobilne
- dostęp Home Assistanta do strony gov.pl

## Rozwiązywanie problemów

Jeżeli integracja nie pojawia się na liście albo przy dodawaniu pokazuje `Invalid handler specified`, najpierw sprawdź wersję Home Assistant w `Ustawienia > Informacje`. Wersje starsze niż `2025.8.0` nie są wspierane.

Po aktualizacji integracji uruchom ponownie Home Assistant. Jeżeli problem nadal występuje, otwórz `Ustawienia > System > Dzienniki` i wyszukaj wpis zawierający `ceny_paliw_gov_pl`, `config_flow`, `ImportError`, `ModuleNotFoundError` albo `Traceback`. Taki fragment logu najlepiej dołączyć do zgłoszenia na GitHubie.

Jeżeli po aktualizacji interfejs nadal pokazuje stare tłumaczenia lub formularze, wykonaj twarde odświeżenie przeglądarki albo zamknij i ponownie otwórz aplikację Home Assistant.

Od Home Assistant `2026.3` ikona integracji jest dostarczana lokalnie z katalogu `custom_components/ceny_paliw_gov_pl/brand/`. Jeśli ikona w Katalogu społeczności nie jest widoczna, nie oznacza to automatycznie braku ikony w widoku integracji. Przy zgłoszeniu sprawdź wersję HA i podaj zrzut problematycznego widoku.

### Przejście z HACS do Katalogu społeczności

Od Home Assistant `2026.11` HACS został zastąpiony przez wbudowany **Marketplace** (w polskim interfejsie Katalog społeczności). Home Assistant migruje zainstalowane repozytoria, ich aktualizacje i niestandardowe źródła automatycznie. Nie trzeba usuwać ani ponownie instalować naszej integracji. Po migracji nie instaluj ponownie HACS.

`hacs.json` w repozytorium oraz techniczna walidacja `hacs/action` pozostają celowo: są nadal wymagane lub obsługiwane przez Marketplace. Nazwy tych plików i identyfikatorów nie zmieniły się.

## Instalacja przez Katalog społeczności (Marketplace)

Instrukcja dla **Home Assistant `2026.11` i nowszych**:

1. Otwórz **Ustawienia > Katalog społeczności** (Marketplace). Jest on wbudowany w Home Assistant.
2. Przy pierwszym użyciu przeczytaj ostrzeżenie dotyczące dodatków społeczności i zaakceptuj warunki, jeśli się z nimi zgadzasz.
3. W prawym górnym rogu wybierz **Dodaj z linku** (`Add from link`).
4. W polu łącza GitHub wklej:

   ```text
   https://github.com/Q-Tronic/HomeAssistant-Ceny-Paliw-GOV
   ```

5. Jeżeli system o to poprosi, połącz konto GitHub. Jest to potrzebne przy dodawaniu niestandardowego repozytorium.
6. Zainstaluj **Maksymalne Ceny Paliw GOV.PL**. Jeśli Home Assistant poprosi o restart, wykonaj go.
7. Przejdź do **Ustawienia > Urządzenia i usługi > Dodaj integrację**. Wyszukaj **Maksymalne Ceny Paliw GOV.PL** i skonfiguruj integrację.

## Aktualizacja przez Katalog społeczności

Po opublikowaniu nowego wydania GitHub Release Katalog społeczności wykrywa dostępną wersję. Informacje o aktualizacjach pojawiają się również w **Ustawienia > Aktualizacje**. Zainstaluj dostępną aktualizację i uruchom ponownie Home Assistant, gdy pojawi się taka prośba w sekcji Naprawy. Ustawienia telefonów, encje i dane historyczne pozostają zachowane.

## Instalacja przez HACS w starszych wersjach HA

Dla Home Assistant **`2025.8.0` do `2026.10.x`**:

1. Otwórz HACS (jeżeli jest już zainstalowany).
2. Wybierz kategorię **Integracje** i dodaj niestandardowe repozytorium `https://github.com/Q-Tronic/HomeAssistant-Ceny-Paliw-GOV` jako `Integration`.
3. Zainstaluj **Maksymalne Ceny Paliw GOV.PL**.
4. Uruchom ponownie Home Assistant i dodaj integrację w **Ustawienia > Urządzenia i usługi**.

HACS w tych starszych wersjach służy również do aktualizacji. W menu repozytorium możesz wybrać `Update information`, aby odświeżyć informacje. Następnie zainstaluj aktualizację i wykonaj restart.

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
