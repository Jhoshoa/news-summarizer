import json
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from bs4 import BeautifulSoup

from src.collectors.economic_indicators import EconomicIndicatorCollector
from src.db.indicators import EconomicIndicatorRepository

BCB_HTML = """
<section class="bcb-kpi2" aria-label="Indicadores clave - BCB">
  <div class="bcb-kpi2-row">
    <article class="bcb-kpi2-card">
      <div class="bcb-kpi2-hd">
        <p class="bcb-kpi2-name">Tipo de cambio</p>
        <div class="bcb-kpi2-sub">Tipo de cambio Bs por 1 Dólar USA.</div>
        <div class="bcb-kpi2-asof"><time>domingo 10 de mayo, 2026</time></div>
      </div>
      <div class="bcb-kpi2-body">
        <div class="bcb-row"><div class="bcb-lbl">Compra</div><div class="bcb-val">6,86</div></div>
        <div class="bcb-row"><div class="bcb-lbl">Venta</div><div class="bcb-val">6,96</div></div>
      </div>
    </article>
    <article class="bcb-kpi2-card">
      <div class="bcb-kpi2-hd">
        <p class="bcb-kpi2-name">Tasa de referencia (TRe) %</p>
        <div class="bcb-kpi2-asof">Del 01/05/2026 al 31/05/2026</div>
      </div>
      <div class="bcb-kpi2-body">
        <div class="bcb-row"><div class="bcb-lbl">MN</div><div class="bcb-val sm">3,53</div></div>
        <div class="bcb-row"><div class="bcb-lbl">ME</div><div class="bcb-val sm">0,51</div></div>
      </div>
    </article>
    <article class="bcb-kpi2-card">
      <div class="bcb-kpi2-hd">
        <p class="bcb-kpi2-name">Unidad de fomento a la vivienda</p>
        <div class="bcb-kpi2-asof"><time>domingo 10 de mayo, 2026</time></div>
      </div>
      <div class="bcb-kpi2-body">
        <div class="bcb-lbl">UFV</div>
        <div class="bcb-val">Bs 3,27232</div>
      </div>
    </article>
    <article class="bcb-kpi2-card">
      <div class="bcb-kpi2-hd">
        <p class="bcb-kpi2-name">Cotización internacional del oro</p>
        <div class="bcb-kpi2-sub">USD / O.T.F.</div>
        <div class="bcb-kpi2-asof"><time>domingo 10 de mayo, 2026</time></div>
      </div>
      <div class="bcb-kpi2-body">
        <div class="bcb-lbl">Valor</div>
        <div class="bcb-val">4.269,71</div>
      </div>
    </article>
  </div>
</section>
"""

BCB_OFFICIAL_USD_HTML = """
<section class="bcb-vrd-wrap" aria-label="Tipo de Cambio Oficial del Dolar Estadounidense">
  <div class="tco-public-card" aria-label="Reporte de ultima cotizacion TCO">
    <div class="tco-public-summary">
      <h3>Ultima cotizacion</h3>
      <div class="tco-public-value">Bs 11,58/$us</div>
      <span class="tco-public-date">FECHA DE CORTE: VIERNES 14 DE AGOSTO DE 2026</span>
      <span class="tco-public-vigencia">VIGENCIA: LUNES 17 DE AGOSTO DE 2026</span>
    </div>
  </div>
  <table class="tco-daily-table">
    <tbody>
      <tr><td>sabado, 15 de agosto de 2026</td><td>11,58</td></tr>
      <tr><td>domingo, 16 de agosto de 2026</td><td>11,58</td></tr>
      <tr><td>lunes, 17 de agosto de 2026</td><td>11,58</td></tr>
    </tbody>
  </table>
</section>
"""

BCB_OFFICIAL_USD_TABLE_ONLY_HTML = """
<section class="bcb-vrd-wrap" aria-label="Tipo de Cambio Oficial del Dolar Estadounidense">
  <table class="tco-daily-table">
    <tbody>
      <tr><td>jueves, 13 de agosto de 2026</td><td>11,66</td></tr>
      <tr><td>viernes, 14 de agosto de 2026</td><td>11,62</td></tr>
    </tbody>
  </table>
</section>
"""


