# Maksymalne Ceny Paliw GOV.PL v1.6.6

Poprawiono wykrywanie niedostępnych telefonów podczas uruchamiania Home Assistanta.

- Ostrzeżenia Repairs o niedostępnych telefonach są weryfikowane dopiero po zakończeniu startu HA.
- Ponownie sprawdzana jest dostępność usług powiadomień po zdarzeniu uruchomienia Home Assistanta.
- Ostrzeżenia znikają niezwłocznie po późniejszej rejestracji usługi `notify.mobile_app_*`.
- Podczas przeładowania integracji w działającym HA kontrola dostępności telefonów wykonywana jest od razu.
- Nasłuchy zdarzeń powiadomień są usuwane przy wyładowaniu integracji.
