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

Ademas del anunciante no confiable, exige que el valor se desvie mas de
MIN_DEVIATION_RATIO del valor interpolado antes de corregirlo -- sin esto,
un anunciante que no llega al umbral de confiabilidad por poco (ej. 9
ordenes en vez de 10) pero cuyo precio ya era normal terminaba
"corrigiendose" en centavos sin necesidad, generando ruido en vez de
arreglar algo real.

Uso (desde la raiz del repo, con el venv activado):
    python deploy/fix-binance-p2p-outliers.py            # dry-run, no escribe nada
    python deploy/fix-binance-p2p-outliers.py --apply    # aplica los cambios

Un anunciante confiable (>=10 ordenes, >=80% completado) puede igual publicar
un precio raro alguna vez -- el criterio automatico no lo va a agarrar, a
proposito, para no tocar volatilidad real de mercado en cuentas que si
cumplen. Para esos casos puntuales, revisados y confirmados a mano, se puede
forzar por id (se salta el chequeo de confiabilidad SOLO para esos ids, pero
sigue exigiendo el desvio minimo e interpolando igual que el resto):
    python deploy/fix-binance-p2p-outliers.py --force-id 1683

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

# Un anuncio no confiable cuyo precio ya coincidia con el mercado (ej. 9 ordenes
# en vez de 10, pero el mismo precio que todos los demas) no necesita
# corregirse -- solo los que ademas se alejan de verdad del valor esperado.
MIN_DEVIATION_RATIO = Decimal("0.03")


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


async def main(apply: bool, force_ids: set[int]) -> None:
    settings = get_settings()
    db = Database(settings.database_url)
    collector = EconomicIndicatorCollector()

    changed = 0
    skipped = 0
    seen_force_ids: set[int] = set()

    async with db.session_maker() as session:
        for code in CODES:
            stmt = (
                select(EconomicIndicatorValue)
                .where(EconomicIndicatorValue.indicator_code == code)
                .order_by(EconomicIndicatorValue.collected_at.asc())
            )
            rows = list((await session.execute(stmt)).scalars().all())
            reliable_rows = [
                row for row in rows if is_reliable(collector, row) and row.id not in force_ids
            ]

            for row in rows:
                forced = row.id in force_ids
                if forced:
                    seen_force_ids.add(row.id)
                if is_reliable(collector, row) and not forced:
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

                deviation = abs(new_value - row.value) / row.value if row.value else Decimal(0)
                if deviation <= MIN_DEVIATION_RATIO:
                    reason_text = "forzado a mano pero" if forced else "anunciante no confiable pero"
                    print(
                        f"SIN TOCAR  {code} id={row.id} {row.collected_at}: {row.value} ya esta cerca "
                        f"del esperado {new_value} (desvio {deviation:.2%}, {reason_text} sin impacto real)"
                    )
                    skipped += 1
                    continue

                action = "APLICAR" if apply else "DRY-RUN"
                forced_tag = " [FORZADO]" if forced else ""
                print(f"{action}{forced_tag}   {code} id={row.id} {row.collected_at}: {row.value} -> {new_value}")

                if apply:
                    row.raw_payload = {
                        **(row.raw_payload or {}),
                        "corrected": {
                            "original_value": str(row.value),
                            "reason": "manual_forced_correction" if forced else "unreliable_advertiser_backfill_correction",
                            "corrected_at": datetime.utcnow().isoformat(),
                        },
                    }
                    row.value = new_value
                changed += 1

        if apply:
            await session.commit()
            print(f"\nListo: {changed} corregidos, {skipped} sin tocar (sin vecino confiable o sin desvio real).")
        else:
            print(
                f"\nDRY-RUN: {changed} se corregirian, {skipped} quedarian igual "
                "(sin vecino confiable o sin desvio real). Corre con --apply para aplicar de verdad."
            )

    unmatched = force_ids - seen_force_ids
    if unmatched:
        print(f"\nOJO: estos --force-id no corresponden a ninguna fila de {CODES}: {sorted(unmatched)}")

    await db.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica los cambios de verdad. Sin esta flag solo hace dry-run.",
    )
    parser.add_argument(
        "--force-id",
        action="append",
        type=int,
        default=[],
        dest="force_ids",
        help="Id de fila a corregir aunque su anunciante pase el chequeo de confiabilidad "
        "(revisado a mano). Se puede repetir para varios ids.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.apply, set(args.force_ids)))
