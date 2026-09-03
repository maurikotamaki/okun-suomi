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

    # --- Alkuperäinen spesifikaatio (säilytetty ennallaan) ------------------
    tulos = analyysi.estimoi_okunin_laki(aineisto)
    analyysi.tulosta_tulokset(tulos)

    KUVAT_HAKEMISTO.mkdir(exist_ok=True)
    aikasarja_polku = KUVAT_HAKEMISTO / "aikasarjat.png"
    hajonta_polku = KUVAT_HAKEMISTO / "hajontakuvio.png"

    analyysi.piirra_aikasarjat(aineisto, str(aikasarja_polku))
    analyysi.piirra_hajontakuvio(tulos, str(hajonta_polku))

    print()
    print(f"Kuvat tallennettu: {aikasarja_polku}, {hajonta_polku}")

    # --- Robustisuustarkastelu ----------------------------------------------
    print()
    print("#" * 70)
    print("# ROBUSTISUUSTARKASTELU")
    print("#" * 70)

    # 1) HAC (Newey–West) -keskivirheet, Durbin–Watson ja Breusch–Godfrey
    #    alkuperäiselle (koko aineisto, v/v) spesifikaatiolle.
    perus = analyysi.estimoi_robusti(
        aineisto,
        y_sarake="tyottomyysasteen_muutos",
        x_sarakkeet=["bkt_kasvu"],
        nimi="Koko aineisto (v/v)",
        kasvu_sarake="bkt_kasvu",
        hac_vahimmaisviive=analyysi.NW_VAHIMMAISVIIVE_VV,
    )
    analyysi.tulosta_hac_diagnostiikka(perus)

    # 2) Kolme rinnakkaista otosta samalla v/v-spesifikaatiolla.
    aineisto_ilman_covidia = aineisto[aineisto["covid"] == 0]
    ilman_covidia = analyysi.estimoi_robusti(
        aineisto_ilman_covidia,
        y_sarake="tyottomyysasteen_muutos",
        x_sarakkeet=["bkt_kasvu"],
        nimi="Ilman 2020–2021",
        kasvu_sarake="bkt_kasvu",
        hac_vahimmaisviive=analyysi.NW_VAHIMMAISVIIVE_VV,
    )
    covid_dummy = analyysi.estimoi_robusti(
        aineisto,
        y_sarake="tyottomyysasteen_muutos",
        x_sarakkeet=["bkt_kasvu", "covid"],
        nimi="Covid-dummy mukana",
        kasvu_sarake="bkt_kasvu",
        hac_vahimmaisviive=analyysi.NW_VAHIMMAISVIIVE_VV,
    )
    analyysi.tulosta_kolmen_otoksen_taulukko([perus, ilman_covidia, covid_dummy])

    # 3) Vaihtoehtoinen spesifikaatio: neljännesmuutokset vuosimuutosten
    #    sijaan (kausitasoitettu BKT edellisneljänneksestä ja kausitasoitettu
    #    työttömyysaste, aggregoitu kuukausista neljännekselle).
    print()
    print(
        "Haetaan vaihtoehtoinen aineisto neljännesmuutos-spesifikaatiota "
        "varten (kausitasoitettu BKT: StatFin/ntp/132h.px, kausitasoitettu "
        "työttömyysaste: StatFin/tyti/135z.px) ..."
    )
    try:
        aineisto_qoq = datahaku.hae_ja_yhdista_qoq()
    except RuntimeError as exc:
        print(
            f"VIRHE: neljännesmuutos-aineiston haku epäonnistui: {exc}",
            file=sys.stderr,
        )
        return 1
    print(
        f"  -> {len(aineisto_qoq)} neljännestä "
        f"({aineisto_qoq.index.min()}–{aineisto_qoq.index.max()})"
    )
    print(aineisto_qoq.round(2).head(4).to_string())
    print("...")
    print(aineisto_qoq.round(2).tail(4).to_string())

    qoq = analyysi.estimoi_robusti(
        aineisto_qoq,
        y_sarake="tyottomyysasteen_muutos_qoq",
        x_sarakkeet=["bkt_kasvu_qoq"],
        nimi="Neljännesmuutokset (q/q)",
        kasvu_sarake="bkt_kasvu_qoq",
        hac_vahimmaisviive=analyysi.NW_VAHIMMAISVIIVE_QOQ,
        paallekkaiset_muutokset=False,
    )
    analyysi.tulosta_hac_diagnostiikka(qoq)

    # 4) Kynnyskasvujen (-a/b) yhteenveto kaikista spesifikaatioista.
    print()
    print("=" * 70)
    print("Kynnyskasvu -a/b kaikissa spesifikaatioissa (BKT:n kasvuvauhti,")
    print("jolla työttömyysaste ei muutu)")
    print("=" * 70)
    for nimi, kynnys in [
        ("Alkuperäinen (v/v, OLS)", tulos.kynnyskasvu),
        ("Koko aineisto (v/v, HAC)", perus.kynnyskasvu()),
        ("Ilman 2020–2021 (v/v, HAC)", ilman_covidia.kynnyskasvu()),
        ("Covid-dummy, ei-covid-tila (v/v, HAC)", covid_dummy.kynnyskasvu()),
        ("Neljännesmuutokset (q/q, HAC)", qoq.kynnyskasvu()),
    ]:
        print(f"  {nimi:<42}{kynnys:>8.3f} %")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