@pytest.mark.asyncio
async def test_fetch_bcb_parses_key_indicator_cards():
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://www.bcb.gob.bo/":
            return httpx.Response(200, text=BCB_HTML)

        assert str(request.url) == "https://www.bcb.gob.bo/tco_reporte_ultima_cotizacion.php"
        return httpx.Response(200, text=BCB_OFFICIAL_USD_HTML)

    collector = EconomicIndicatorCollector()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        indicators = await collector.fetch_bcb(client, snapshot_key="snapshot", collected_at=None)

    by_code = {indicator.indicator_code: indicator for indicator in indicators}

    assert "bcb_tipo_de_cambio_compra" not in by_code
    assert "bcb_tipo_de_cambio_venta" not in by_code
    assert by_code["bcb_tipo_de_cambio_oficial"].value == Decimal("11.58")
    assert by_code["bcb_tipo_de_cambio_oficial"].side is None
    assert by_code["bcb_tipo_de_cambio_oficial"].observed_at.isoformat() == "2026-08-17"
    assert by_code["bcb_tipo_de_cambio_oficial"].raw_payload["validity_label"] == (
        "VIGENCIA: LUNES 17 DE AGOSTO DE 2026"
    )
    assert by_code["bcb_tasa_de_referencia_tre_mn"].value == Decimal("3.53")
    assert by_code["bcb_tasa_de_referencia_tre_me"].unit == "%"
    assert by_code["bcb_unidad_de_fomento_a_la_vivienda_ufv"].value == Decimal("3.27232")
    assert by_code["bcb_unidad_de_fomento_a_la_vivienda_ufv"].asset == "UFV"
    assert by_code["bcb_cotizacion_internacional_del_oro_valor"].value == Decimal("4269.71")
    assert by_code["bcb_cotizacion_internacional_del_oro_valor"].asset == "GOLD"


def test_parse_official_usd_report_uses_latest_daily_row_as_fallback():
    collector = EconomicIndicatorCollector()
    soup = BeautifulSoup(BCB_OFFICIAL_USD_TABLE_ONLY_HTML, "lxml")

    value_text, observed_at, validity_label = collector._parse_official_usd_report(soup)

    assert value_text == "11,62"
    assert observed_at == date(2026, 8, 14)
    assert validity_label == ""


@pytest.mark.asyncio
async def test_fetch_binance_p2p_uses_lowest_bob_price_for_buy_and_sell():
    responses = {
        "BUY": {
            "data": [
                {"adv": {"price": "9.95", "advNo": "high-buy"}},
                {"adv": {"price": "9.93", "advNo": "low-buy"}},
            ]
        },
        "SELL": {
            "data": [
                {"adv": {"price": "9.91", "advNo": "high-sell"}},
                {"adv": {"price": "9.90", "advNo": "low-sell"}},
            ]
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        trade_type = payload["tradeType"]
        return httpx.Response(200, json=responses[trade_type])

    collector = EconomicIndicatorCollector()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        indicators = await collector.fetch_binance_p2p(
            client,
            snapshot_key="snapshot",
            collected_at=None,
        )

    by_side = {indicator.side: indicator for indicator in indicators}

    assert by_side["buy"].value == Decimal("9.93")
    assert by_side["buy"].raw_payload["advertisement"]["adv"]["advNo"] == "low-buy"
    assert by_side["sell"].value == Decimal("9.90")
    assert by_side["sell"].raw_payload["advertisement"]["adv"]["advNo"] == "low-sell"


def test_indicator_repository_same_day_requires_same_observed_or_collected_day():
    repository = object.__new__(EconomicIndicatorRepository)
    existing = SimpleNamespace(
        observed_at=date(2026, 5, 10),
        collected_at=datetime(2026, 5, 10, 9, 0),
    )

    assert repository._same_day(
        existing,
        {
            "observed_at": date(2026, 5, 10),
            "collected_at": datetime(2026, 5, 10, 10, 0),
        },
    )
    assert not repository._same_day(
        existing,
        {
            "observed_at": date(2026, 5, 11),
            "collected_at": datetime(2026, 5, 11, 9, 0),
        },
    )


def test_indicator_repository_same_value_normalizes_decimal_scale():
    repository = object.__new__(EconomicIndicatorRepository)

    assert repository._same_value(Decimal("6.860000"), Decimal("6.86"))
    assert not repository._same_value(Decimal("6.86"), Decimal("6.87"))
