# Ceny paliw GOV.PL

Niestandardowa integracja Home Assistant autorstwa **Q-Tronic**. Pobiera maksymalne detaliczne ceny paliw publikowane przez Ministerstwo Energii na gov.pl.

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

Ceny są sprawdzane co 30 minut.

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

## Źródło danych

Oficjalna strona Ministerstwa Energii:

https://www.gov.pl/web/energia/wiadomosci

Integracja obsługuje zarówno publikacje dla pojedynczego dnia, jak i publikacje obejmujące kilka dni, na przykład weekend lub okres świąteczny.

## Instalacja przez HACS

1. Otwórz HACS.
2. Wejdź w Integracje.
3. Dodaj niestandardowe repozytorium:

```text
https://github.com/Q-Tronic/homeassistant-ceny-paliw-gov
```

4. Typ repozytorium: Integracja.
5. Zainstaluj `Ceny paliw GOV.PL`.
6. Uruchom ponownie Home Assistant.
7. Wejdź w Ustawienia, Urządzenia i usługi, Dodaj integrację.
8. Wyszukaj `Ceny paliw GOV.PL` i dodaj integrację.

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

## Przykład

Dla cen:

```text
PB95 dzisiaj: 6,79 zł/l
PB95 jutro: 6,86 zł/l
```

encja `sensor.pb95_zmiana_ceny` zwróci:

```text
drożej o 7gr
```

oraz atrybuty:

```yaml
cena_dzis: 6.79
cena_jutro: 6.86
roznica_zl: 0.07
roznica_gr: 7
kierunek: drozej
```

## Autor

Q-Tronic

## Licencja

MIT
