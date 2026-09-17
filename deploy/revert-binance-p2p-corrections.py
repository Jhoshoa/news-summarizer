"""One-off: revierte las correcciones aplicadas por fix-binance-p2p-outliers.py.

Cada fila que ese script corrige queda marcada con
raw_payload.corrected.original_value (ver fix-binance-p2p-outliers.py) --
este script busca esas filas y les devuelve ese valor original. Deja un
rastro de que se revirtio (raw_payload.reverted_correction) en vez de borrar
la historia sin dejar nada.

Uso (desde la raiz del repo, con el venv activado):
    python deploy/revert-binance-p2p-corrections.py            # dry-run
    python deploy/revert-binance-p2p-corrections.py --apply    # revierte de verdad
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from src.config import get_settings
from src.db.indicators import EconomicIndicatorValue
from src.db.repository import Database

CODES = ["binance_p2p_usdt_bob_buy", "binance_p2p_usdt_bob_sell"]


async def main(apply: bool) -> None:
    settings = get_settings()
    db = Database(settings.database_url)

    reverted = 0

    async with db.session_maker() as session:
        for code in CODES:
            stmt = select(EconomicIndicatorValue).where(EconomicIndicatorValue.indicator_code == code)
            rows = list((await session.execute(stmt)).scalars().all())

            for row in rows:
                correction = (row.raw_payload or {}).get("corrected")
                if not correction:
                    continue

                original_value = Decimal(str(correction["original_value"]))
                action = "APLICAR" if apply else "DRY-RUN"
                print(
                    f"{action}   {code} id={row.id} {row.collected_at}: "
                    f"{row.value} -> {original_value} (revirtiendo correccion)"
                )

                if apply:
                    remaining_payload = {
                        key: value for key, value in (row.raw_payload or {}).items() if key != "corrected"
                    }
                    row.raw_payload = {
                        **remaining_payload,
                        "reverted_correction": {
                            **correction,
                            "reverted_at": datetime.utcnow().isoformat(),
                        },
                    }
                    row.value = original_value
                reverted += 1

        if apply:
            await session.commit()
            print(f"\nListo: {reverted} filas revertidas a su valor original.")
        else:
            print(f"\nDRY-RUN: {reverted} se revertirian. Corre con --apply para aplicar de verdad.")

    await db.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica la reversion de verdad. Sin esta flag solo hace dry-run.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.apply))
