# Maksymalne Ceny Paliw GOV.PL v1.6.0

Nowa wersja rozbudowuje indywidualne ustawienia powiadomień dla każdego telefonu.

## Nowości

- osobny tryb wysyłki dla każdego telefonu
- `O ustalonej godzinie` zachowuje dotychczasowe działanie
- `Po publikacji` wysyła wiadomość od razu po wykryciu nowej publikacji GOV.PL
- `Po publikacji tylko gdy cena się zmieni` wysyła tylko przy zmianie wybranego paliwa
- tryb publikacyjny ze zmianą korzysta z ustawionego minimalnego progu zmiany ceny
- nowa encja `select` trybu wysyłki dostępna na dashboardzie
- istniejące telefony zachowują tryb godzinowy po aktualizacji
- nowe telefony również domyślnie używają trybu godzinowego
- jedna publikacja weekendowa powoduje jedną wiadomość w trybach publikacyjnych
- rozszerzona trwała ochrona przed duplikatami po restarcie Home Assistanta
- zaktualizowana diagnostyka, README i przykłady dashboardu

Bez zmian w źródle danych. Integracja nadal pobiera dane z oficjalnych publikacji Ministerstwa Energii na gov.pl.
