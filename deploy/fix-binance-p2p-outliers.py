"""One-off: corrige valores historicos de binance_p2p_usdt_bob_buy/sell que
vinieron de un anunciante poco confiable (ver el fix real en
src/collectors/economic_indicators.py, _is_reliable_advertiser). Ese fix
solo evita que vuelva a pasar en la recoleccion de ahora en adelante --
este script limpia lo que ya quedo guardado de antes, con el mismo
criterio (monthOrderCount / monthFinishRate) para no duplicar logica.

Cada valor de un anunciante no confiable se reemplaza por una
interpolacion lineal en el tiempo entre el valor confiable mas cercano
antes y despues de esa fecha (mismo indicator_code). Si falta un lado, usa
el otro. Si no hay ningun valor confiable cerca (mercado muy delgado en
ese tramo), no toca esa fila y lo reporta en vez de inventar un numero.

Uso (desde la raiz del repo, con el venv activado):
    python deploy/fix-binance-p2p-outliers.py            # dry-run, no escribe nada
    python deploy/fix-binance-p2p-outliers.py --apply    # aplica los cambios

Antes de correr con --apply en produccion, se recomienda un pg_dump de
economic_indicator_values por las dudas (ver DEPLOYMENT.md).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# `python deploy/fix-binance-p2p-outliers.py` pone el directorio del script
# (deploy/) primero en sys.path, no la raiz del repo -- sin esto, `import src`
# falla con ModuleNotFoundError sin importar desde donde se lo corra.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from src.collectors.economic_indicators import EconomicIndicatorCollector  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.db.indicators import EconomicIndicatorValue  # noqa: E402
from src.db.repository import Database  # noqa: E402

CODES = ["binance_p2p_usdt_bob_buy", "binance_p2p_usdt_bob_sell"]


def is_reliable(collector: EconomicIndicatorCollector, row: EconomicIndicatorValue) -> bool:
    advertiser = ((row.raw_payload or {}).get("advertisement") or {}).get("advertiser") or {}
    return collector._is_reliable_advertiser({"advertiser": advertiser})


def interpolate(
    before: EconomicIndicatorValue | None,
    after: EconomicIndicatorValue | None,
    at: datetime,
) -> Decimal | None:
    if before is None and after is None:
        return None
    if before is None:
        return after.value
    if after is None:
        return before.value
    if after.collected_at == before.collected_at:
        return before.value

    total_seconds = (after.collected_at - before.collected_at).total_seconds()
    elapsed_seconds = (at - before.collected_at).total_seconds()
    ratio = Decimal(str(elapsed_seconds / total_seconds))
    return before.value + (after.value - before.value) * ratio


async def main(apply: bool) -> None:
    settings = get_settings()
    db = Database(settings.database_url)
    collector = EconomicIndicatorCollector()

    changed = 0
    skipped = 0

    async with db.session_maker() as session:
        for code in CODES:
            stmt = (
                select(EconomicIndicatorValue)
                .where(EconomicIndicatorValue.indicator_code == code)
                .order_by(EconomicIndicatorValue.collected_at.asc())
            )
            rows = list((await session.execute(stmt)).scalars().all())
            reliable_rows = [row for row in rows if is_reliable(collector, row)]

            for row in rows:
                if is_reliable(collector, row):
                    continue

                before = max(
                    (r for r in reliable_rows if r.collected_at < row.collected_at),
                    key=lambda r: r.collected_at,
                    default=None,
                )
                after = min(
                    (r for r in reliable_rows if r.collected_at > row.collected_at),
                    key=lambda r: r.collected_at,
                    default=None,
                )
                new_value = interpolate(before, after, row.collected_at)

                if new_value is None:
                    print(f"SIN TOCAR  {code} id={row.id} {row.collected_at}: sin vecino confiable cerca")
                    skipped += 1
                    continue

                action = "APLICAR" if apply else "DRY-RUN"
                print(f"{action}   {code} id={row.id} {row.collected_at}: {row.value} -> {new_value}")

                if apply:
                    row.raw_payload = {
                        **(row.raw_payload or {}),
                        "corrected": {
                            "original_value": str(row.value),
                            "reason": "unreliable_advertiser_backfill_correction",
                            "corrected_at": datetime.utcnow().isoformat(),
                        },
                    }
                    row.value = new_value
                changed += 1

        if apply:
            await session.commit()
            print(f"\nListo: {changed} corregidos, {skipped} sin vecino confiable (sin tocar).")
        else:
            print(
                f"\nDRY-RUN: {changed} se corregirian, {skipped} quedarian igual. "
                "Corre con --apply para aplicar de verdad."
            )

    await db.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica los cambios de verdad. Sin esta flag solo hace dry-run.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.apply))
