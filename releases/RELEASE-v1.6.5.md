# Maksymalne Ceny Paliw GOV.PL v1.6.5

Poprawka automatycznej zmiany dnia i prezentacji nieopublikowanych cen.

- Dodano automatyczne przełączenie cen dzisiaj/jutro tuż po lokalnej północy bez restartowania Home Assistanta.
- Zachowano ważne już pobrane ceny przy zmianie daty, również dla zakresów kilkudniowych.
- Po północy integracja wykonuje dodatkową próbę odświeżenia GOV.PL.
- Zachowano dostępność cen o potwierdzonych datach obowiązywania podczas krótkotrwałych błędów pobierania.
- Zapobiegnięto pokazywaniu wczorajszej ceny jako dzisiejszej poza okresem obowiązywania.
- Dodano opcjonalną kartę prezentującą brak ceny jako „—”, bez zmiany numerycznych sensorów.
- Zachowano identyfikatory encji, konfigurację powiadomień i pliki ikon.
