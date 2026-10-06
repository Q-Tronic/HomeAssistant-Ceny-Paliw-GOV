"""Constants for the Ceny paliw GOV.PL integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "ceny_paliw_gov_pl"
NAME = "Ceny paliw GOV.PL"
VERSION = "1.1.0"
AUTHOR = "Q-Tronic"

NEWS_URL = "https://www.gov.pl/web/energia/wiadomosci"
REPOSITORY_URL = "https://github.com/Q-Tronic/HomeAssistant-Ceny-Paliw-GOV"
ISSUE_TRACKER_URL = f"{REPOSITORY_URL}/issues"

UPDATE_INTERVAL = timedelta(minutes=30)
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

STATUS_NOT_PUBLISHED = "Nie opublikowano"
STATUS_NO_CHANGE = "bez zmian"
UNIT_PRICE = "zł/l"

CONF_NOTIFICATIONS_ENABLED = "notifications_enabled"
CONF_NOTIFICATION_TIME = "notification_time"
CONF_NOTIFICATION_MODE = "notification_mode"
CONF_NOTIFICATION_SERVICES = "notification_services"
CONF_NOTIFICATION_DEVICES = "notification_devices"
CONF_DEVICE_NAME = "device_name"
CONF_DEVICE_ENABLED = "device_enabled"
CONF_TEST_NOTIFICATION = "test_notification"

DEVICE_SERVICE = "service"
DEVICE_NAME = "name"
DEVICE_ENABLED = "enabled"

NOTIFICATION_MODE_SCHEDULED = "scheduled"
NOTIFICATION_MODE_ON_PUBLICATION = "on_publication"
NOTIFICATION_MODE_SCHEDULED_THEN_PUBLICATION = "scheduled_then_publication"
NOTIFICATION_MODES = (
    NOTIFICATION_MODE_SCHEDULED,
    NOTIFICATION_MODE_ON_PUBLICATION,
    NOTIFICATION_MODE_SCHEDULED_THEN_PUBLICATION,
)

DEFAULT_NOTIFICATIONS_ENABLED = False
DEFAULT_NOTIFICATION_TIME = "18:00:00"
DEFAULT_NOTIFICATION_MODE = NOTIFICATION_MODE_SCHEDULED_THEN_PUBLICATION

NOTIFICATION_TITLE = "Ceny paliw GOV.PL"
NOTIFICATION_TEST_TITLE = "Test powiadomienia"
NOTIFICATION_DATA = {
    "ttl": 0,
    "priority": "high",
}

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = f"{DOMAIN}.notification_state"
