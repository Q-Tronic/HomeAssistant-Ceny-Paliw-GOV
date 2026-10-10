"""Constants for the Maksymalne Ceny Paliw GOV.PL integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "ceny_paliw_gov_pl"
NAME = "Maksymalne Ceny Paliw GOV.PL"
VERSION = "1.6.1"
AUTHOR = "Q-Tronic"

NEWS_URL = "https://www.gov.pl/web/energia/wiadomosci"
REPOSITORY_URL = "https://github.com/Q-Tronic/HomeAssistant-Ceny-Paliw-GOV"
ISSUE_TRACKER_URL = f"{REPOSITORY_URL}/issues"

DEFAULT_UPDATE_INTERVAL_MINUTES = 30
UPDATE_INTERVAL_MINUTES_OPTIONS = (5, 10, 15, 30, 60)
STALE_DATA_AFTER = timedelta(minutes=75)
REQUEST_TIMEOUT_SECONDS = 20
USER_AGENT = f"HomeAssistant-{DOMAIN}/{VERSION} (+{REPOSITORY_URL})"

FUEL_PB95 = "pb95"
FUEL_PB98 = "pb98"
FUEL_ON = "on"
FUELS = (FUEL_PB95, FUEL_PB98, FUEL_ON)

FUEL_NAMES: dict[str, str] = {
    FUEL_PB95: "PB95",
    FUEL_PB98: "PB98",
    FUEL_ON: "ON",
}

FUEL_SELECTION_OPTIONS: dict[str, tuple[str, ...]] = {
    "PB95": (FUEL_PB95,),
    "PB98": (FUEL_PB98,),
    "ON": (FUEL_ON,),
    "PB95 + PB98": (FUEL_PB95, FUEL_PB98),
    "PB95 + ON": (FUEL_PB95, FUEL_ON),
    "PB98 + ON": (FUEL_PB98, FUEL_ON),
    "PB95 + PB98 + ON": (FUEL_PB95, FUEL_PB98, FUEL_ON),
}

STATUS_NOT_PUBLISHED = "Nie opublikowano"
STATUS_NO_CHANGE = "bez zmian"
STATUS_PUBLISHED = "Opublikowano"
STATUS_WAITING = "Oczekiwanie na publikację"
STATUS_DOWNLOAD_ERROR = "Błąd pobierania"
STATUS_STALE = "Dane nieaktualne"
STATUS_NO_HISTORY = "Brak historii"
UNIT_PRICE = "zł/l"
UNIT_GROSZ = "gr"

EVENT_PRICES_UPDATED = f"{DOMAIN}_updated"

SIGNAL_NOTIFICATION_STATE_UPDATED = f"{DOMAIN}_notification_state_updated"

PHONE_STATUS_NONE = "Brak wysyłki"
PHONE_STATUS_WAITING = "Oczekuje na publikację"
PHONE_STATUS_SENT = "Wysłano"
PHONE_STATUS_ERROR = "Błąd"
PHONE_STATUS_FILTERED = "Pominięto filtrem"

CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"
CONF_NOTIFICATION_DEVICES = "notification_devices"
CONF_NOTIFICATION_SERVICES = "notification_services"
CONF_SELECTED_DEVICE = "selected_device"
CONF_DEVICE_NAME = "device_name"
CONF_DEVICE_ENABLED = "device_enabled"
CONF_DEVICE_NOTIFICATION_TIME = "device_notification_time"
CONF_DEVICE_NOTIFICATION_FUELS = "device_notification_fuels"
CONF_DEVICE_NOTIFICATION_MODE = "device_notification_mode"
CONF_NOTIFICATION_ONLY_ON_CHANGE = "notification_only_on_change"
CONF_NOTIFICATION_MIN_CHANGE_GROSZ = "notification_min_change_grosz"
CONF_NOTIFICATION_CUSTOM_TITLE = "notification_custom_title"
CONF_NOTIFICATION_CUSTOM_MESSAGE = "notification_custom_message"

# Klucze pozostawione dla zgodności z konfiguracją wersji 1.3.x.
CONF_NOTIFICATIONS_ENABLED = "notifications_enabled"
CONF_NOTIFICATION_TIME = "notification_time"
CONF_NOTIFICATION_MODE = "notification_mode"
CONF_NOTIFICATION_FUELS = "notification_fuels"

DEVICE_SERVICE = "service"
DEVICE_NAME = "name"
DEVICE_ENABLED = "enabled"
DEVICE_NOTIFICATION_TIME = "notification_time"
DEVICE_FUELS = "fuels"
DEVICE_NOTIFICATION_MODE = "notification_mode"

DEFAULT_NOTIFICATION_TIME = "18:00:00"
DEFAULT_NOTIFICATION_FUELS = list(FUELS)
DEFAULT_NOTIFICATION_ONLY_ON_CHANGE = False
DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ = 0
DEFAULT_NOTIFICATION_CUSTOM_TITLE = ""
DEFAULT_NOTIFICATION_CUSTOM_MESSAGE = ""
DEFAULT_NOTIFICATIONS_ENABLED = True

PHONE_NOTIFICATION_MODE_SCHEDULED = "scheduled"
PHONE_NOTIFICATION_MODE_PUBLICATION = "publication"
PHONE_NOTIFICATION_MODE_PUBLICATION_CHANGE = "publication_change"
PHONE_NOTIFICATION_MODES = (
    PHONE_NOTIFICATION_MODE_SCHEDULED,
    PHONE_NOTIFICATION_MODE_PUBLICATION,
    PHONE_NOTIFICATION_MODE_PUBLICATION_CHANGE,
)
PHONE_NOTIFICATION_MODE_NAMES: dict[str, str] = {
    PHONE_NOTIFICATION_MODE_SCHEDULED: "O ustalonej godzinie",
    PHONE_NOTIFICATION_MODE_PUBLICATION: "Po publikacji",
    PHONE_NOTIFICATION_MODE_PUBLICATION_CHANGE: "Po publikacji tylko gdy cena się zmieni",
}
DEFAULT_PHONE_NOTIFICATION_MODE = PHONE_NOTIFICATION_MODE_SCHEDULED

# Zachowane wyłącznie dla migracji starszych ustawień.
NOTIFICATION_MODE_SCHEDULED = "scheduled"
NOTIFICATION_MODE_ON_PUBLICATION = "on_publication"
NOTIFICATION_MODE_SCHEDULED_THEN_PUBLICATION = "scheduled_then_publication"
DEFAULT_NOTIFICATION_MODE = NOTIFICATION_MODE_SCHEDULED_THEN_PUBLICATION

NOTIFICATION_TITLE = "Maksymalne Ceny Paliw GOV.PL"
NOTIFICATION_TEST_TITLE = "Test powiadomienia"
NOTIFICATION_DATA = {
    "ttl": 0,
    "priority": "high",
}

NOTIFICATION_STORAGE_VERSION = 1
NOTIFICATION_STORAGE_KEY_PREFIX = f"{DOMAIN}.notification_state"
HISTORY_STORAGE_VERSION = 1
HISTORY_STORAGE_KEY_PREFIX = f"{DOMAIN}.history"
HISTORY_RETENTION_DAYS = 120
HISTORY_PERIODS = (7, 30, 90)
