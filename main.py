"""Aja koko putki: hae data Tilastokeskuksen PxWeb-rajapinnasta, estimoi
Okunin laki ja piirrä kuvat.

Käyttö:
    python main.py

Katso README.md tarkemmat ajo-ohjeet ja riippuvuuksien asennus.
"""

from __future__ import annotations

import sys
from pathlib import Path

from okun_suomi import analyysi, datahaku

KUVAT_HAKEMISTO = Path(__file__).resolve().parent / "kuvat"


def main() -> int:
    print("Haetaan BKT:n volyymin kasvu (StatFin/ntp/132h.px) ...")
    try:
        bkt = datahaku.hae_bkt_kasvu()
    except RuntimeError as exc:
        print(f"VIRHE: BKT-datan haku epäonnistui: {exc}", file=sys.stderr)
        return 1
    print(
        f"  -> {len(bkt)} havaintoa, {bkt.index.min()}–{bkt.index.max()}"
    )

    print("Haetaan työttömyysaste (StatFin/tyti/137h.px) ...")
    try:
        tyottomyys = datahaku.hae_tyottomyysaste()
    except RuntimeError as exc:
        print(f"VIRHE: työttömyysasteen haku epäonnistui: {exc}", file=sys.stderr)
        return 1
    print(
        f"  -> {len(tyottomyys)} havaintoa, "
        f"{tyottomyys.index.min()}–{tyottomyys.index.max()}"
    )

    print()
    print("Yhdistetään sarjat (työttömyysasteesta lasketaan vuosimuutos)...")
    try:
        aineisto = datahaku.hae_ja_yhdista()
    except RuntimeError as exc:
        print(f"VIRHE: aineiston yhdistäminen epäonnistui: {exc}", file=sys.stderr)
        return 1

    print(
        f"Lopullinen, yhtenäinen aineisto: {len(aineisto)} neljännestä "
        f"({aineisto.index.min()}–{aineisto.index.max()})"
    )
    print()
    print("Ensimmäiset ja viimeiset rivit yhdistetystä aineistosta:")
    with_pandas_options = aineisto.round(2)
    print(with_pandas_options.head(5).to_string())
    print("...")
    print(with_pandas_options.tail(5).to_string())
    print()

    tulos = analyysi.estimoi_okunin_laki(aineisto)
    analyysi.tulosta_tulokset(tulos)

    KUVAT_HAKEMISTO.mkdir(exist_ok=True)
    aikasarja_polku = KUVAT_HAKEMISTO / "aikasarjat.png"
    hajonta_polku = KUVAT_HAKEMISTO / "hajontakuvio.png"

    analyysi.piirra_aikasarjat(aineisto, str(aikasarja_polku))
    analyysi.piirra_hajontakuvio(tulos, str(hajonta_polku))

    print()
    print(f"Kuvat tallennettu: {aikasarja_polku}, {hajonta_polku}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
