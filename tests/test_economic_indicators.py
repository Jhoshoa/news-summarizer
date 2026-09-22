import json
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from bs4 import BeautifulSoup

import src.main as main_module
from src.collectors.economic_indicators import EconomicIndicatorCollector
from src.db.indicators import EconomicIndicatorRepository
from src.main import app

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

BCB_HTML_WITH_OFFICIAL_RATE_CARD = """
<section class="bcb-kpi2" aria-label="Indicadores clave - BCB">
  <div class="bcb-kpi2-row">
    <article class="bcb-kpi2-card is-tc-oficial has-range-label">
      <div class="bcb-kpi2-hd">
        <p class="bcb-kpi2-name">Tipo de cambio oficial</p>
        <div class="bcb-kpi2-sub">Bolivianos por dólar estadounidense</div>
        <div class="bcb-kpi2-asof">
          <time datetime="2026-09-07">VIGENTE PARA EL SÁBADO 5, DOMINGO 6 Y LUNES 7 DE SEPTIEMBRE, 2026</time>
        </div>
      </div>
      <div class="bcb-kpi2-body">
        <div class="bcb-tco-value">
          <div class="bcb-tco-amount">
            <span class="bcb-tco-num">12,58</span>
          </div>
        </div>
      </div>
    </article>
  </div>
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


@pytest.mark.asyncio
async def test_fetch_bcb_uses_home_official_rate_card_over_stale_report_page():
    """El home publica el tipo de cambio oficial vigente en la propia tarjeta
    (.bcb-tco-amount); el reporte aparte (tco_reporte_ultima_cotizacion.php)
    es un indicador distinto (promedio de transacciones bancarias) que se
    actualiza con rezago. Caso real /article regression: el home informaba
    Bs 12,58 vigente para el 5-7 de septiembre de 2026 mientras el reporte
    aun mostraba Bs 11,52 con vigencia del 21 de agosto -- se debe usar el
    valor del home y ni siquiera consultar el reporte cuando la tarjeta
    trae el valor.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://www.bcb.gob.bo/":
            return httpx.Response(200, text=BCB_HTML_WITH_OFFICIAL_RATE_CARD)

        raise AssertionError(
            f"no deberia consultarse {request.url} cuando el home ya trae el valor oficial"
        )

    collector = EconomicIndicatorCollector()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        indicators = await collector.fetch_bcb(client, snapshot_key="snapshot", collected_at=None)

    by_code = {indicator.indicator_code: indicator for indicator in indicators}

    assert by_code["bcb_tipo_de_cambio_oficial"].value == Decimal("12.58")
    assert by_code["bcb_tipo_de_cambio_oficial"].observed_at.isoformat() == "2026-09-07"


def test_parse_official_usd_report_uses_latest_daily_row_as_fallback():
    collector = EconomicIndicatorCollector()
    soup = BeautifulSoup(BCB_OFFICIAL_USD_TABLE_ONLY_HTML, "lxml")

    value_text, observed_at, validity_label = collector._parse_official_usd_report(soup)

    assert value_text == "11,62"
    assert observed_at == date(2026, 8, 14)
    assert validity_label == ""


