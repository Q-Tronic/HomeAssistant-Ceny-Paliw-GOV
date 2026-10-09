"""Basic parser tests that do not require Home Assistant."""

from datetime import date
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ceny_paliw_gov_pl"

package = types.ModuleType("ceny_paliw_gov_pl")
package.__path__ = [str(COMPONENT)]
sys.modules["ceny_paliw_gov_pl"] = package

for module_name in ("const", "api"):
    spec = importlib.util.spec_from_file_location(
        f"ceny_paliw_gov_pl.{module_name}", COMPONENT / f"{module_name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

api = sys.modules["ceny_paliw_gov_pl.api"]


class ParserTests(unittest.TestCase):
    def test_single_days_and_weekend_range(self) -> None:
        html = """
        <html><body>
        <div>06.10.2026</div>
        <a href="/web/energia/cena-7-pazdziernika">Maksymalna cena detaliczna paliw obowiązująca 7 października 2026 r.</a>
        <p>Benzyna 95 - 6,86 zł/l, benzyna 98 - 7,74 zł/l, olej napędowy - 7,80 zł/l.</p>
        <div>05.10.2026</div>
        <a href="/web/energia/cena-6-pazdziernika">Maksymalna cena detaliczna paliw obowiązująca 6 października 2026 r.</a>
        <p>Benzyna 95 - 6,79 zł/l, benzyna 98 - 7,66 zł/l, olej napędowy - 7,82 zł/l.</p>
        <div>02.10.2026</div>
        <a href="/web/energia/tansze-tankowanie">Tańsze tankowanie dla kierowców</a>
        <p>Benzyna 95 - 6,73 zł/l, benzyna 98 - 7,59 zł/l, olej napędowy - 7,88 zł/l. Takie maksymalne ceny paliw będą obowiązywać od soboty 3 października do poniedziałku 5 października włącznie.</p>
        </body></html>
        """
        periods = api.parse_news_page(html)
        self.assertEqual(len(periods), 3)

        by_start = {period.valid_from: period for period in periods}
        today = by_start[date(2026, 10, 6)]
        tomorrow = by_start[date(2026, 10, 7)]
        weekend = by_start[date(2026, 10, 3)]

        self.assertEqual(today.prices["pb95"], Decimal("6.79"))
        self.assertEqual(tomorrow.prices["pb98"], Decimal("7.74"))
        self.assertEqual(weekend.valid_to, date(2026, 10, 5))
        self.assertTrue(today.source_url.endswith("/web/energia/cena-6-pazdziernika"))

    def test_period_title(self) -> None:
        html = """
        <html><body>
        <div>26.06.2026</div>
        <a href="/web/energia/weekend">Maksymalna cena detaliczna paliw obowiązująca w okresie 27-29 czerwca 2026 r.</a>
        <p>Benzyna 95 - 6,02 zł/l, benzyna 98 - 6,70 zł/l, olej napędowy - 6,17 zł/l.</p>
        </body></html>
        """
        periods = api.parse_news_page(html)
        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0].valid_from, date(2026, 6, 27))
        self.assertEqual(periods[0].valid_to, date(2026, 6, 29))

    def test_weekend_range_in_days_title(self) -> None:
        html = """
        <html><body>
        <div>09.10.2026</div>
        <a href="/web/energia/maksymalna-cena-detaliczna-paliw-obowiazujaca-w-dniach-10-12-pazdziernika-2026-r">Maksymalna cena detaliczna paliw obowiązująca w dniach 10-12 października 2026 r.</a>
        <p>Benzyna 95 - 6,97 zł/l, benzyna 98 - 7,85 zł/l, olej napędowy - 8,06 zł/l.</p>
        </body></html>
        """
        periods = api.parse_news_page(html)
        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0].valid_from, date(2026, 10, 10))
        self.assertEqual(periods[0].valid_to, date(2026, 10, 12))
        self.assertEqual(periods[0].prices["pb95"], Decimal("6.97"))
        self.assertEqual(periods[0].prices["pb98"], Decimal("7.85"))
        self.assertEqual(periods[0].prices["on"], Decimal("8.06"))

    def test_cross_month_period_title(self) -> None:
        html = """
        <html><body>
        <div>30.10.2026</div>
        <a href="/web/energia/weekend-listopad">Maksymalna cena detaliczna paliw obowiązująca w okresie 31 października - 2 listopada 2026 r.</a>
        <p>Benzyna 95 - 6,10 zł/l, benzyna 98 - 6,80 zł/l, olej napędowy - 6,30 zł/l.</p>
        </body></html>
        """
        periods = api.parse_news_page(html)
        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0].valid_from, date(2026, 10, 31))
        self.assertEqual(periods[0].valid_to, date(2026, 11, 2))


if __name__ == "__main__":
    unittest.main()
