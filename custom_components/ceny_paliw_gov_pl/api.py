"""Client and parser for fuel price information published on gov.pl."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import re
from typing import Final
from urllib.parse import urljoin

import aiohttp

from .const import (
    FUEL_ON,
    FUEL_PB95,
    FUEL_PB98,
    NEWS_URL,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)


class FuelPriceApiError(Exception):
    """Base error raised by the gov.pl fuel price client."""


class FuelPriceParseError(FuelPriceApiError):
    """Raised when the gov.pl page cannot be parsed."""


@dataclass(frozen=True, slots=True)
class PricePeriod:
    """Fuel prices valid for a continuous date range."""

    valid_from: date
    valid_to: date
    prices: dict[str, Decimal]
    source_url: str
    published_on: date | None = None

    def contains(self, day: date) -> bool:
        """Return whether this period contains a given date."""
        return self.valid_from <= day <= self.valid_to


@dataclass(frozen=True, slots=True)
class FuelPriceData:
    """Resolved fuel price data for today and tomorrow."""

    today_date: date
    tomorrow_date: date
    today: PricePeriod | None
    tomorrow: PricePeriod | None
    fetched_at: datetime
    parsed_periods: int
    periods: tuple[PricePeriod, ...]


@dataclass(frozen=True, slots=True)
class _Link:
    """Anchor found on the news page."""

    end_position: int
    text: str
    href: str


class _NewsPageParser(HTMLParser):
    """Extract readable text and anchor positions without external dependencies."""

    _BLOCK_TAGS: Final[set[str]] = {
        "article",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "li",
        "p",
        "section",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._length = 0
        self._ignored_depth = 0
        self._current_href: str | None = None
        self._current_link_parts: list[str] = []
        self.links: list[_Link] = []

    @property
    def text(self) -> str:
        """Return the normalized visible text."""
        return "".join(self._parts)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            self._ignored_depth += 1
            return

        if self._ignored_depth:
            return

        if tag in self._BLOCK_TAGS:
            self._append_space()

        if tag == "a":
            href = dict(attrs).get("href")
            self._current_href = href
            self._current_link_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            if self._ignored_depth:
                self._ignored_depth -= 1
            return

        if self._ignored_depth:
            return

        if tag == "a" and self._current_href:
            link_text = " ".join(self._current_link_parts).strip()
            self.links.append(
                _Link(
                    end_position=self._length,
                    text=link_text,
                    href=self._current_href,
                )
            )
            self._current_href = None
            self._current_link_parts = []

        if tag in self._BLOCK_TAGS:
            self._append_space()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return

        clean = re.sub(r"\s+", " ", data).strip()
        if not clean:
            return

        if self._parts and not self._parts[-1].endswith(" "):
            self._append_raw(" ")

        self._append_raw(clean)
        if self._current_href is not None:
            self._current_link_parts.append(clean)

    def _append_space(self) -> None:
        if self._parts and not self._parts[-1].endswith(" "):
            self._append_raw(" ")

    def _append_raw(self, value: str) -> None:
        self._parts.append(value)
        self._length += len(value)


_MONTHS: Final[dict[str, int]] = {
    "stycznia": 1,
    "lutego": 2,
    "marca": 3,
    "kwietnia": 4,
    "maja": 5,
    "czerwca": 6,
    "lipca": 7,
    "sierpnia": 8,
    "września": 9,
    "wrzesnia": 9,
    "października": 10,
    "pazdziernika": 10,
    "listopada": 11,
    "grudnia": 12,
}
_MONTH_RE = "(?:" + "|".join(re.escape(name) for name in _MONTHS) + ")"

_PRICE_RE: Final[re.Pattern[str]] = re.compile(
    rf"benzyna\s*95\s*[-:\u2013\u2014]\s*(?P<pb95>\d+[,.]\d{{1,2}})\s*zł\s*/\s*l"
    rf".{{0,140}}?benzyna\s*98\s*[-:\u2013\u2014]\s*(?P<pb98>\d+[,.]\d{{1,2}})\s*zł\s*/\s*l"
    rf".{{0,140}}?olej\s+napędowy\s*[-:\u2013\u2014]\s*(?P<on>\d+[,.]\d{{1,2}})\s*zł\s*/\s*l",
    re.IGNORECASE | re.DOTALL,
)

_PUBLISHED_DATE_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?P<day>\d{1,2})\.(?P<month>\d{1,2})\.(?P<year>\d{4})\b"
)

_RANGE_SAME_MONTH_RE: Final[re.Pattern[str]] = re.compile(
    rf"obowiązuj\w*\s+w\s+(?:okresie|dniach)\s+"
    rf"(?P<start>\d{{1,2}})\s*[-\u2013\u2014]\s*(?P<end>\d{{1,2}})\s+"
    rf"(?P<month>{_MONTH_RE})(?:\s+(?P<year>\d{{4}}))?",
    re.IGNORECASE,
)


_RANGE_CROSS_MONTH_RE: Final[re.Pattern[str]] = re.compile(
    rf"obowiązuj\w*(?:\s+w\s+(?:okresie|dniach))?\s+"
    rf"(?P<start>\d{{1,2}})\s+(?P<start_month>{_MONTH_RE})\s*"
    rf"(?:[-\u2013\u2014]|do)\s*(?P<end>\d{{1,2}})\s+"
    rf"(?P<end_month>{_MONTH_RE})(?:\s+(?P<year>\d{{4}}))?",
    re.IGNORECASE,
)

_RANGE_FROM_TO_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?:będą\s+)?obowiązywać\s+od\s+(?:[a-ząćęłńóśźż]+\s+)?"
    rf"(?P<start>\d{{1,2}})\s+(?P<start_month>{_MONTH_RE})(?:\s+(?P<start_year>\d{{4}}))?\s+"
    rf"do\s+(?:[a-ząćęłńóśźż]+\s+)?(?P<end>\d{{1,2}})\s+"
    rf"(?P<end_month>{_MONTH_RE})(?:\s+(?P<end_year>\d{{4}}))?",
    re.IGNORECASE,
)

_SINGLE_DATE_RE: Final[re.Pattern[str]] = re.compile(
    rf"obowiązuj\w*\s+(?P<day>\d{{1,2}})\s+(?P<month>{_MONTH_RE})"
    rf"(?:\s+(?P<year>\d{{4}}))?",
    re.IGNORECASE,
)

_AFTER_SINGLE_DATE_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?:będą\s+)?obowiązywać\s+(?P<day>\d{{1,2}})\s+(?P<month>{_MONTH_RE})"
    rf"(?:\s+(?P<year>\d{{4}}))?",
    re.IGNORECASE,
)


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", ".")).quantize(Decimal("0.01"))
    except InvalidOperation as err:
        raise FuelPriceParseError(f"Nieprawidłowa cena: {value}") from err


def _month_number(value: str) -> int:
    month = _MONTHS.get(value.lower())
    if month is None:
        raise FuelPriceParseError(f"Nieznana nazwa miesiąca: {value}")
    return month


def _safe_date(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError as err:
        raise FuelPriceParseError(
            f"Nieprawidłowa data w publikacji: {day}.{month}.{year}"
        ) from err


def _publication_date(before: str) -> date | None:
    matches = list(_PUBLISHED_DATE_RE.finditer(before))
    if not matches:
        return None

    match = matches[-1]
    return _safe_date(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
    )


def _year_or_reference(value: str | None, published_on: date | None) -> int:
    if value:
        return int(value)
    if published_on:
        return published_on.year
    return date.today().year


def _parse_validity(
    before: str,
    after: str,
    published_on: date | None,
) -> tuple[date, date] | None:
    before_near = before[-320:]
    after_near = after[:420]

    cross_month_matches = list(_RANGE_CROSS_MONTH_RE.finditer(before_near))
    if cross_month_matches:
        match = cross_month_matches[-1]
        if len(before_near) - match.end() <= 180:
            start_month = _month_number(match.group("start_month"))
            end_month = _month_number(match.group("end_month"))
            end_year = _year_or_reference(match.group("year"), published_on)
            start_year = end_year - (1 if start_month > end_month else 0)
            return (
                _safe_date(start_year, start_month, int(match.group("start"))),
                _safe_date(end_year, end_month, int(match.group("end"))),
            )

    same_month_matches = list(_RANGE_SAME_MONTH_RE.finditer(before_near))
    if same_month_matches:
        match = same_month_matches[-1]
        if len(before_near) - match.end() > 180:
            match = None
        if match is not None:
            year = _year_or_reference(match.group("year"), published_on)
            month = _month_number(match.group("month"))
            return (
                _safe_date(year, month, int(match.group("start"))),
                _safe_date(year, month, int(match.group("end"))),
            )

    single_matches = list(_SINGLE_DATE_RE.finditer(before_near))
    if single_matches:
        match = single_matches[-1]
        if len(before_near) - match.end() <= 180:
            year = _year_or_reference(match.group("year"), published_on)
            day = _safe_date(
                year,
                _month_number(match.group("month")),
                int(match.group("day")),
            )
            return day, day

    from_to_matches = list(_RANGE_FROM_TO_RE.finditer(after_near))
    if from_to_matches:
        match = from_to_matches[0]
        start_month = _month_number(match.group("start_month"))
        end_month = _month_number(match.group("end_month"))
        start_year = _year_or_reference(match.group("start_year"), published_on)
        end_year = (
            int(match.group("end_year"))
            if match.group("end_year")
            else start_year + (1 if end_month < start_month else 0)
        )
        return (
            _safe_date(start_year, start_month, int(match.group("start"))),
            _safe_date(end_year, end_month, int(match.group("end"))),
        )

    after_single_matches = list(_AFTER_SINGLE_DATE_RE.finditer(after_near))
    if after_single_matches:
        match = after_single_matches[0]
        year = _year_or_reference(match.group("year"), published_on)
        day = _safe_date(year, _month_number(match.group("month")), int(match.group("day")))
        return day, day

    return None


def _nearest_article_link(links: list[_Link], match_start: int) -> _Link | None:
    candidates = [
        link
        for link in links
        if link.end_position <= match_start
        and match_start - link.end_position <= 500
        and link.href
        and "/web/energia/" in link.href
        and link.text
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.end_position)


def parse_news_page(html: str) -> list[PricePeriod]:
    """Parse fuel price periods from the Ministerstwo Energii news page."""
    parser = _NewsPageParser()
    parser.feed(html)
    text = parser.text

    periods: list[PricePeriod] = []
    seen: set[tuple[date, date, Decimal, Decimal, Decimal]] = set()

    for match in _PRICE_RE.finditer(text):
        before = text[max(0, match.start() - 420) : match.start()]
        after = text[match.end() : min(len(text), match.end() + 500)]
        article_link = _nearest_article_link(parser.links, match.start())
        title_context = article_link.text if article_link is not None else before
        published_on = _publication_date(before)
        validity = _parse_validity(title_context, after, published_on)
        if validity is None:
            continue

        valid_from, valid_to = validity
        prices = {
            FUEL_PB95: _decimal(match.group("pb95")),
            FUEL_PB98: _decimal(match.group("pb98")),
            FUEL_ON: _decimal(match.group("on")),
        }
        key = (
            valid_from,
            valid_to,
            prices[FUEL_PB95],
            prices[FUEL_PB98],
            prices[FUEL_ON],
        )
        if key in seen:
            continue
        seen.add(key)

        periods.append(
            PricePeriod(
                valid_from=valid_from,
                valid_to=valid_to,
                prices=prices,
                source_url=(
                    urljoin(NEWS_URL, article_link.href)
                    if article_link is not None
                    else NEWS_URL
                ),
                published_on=published_on,
            )
        )

    periods.sort(
        key=lambda item: (
            item.published_on or date.min,
            item.valid_from,
            item.valid_to,
        ),
        reverse=True,
    )
    return periods


def _resolve_period(periods: list[PricePeriod], target: date) -> PricePeriod | None:
    matches = [period for period in periods if period.contains(target)]
    if not matches:
        return None
    return max(
        matches,
        key=lambda item: (
            item.published_on or date.min,
            item.valid_from,
            item.valid_to,
        ),
    )


class FuelPriceApi:
    """Fetch fuel price data from gov.pl."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def async_fetch(self, today: date, now: datetime) -> FuelPriceData:
        """Fetch and resolve prices for today and tomorrow."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                async with self._session.get(
                    NEWS_URL,
                    headers={"User-Agent": USER_AGENT},
                ) as response:
                    response.raise_for_status()
                    html = await response.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise FuelPriceApiError(f"Błąd pobierania danych z gov.pl: {err}") from err

        periods = parse_news_page(html)
        if not periods:
            raise FuelPriceParseError(
                "Nie znaleziono żadnych publikacji z cenami paliw na stronie gov.pl"
            )

        tomorrow = date.fromordinal(today.toordinal() + 1)
        return FuelPriceData(
            today_date=today,
            tomorrow_date=tomorrow,
            today=_resolve_period(periods, today),
            tomorrow=_resolve_period(periods, tomorrow),
            fetched_at=now,
            parsed_periods=len(periods),
            periods=tuple(periods),
        )