@pytest.mark.asyncio
async def test_fetch_binance_p2p_picks_best_price_per_side():
    """buy (comprando USDT) quiere el precio mas bajo que alguien pide;
    sell (vendiendo USDT) quiere el precio mas alto que alguien ofrece
    pagar -- ver caso real donde Binance mostraba venta a Bs 12,46 (el mas
    alto de los anuncios) y nosotros guardabamos Bs 12,44 (el mas bajo)
    por tomar siempre el minimo sin importar el lado.
    """

    # Anunciante confiable de sobra (ordenes/tasa de completado por encima
    # de MIN_ADVERTISER_ORDER_COUNT/MIN_ADVERTISER_FINISH_RATE) -- este test
    # es sobre la direccion del min/max por lado, no sobre el filtro de
    # confiabilidad (ver test_fetch_binance_p2p_* mas abajo para eso).
    reliable_advertiser = {"monthOrderCount": 500, "monthFinishRate": 0.99, "userType": "merchant"}

    responses = {
        "BUY": {
            "data": [
                {"adv": {"price": "9.95", "advNo": "high-buy"}, "advertiser": reliable_advertiser},
                {"adv": {"price": "9.93", "advNo": "low-buy"}, "advertiser": reliable_advertiser},
            ]
        },
        "SELL": {
            "data": [
                {"adv": {"price": "9.91", "advNo": "high-sell"}, "advertiser": reliable_advertiser},
                {"adv": {"price": "9.90", "advNo": "low-sell"}, "advertiser": reliable_advertiser},
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
    assert by_side["buy"].raw_payload["selection"] == "lowest_price"
    assert by_side["sell"].value == Decimal("9.91")
    assert by_side["sell"].raw_payload["advertisement"]["adv"]["advNo"] == "high-sell"
    assert by_side["sell"].raw_payload["selection"] == "highest_price"


@pytest.mark.asyncio
async def test_fetch_binance_p2p_requests_only_verified_merchants():
    """publisherType="merchant" es el mismo filtro "cajeros verificados" de
    la UI de Binance -- confirmado en vivo contra la API real: con
    publisherType=None, 4 de 20 anuncios eran usuarios sin verificar; con
    "merchant", los 20 eran mercaderes certificados. Un pico real (Bs 12,03
    de venta vs ~10,7-10,9 del resto) salio de un usuario no verificado con
    pocas ordenes -- operar sin verificar ya es mas riesgoso de por si, asi
    que ni siquiera deberian entrar al pool de candidatos."""

    advertiser = {"monthOrderCount": 500, "monthFinishRate": 0.99}
    seen_payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        seen_payloads.append(payload)
        return httpx.Response(
            200,
            json={"data": [{"adv": {"price": "10.00", "advNo": "x"}, "advertiser": advertiser}]},
        )

    collector = EconomicIndicatorCollector()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await collector.fetch_binance_p2p(client, snapshot_key="snapshot", collected_at=None)

    assert len(seen_payloads) == 2
    assert {payload["tradeType"] for payload in seen_payloads} == {"BUY", "SELL"}
    assert all(payload["publisherType"] == "merchant" for payload in seen_payloads)


@pytest.mark.asyncio
async def test_fetch_binance_p2p_discards_unreliable_outlier_advertiser():
    """Caso real: un anuncio de venta a Bs 12.03 (vs. ~10.7-10.9 del resto)
    vino de un anunciante con 4 ordenes en el mes y 36% de tasa de
    completado -- ese anuncio no deberia poder mover el precio guardado."""

    reliable = {"monthOrderCount": 500, "monthFinishRate": 0.99, "userType": "merchant"}
    unreliable = {"monthOrderCount": 4, "monthFinishRate": 0.364}

    responses = {
        "BUY": {"data": [{"adv": {"price": "9.90", "advNo": "only-buy"}, "advertiser": reliable}]},
        "SELL": {
            "data": [
                {"adv": {"price": "10.90", "advNo": "normal-sell"}, "advertiser": reliable},
                {"adv": {"price": "12.03", "advNo": "outlier-sell"}, "advertiser": unreliable},
            ]
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        return httpx.Response(200, json=responses[payload["tradeType"]])

    collector = EconomicIndicatorCollector()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        indicators = await collector.fetch_binance_p2p(
            client, snapshot_key="snapshot", collected_at=None
        )

    sell = next(i for i in indicators if i.side == "sell")
    assert sell.value == Decimal("10.90")
    assert sell.raw_payload["advertisement"]["adv"]["advNo"] == "normal-sell"
    assert sell.raw_payload["selection"] == "highest_price"


@pytest.mark.asyncio
async def test_fetch_binance_p2p_discards_unverified_user_even_with_good_stats():
    """Caso real (id=2438 en produccion): un anunciante tipo "user" (no
    mercader verificado) con 129 ordenes en el mes y 99.3% de completado --
    numeros que superan de sobra MIN_ADVERTISER_ORDER_COUNT/
    MIN_ADVERTISER_FINISH_RATE -- publico Bs 11.12 de compra, un solo punto
    aislado muy por debajo de los ~12.16-12.18 de antes y despues. Buen
    historial no alcanza si no esta verificado: el filtro de userType debe
    descartarlo igual, dejando pasar al mercader aunque su precio sea peor
    para nosotros."""

    good_but_unverified_user = {
        "monthOrderCount": 129,
        "monthFinishRate": 0.993,
        "userType": "user",
    }
    verified_merchant = {
        "monthOrderCount": 500,
        "monthFinishRate": 0.99,
        "userType": "merchant",
    }

    responses = {
        "BUY": {
            "data": [
                {"adv": {"price": "12.17", "advNo": "merchant-buy"}, "advertiser": verified_merchant},
                {"adv": {"price": "11.12", "advNo": "unverified-buy"}, "advertiser": good_but_unverified_user},
            ]
        },
        "SELL": {"data": [{"adv": {"price": "12.20", "advNo": "only-sell"}, "advertiser": verified_merchant}]},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        return httpx.Response(200, json=responses[payload["tradeType"]])

    collector = EconomicIndicatorCollector()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        indicators = await collector.fetch_binance_p2p(
            client, snapshot_key="snapshot", collected_at=None
        )

    buy = next(i for i in indicators if i.side == "buy")
    assert buy.value == Decimal("12.17")
    assert buy.raw_payload["advertisement"]["adv"]["advNo"] == "merchant-buy"
    assert buy.raw_payload["selection"] == "lowest_price"


@pytest.mark.asyncio
async def test_fetch_binance_p2p_falls_back_to_unfiltered_pool_when_nobody_is_reliable():
    """Si un lote entero es de anunciantes poco confiables (mercado muy
    delgado en ese momento), mejor guardar ese precio igual -- marcado como
    fallback en `selection` para poder auditarlo -- que perder el dato."""

    unreliable = {"monthOrderCount": 2, "monthFinishRate": 0.5}
    responses = {
        "BUY": {"data": [{"adv": {"price": "9.90", "advNo": "thin-buy"}, "advertiser": unreliable}]},
        "SELL": {"data": [{"adv": {"price": "11.20", "advNo": "thin-sell"}, "advertiser": unreliable}]},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        return httpx.Response(200, json=responses[payload["tradeType"]])

    collector = EconomicIndicatorCollector()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        indicators = await collector.fetch_binance_p2p(
            client, snapshot_key="snapshot", collected_at=None
        )

    sell = next(i for i in indicators if i.side == "sell")
    assert sell.value == Decimal("11.20")
    assert sell.raw_payload["selection"] == "highest_price_unfiltered_fallback"


@pytest.mark.asyncio
async def test_fetch_binance_p2p_treats_missing_advertiser_fields_as_unreliable():
    """Sin monthOrderCount/monthFinishRate no hay forma de saber si el
    anunciante es confiable -- se trata como no confiable, no como valido."""

    responses = {
        "BUY": {"data": [{"adv": {"price": "9.90", "advNo": "no-advertiser-info"}}]},
        "SELL": {"data": [{"adv": {"price": "9.90", "advNo": "no-advertiser-info"}}]},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        return httpx.Response(200, json=responses[payload["tradeType"]])

    collector = EconomicIndicatorCollector()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        indicators = await collector.fetch_binance_p2p(
            client, snapshot_key="snapshot", collected_at=None
        )

    sell = next(i for i in indicators if i.side == "sell")
    assert sell.raw_payload["selection"] == "highest_price_unfiltered_fallback"


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


class _FakeSessionCtx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc_info):
        return False


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalars(self._rows)


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.executed_statements = []

    async def execute(self, stmt):
        self.executed_statements.append(stmt)
        return _FakeResult(self._rows)


def _compiled_sql(stmt) -> str:
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


def _make_value_row(code: str, value: Decimal, collected_at: datetime, observed_at=None):
    from src.db.indicators import EconomicIndicatorValue

    return EconomicIndicatorValue(
        source="bcb",
        indicator_code=code,
        indicator_name=code,
        indicator_group="grupo",
        value=value,
        observed_at=observed_at,
        collected_at=collected_at,
        snapshot_key="snap",
    )


@pytest.mark.asyncio
async def test_get_history_filters_by_codes_and_since():
    repository = object.__new__(EconomicIndicatorRepository)
    session = _FakeSession(rows=[])
    repository.session_maker = lambda: _FakeSessionCtx(session)

    since = datetime(2026, 6, 1, 0, 0, 0)
    await repository.get_history(["bcb_tipo_de_cambio_oficial", "binance_p2p_usdt_bob_buy"], since)

    assert len(session.executed_statements) == 1
    sql = _compiled_sql(session.executed_statements[0])
    assert "indicator_code IN ('bcb_tipo_de_cambio_oficial', 'binance_p2p_usdt_bob_buy')" in sql
    assert "collected_at >= '2026-06-01 00:00:00'" in sql
    assert "ORDER BY economic_indicator_values.collected_at ASC" in sql


@pytest.mark.asyncio
async def test_get_history_groups_rows_by_indicator_code_in_chronological_order():
    repository = object.__new__(EconomicIndicatorRepository)
    rows = [
        _make_value_row("bcb_tipo_de_cambio_oficial", Decimal("11.52"), datetime(2026, 8, 17, 10, 0)),
        _make_value_row("binance_p2p_usdt_bob_buy", Decimal("11.60"), datetime(2026, 8, 17, 10, 5)),
        _make_value_row("binance_p2p_usdt_bob_buy", Decimal("11.62"), datetime(2026, 8, 17, 10, 10)),
    ]
    session = _FakeSession(rows=rows)
    repository.session_maker = lambda: _FakeSessionCtx(session)

    history = await repository.get_history(
        ["bcb_tipo_de_cambio_oficial", "binance_p2p_usdt_bob_buy", "binance_p2p_usdt_bob_sell"],
        since=datetime(2026, 1, 1),
    )

    assert [p["value"] for p in history["bcb_tipo_de_cambio_oficial"]] == [11.52]
    assert [p["value"] for p in history["binance_p2p_usdt_bob_buy"]] == [11.60, 11.62]
    assert history["binance_p2p_usdt_bob_sell"] == []


@pytest.fixture
def fake_app_instance_with_history():
    original = main_module.app_instance
    rows = [
        _make_value_row("bcb_tipo_de_cambio_oficial", Decimal("12.04"), datetime(2026, 9, 10, 9, 0)),
        _make_value_row("binance_p2p_usdt_bob_buy", Decimal("11.82"), datetime(2026, 9, 10, 9, 5)),
    ]
    session = _FakeSession(rows=rows)
    db = SimpleNamespace(session_maker=lambda: _FakeSessionCtx(session))
    main_module.app_instance = SimpleNamespace(db=db, settings=SimpleNamespace())
    try:
        yield session
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_economic_indicators_history_endpoint_returns_series(fake_app_instance_with_history):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/economic-indicators/history",
            params={"codes": "bcb_tipo_de_cambio_oficial,binance_p2p_usdt_bob_buy", "days": 30},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["days"] == 30
    assert [p["value"] for p in payload["series"]["bcb_tipo_de_cambio_oficial"]] == [12.04]
    assert [p["value"] for p in payload["series"]["binance_p2p_usdt_bob_buy"]] == [11.82]


@pytest.mark.asyncio
async def test_economic_indicators_history_defaults_to_bcb_and_binance_codes(
    fake_app_instance_with_history,
):
    session = fake_app_instance_with_history
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/economic-indicators/history")

    assert response.status_code == 200
    sql = _compiled_sql(session.executed_statements[0])
    assert "bcb_tipo_de_cambio_oficial" in sql
    assert "binance_p2p_usdt_bob_buy" in sql
    assert "binance_p2p_usdt_bob_sell" in sql
