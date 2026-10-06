"""Constants for the Ceny paliw GOV.PL integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "ceny_paliw_gov_pl"
NAME = "Ceny paliw GOV.PL"
VERSION = "1.0.0"
AUTHOR = "Q-Tronic"

NEWS_URL = "https://www.gov.pl/web/energia/wiadomosci"
REPOSITORY_URL = "https://github.com/Q-Tronic/homeassistant-ceny-paliw-gov"
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
