# Ceny paliw GOV.PL

Niestandardowa integracja Home Assistant autorstwa **Q-Tronic**. Pobiera maksymalne detaliczne ceny paliw publikowane przez Ministerstwo Energii na gov.pl i może wysyłać codzienne powiadomienia na telefony z aplikacją Home Assistant Companion.

## Funkcje

Integracja tworzy 9 encji:

- `sensor.cena_pb95_dzisiaj`
- `sensor.cena_pb95_jutro`
- `sensor.pb95_zmiana_ceny`
- `sensor.cena_pb98_dzisiaj`
- `sensor.cena_pb98_jutro`
- `sensor.pb98_zmiana_ceny`
- `sensor.cena_on_dzisiaj`
- `sensor.cena_on_jutro`
- `sensor.on_zmiana_ceny`

Ceny są sprawdzane automatycznie co 30 minut.

Jeżeli cena na jutro nie została jeszcze opublikowana, encja pozostaje dostępna i pokazuje:

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

Dodatkowe atrybuty zawierają między innymi cenę liczbową, różnicę w groszach, różnicę w złotych, daty obowiązywania, datę publikacji, czas ostatniego pobrania oraz adres źródła.

## Powiadomienia na telefon

Od wersji `1.1.0` integracja ma własną konfigurację powiadomień.

Po dodaniu integracji otwórz:

```text
Ustawienia > Urządzenia i usługi > Ceny paliw GOV.PL > Konfiguruj
```

Możesz ustawić:

- globalne włączenie lub wyłączenie powiadomień,
- godzinę wysyłki,
- tryb wysyłki,
- jeden lub kilka telefonów,
- własną nazwę każdego telefonu,
- osobne włączenie lub wyłączenie każdego telefonu bez usuwania go z listy,
- test powiadomienia osobno dla każdego telefonu.

Telefony są pobierane z usług Home Assistant Companion o nazwach `notify.mobile_app_*`.

### Tryby wysyłki

Dostępne są trzy tryby:

1. `O ustawionej godzinie`

   Integracja wysyła wiadomość o ustawionej godzinie. Jeżeli cen na jutro jeszcze nie ma, wysyła informację o braku publikacji.

2. `Natychmiast po publikacji nowych cen`

   Integracja wysyła wiadomość po wykryciu opublikowanych cen na jutro.

3. `O ustawionej godzinie, a jeśli brak cen, od razu po publikacji`

   Jest to tryb domyślny. O ustawionej godzinie integracja sprawdza ceny. Jeżeli ceny na jutro są dostępne, wysyła powiadomienie. Jeżeli jeszcze ich nie ma, nie wysyła komunikatu o braku danych. Czeka na publikację i wysyła właściwe powiadomienie po jej wykryciu.

Jeżeli wysyłka do jednego z kilku telefonów się nie powiedzie, integracja zapamiętuje telefony, które już otrzymały wiadomość i w domyślnym trybie ponawia próbę tylko dla brakujących urządzeń przy kolejnych aktualizacjach danych.

### Przykład powiadomienia

```text
Ceny paliw na jutro, 07.10.2026

PB95: dziś 6,79 zł/l, jutro 6,86 zł/l, drożej o 7gr
PB98: dziś 7,54 zł/l, jutro 7,49 zł/l, taniej o 5gr
ON: dziś 7,82 zł/l, jutro 7,82 zł/l, bez zmian
```

Każde powiadomienie, również testowe, jest wysyłane z danymi:

```yaml
data:
  ttl: 0
  priority: high
```

Na Androidzie ustawienia te wymuszają wysoką priorytetyzację dostarczenia przez Home Assistant Companion.

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

Po opublikowaniu nowego GitHub Release HACS powinien wykryć nową wersję automatycznie. Aby wymusić sprawdzenie od razu:

1. Otwórz HACS i znajdź `Ceny paliw GOV.PL`.
2. Otwórz menu z trzema kropkami.
3. Wybierz `Update information`.
4. Ponownie otwórz menu z trzema kropkami i wybierz `Redownload`.
5. Wybierz najnowszą wersję, jeśli HACS pokaże wybór wersji.
6. Po pobraniu uruchom ponownie Home Assistant.

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
