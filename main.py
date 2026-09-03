"""Aja koko putki: hae data Tilastokeskuksen PxWeb-rajapinnasta, estimoi
Okunin laki ja piirrä kuvat.

Käyttö:
    python main.py

Katso README.md tarkemmat ajo-ohjeet ja riippuvuuksien asennus.
"""

from __future__ import annotations

import sys
from pathlib import Path

from okun_suomi import analyysi, datahaku, raportti

KUVAT_HAKEMISTO = Path(__file__).resolve().parent / "kuvat"
TULOKSET_POLKU = Path(__file__).resolve().parent / "tulokset.md"


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

    # Markdown-lohkot kootaan samassa järjestyksessä kuin konsolitulostus,
    # ja kirjoitetaan lopuksi tulokset.md-tiedostoon (ks. main()-funktion
    # loppu).
    md_osat: list[str] = []

    # --- Alkuperäinen spesifikaatio (säilytetty ennallaan) ------------------
    tulos = analyysi.estimoi_okunin_laki(aineisto)
    analyysi.tulosta_tulokset(tulos)
    md_osat.append(raportti.md_alkuperainen(tulos))

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
    md_osat.append("## 2. Robustisuustarkastelu\n")

    # 1) OLS/Newey–West/Andrews–Monahan-keskivirheet, Durbin–Watson ja
    #    Breusch–Godfrey alkuperäiselle (koko aineisto, v/v) spesifikaatiolle.
    perus = analyysi.estimoi_robusti(
        aineisto,
        y_sarake="tyottomyysasteen_muutos",
        x_sarakkeet=["bkt_kasvu"],
        nimi="Koko aineisto (v/v)",
        kasvu_sarakkeet=["bkt_kasvu"],
        yksikko="v/v",
        nw_vahimmaisviive=analyysi.NW_VAHIMMAISVIIVE_VV,
    )
    analyysi.tulosta_hac_diagnostiikka(perus)
    md_osat.append(raportti.md_hac_taulukko(perus, otsikon_etuliite="2.1 "))

    # 2) Kolme rinnakkaista otosta samalla v/v-spesifikaatiolla.
    aineisto_ilman_covidia = aineisto[aineisto["covid"] == 0]
    ilman_covidia = analyysi.estimoi_robusti(
        aineisto_ilman_covidia,
        y_sarake="tyottomyysasteen_muutos",
        x_sarakkeet=["bkt_kasvu"],
        nimi="Ilman 2020–2021",
        kasvu_sarakkeet=["bkt_kasvu"],
        yksikko="v/v",
        nw_vahimmaisviive=analyysi.NW_VAHIMMAISVIIVE_VV,
    )
    covid_dummy = analyysi.estimoi_robusti(
        aineisto,
        y_sarake="tyottomyysasteen_muutos",
        x_sarakkeet=["bkt_kasvu", "covid"],
        nimi="Covid-dummy mukana",
        kasvu_sarakkeet=["bkt_kasvu"],
        yksikko="v/v",
        nw_vahimmaisviive=analyysi.NW_VAHIMMAISVIIVE_VV,
    )
    analyysi.tulosta_kolmen_otoksen_taulukko([perus, ilman_covidia, covid_dummy])
    md_osat.append(raportti.md_kolmen_otoksen_taulukko([perus, ilman_covidia, covid_dummy]))

    # 3) Vaihtoehtoinen spesifikaatio: neljännesmuutokset vuosimuutosten
    #    sijaan (kausitasoitettu BKT edellisneljänneksestä ja kausitasoitettu
    #    työttömyysaste, aggregoitu kuukausista neljännekselle), BKT-kasvun
    #    viiveillä 0–4 neljännestä.
    print()
    print(
        "Haetaan vaihtoehtoinen aineisto neljännesmuutos-spesifikaatiota "
        "varten (kausitasoitettu BKT: StatFin/ntp/132h.px, kausitasoitettu "
        "työttömyysaste: StatFin/tyti/135z.px), BKT-kasvun viiveillä 0-4 ..."
    )

    # Varmistetaan PxWeb-metatiedoista (ajonaikaisesti, ei vain koodin
    # nimen perusteella), että molemmat q/q-sarjat ovat todella
    # kausitasoitettuja, ja tulostetaan mikä sarja valittiin kummallekin
    # muuttujalle.
    try:
        kausitasoitus = datahaku.varmista_qoq_kausitasoitus()
    except RuntimeError as exc:
        print(f"VIRHE: kausitasoituksen varmistus epäonnistui: {exc}", file=sys.stderr)
        return 1
    print("Kausitasoituksen varmistus PxWeb-metatiedoista:")
    for nimi, (taulukko, koodi, selite) in kausitasoitus.items():
        print(f"  {nimi}:")
        print(f"    taulukko: {taulukko}")
        print(f"    sisältökoodi: {koodi!r}")
        print(f"    PxWeb-selite: {selite!r}")
    md_osat.append(raportti.md_kausitasoitus(kausitasoitus))

    VIIVEET_QOQ = 4
    try:
        aineisto_qoq = datahaku.hae_ja_yhdista_qoq(maksimiviive=VIIVEET_QOQ)
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

    qoq_sarakkeet = [f"bkt_kasvu_qoq_L{i}" for i in range(VIIVEET_QOQ + 1)]
    qoq = analyysi.estimoi_robusti(
        aineisto_qoq,
        y_sarake="tyottomyysasteen_muutos_qoq",
        x_sarakkeet=qoq_sarakkeet,
        nimi=f"Neljännesmuutokset, viiveet 0-{VIIVEET_QOQ} (q/q)",
        kasvu_sarakkeet=qoq_sarakkeet,
        yksikko="q/q",
        nw_vahimmaisviive=analyysi.NW_VAHIMMAISVIIVE_QOQ,
    )
    analyysi.tulosta_hac_diagnostiikka(qoq)
    md_osat.append(raportti.md_hac_taulukko(qoq, otsikon_etuliite="2.4 "))

    # 3b) Jäännösten kausivaihtelutesti viivemallille: jos kausitasoitus
    #     ei ole täydellinen, kausidummyt (Q2-Q4 vs. Q1) näkyisivät
    #     merkitsevinä jäännöksissä — mahdollinen selitys sille, että
    #     yksittäiset viivekertoimet (esim. L4) poikkeavat naapureistaan.
    kausivaihtelutesti = analyysi.testaa_jaannosten_kausivaihtelu(qoq)
    nimi_qoq = f"Neljännesmuutokset, viiveet 0-{VIIVEET_QOQ} (q/q)"
    analyysi.tulosta_kausivaihtelutesti(kausivaihtelutesti, nimi=nimi_qoq)
    md_osat.append(raportti.md_kausivaihtelutesti(kausivaihtelutesti, nimi=nimi_qoq))

    # 4) Kynnyskasvun yhteenveto kaikista spesifikaatioista, annualisoituna
    #    samaan (%/vuosi) yksikköön, jotta v/v- ja q/q-mallit ovat suoraan
    #    vertailukelpoisia.
    kynnyskasvu_yhteenveto = [
        ("Alkuperäinen (v/v, OLS, ei-robusti)", tulos.kynnyskasvu, "v/v"),
        ("Koko aineisto (v/v, konservatiivinen HAC)", perus.kynnyskasvu(), "v/v"),
        (
            "Ilman 2020–2021 (v/v, konservatiivinen HAC)",
            ilman_covidia.kynnyskasvu(),
            "v/v",
        ),
        (
            "Covid-dummy, ei-covid-tila (v/v, konservatiivinen HAC)",
            covid_dummy.kynnyskasvu(),
            "v/v",
        ),
        (
            f"Neljännesmuutokset, Σb viiveille 0-{VIIVEET_QOQ} (q/q, konservatiivinen HAC)",
            qoq.kynnyskasvu(),
            "q/q",
        ),
    ]
    analyysi.tulosta_kynnyskasvu_yhteenveto(kynnyskasvu_yhteenveto)
    md_osat.append(raportti.md_kynnyskasvu_yhteenveto(kynnyskasvu_yhteenveto))

    # --- Tulosten kirjoitus versionhallittavaan tulokset.md-tiedostoon ------
    raportti.kirjoita_tulokset_md(
        TULOKSET_POLKU,
        v_v_viimeinen_havainto=str(aineisto.index.max()),
        q_q_viimeinen_havainto=str(aineisto_qoq.index.max()),
        osat=md_osat,
    )
    print()
    print(f"Tulokset kirjoitettu: {TULOKSET_POLKU}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
