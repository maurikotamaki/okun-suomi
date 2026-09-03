"""Analyysin tulosten kirjoittaminen versionhallittavaan Markdown-muotoon.

Tämä moduuli ei laske mitään itse — se ainoastaan muotoilee
``analyysi``-moduulin jo estimoimat tulosoliot (``OkuninLainTulos``,
``RobustiTulos``, ``KausivaihteluTesti``) Markdown-taulukoiksi ja
kokoaa niistä yhden ``tulokset.md``-tiedoston, jonka ``main.py``
kirjoittaa jokaisen ajon lopuksi. Tiedosto on tarkoitettu committoitavaksi
versionhallintaan, jotta tulosten muutokset (esim. Tilastokeskuksen
datapäivitysten myötä) näkyvät diffinä.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from . import analyysi


def _otsikko(teksti: str, taso: int = 2) -> str:
    return f"{'#' * taso} {teksti}\n"


def md_alkuperainen(tulos: analyysi.OkuninLainTulos) -> str:
    """Markdown-taulukko alkuperäiselle (v/v, ei-robusti OLS) spesifikaatiolle."""
    rivit = [
        _otsikko("1. Alkuperäinen spesifikaatio (v/v, OLS)"),
        "Malli: `Δtyöttömyysaste_t = a + b · BKT_kasvu_t + e_t` "
        "(Δtyöttömyysaste = muutos vuodentakaisesta, %-yks.; "
        "BKT_kasvu = volyymin muutos vuodentakaisesta, %)\n",
        f"Aikaväli: {tulos.aineisto.index.min()} – {tulos.aineisto.index.max()}  "
        f"N = {tulos.havaintojen_maara}\n",
        "| Termi | Kerroin | Keskivirhe | t-arvo | p-arvo |",
        "|---|---:|---:|---:|---:|",
        (
            f"| Vakio (a) | {tulos.vakiotermi:.4f} | {tulos.vakiotermin_keskivirhe:.4f} | "
            f"{tulos.malli.tvalues['const']:.3f} | {tulos.malli.pvalues['const']:.4f} |"
        ),
        (
            f"| BKT-kasvu (b) | {tulos.kerroin:.4f} | {tulos.kertoimen_keskivirhe:.4f} | "
            f"{tulos.malli.tvalues['bkt_kasvu']:.3f} | {tulos.malli.pvalues['bkt_kasvu']:.4f} |"
        ),
        "",
        f"- Selitysaste R²: {tulos.selitysaste:.4f}",
        f"- Kynnyskasvu -a/b: **{tulos.kynnyskasvu:.3f} %/vuosi** "
        "(BKT:n kasvuvauhti, jolla työttömyysaste ei muutu)",
        "",
    ]
    return "\n".join(rivit)


def md_hac_taulukko(
    tulos: analyysi.RobustiTulos, otsikkotaso: int = 3, otsikon_etuliite: str = ""
) -> str:
    """Markdown-taulukko: kerroin + OLS/NW/AM-keskivirheet, N/df,
    autokorrelaatiodiagnostiikka ja kynnyskasvu yhdelle ``RobustiTulos``-
    mallille (kelpaa niin v/v- kuin q/q-viivemalleille).

    ``otsikon_etuliite`` (esim. ``"2.1 "``) lisätään otsikon eteen, jotta
    tiedoston jaksonumerointi pysyy juoksevana."""
    rivit = [_otsikko(f"{otsikon_etuliite}{tulos.nimi}", otsikkotaso)]

    k_params = len(tulos.param_nimet)
    df_resid = tulos.nobs - k_params
    rivit.append(
        f"N = {tulos.nobs}, selittäjiä (vakio mukaan lukien) k = {k_params}, "
        f"vapausasteet df_resid = N-k = {df_resid}\n"
    )

    rivit.append("| Termi | Kerroin | OLS-SE | NW-SE | AM-SE (esivalk.) |")
    rivit.append("|---|---:|---:|---:|---:|")
    ols_bse = tulos.bse("ols")
    nw_bse = tulos.bse("nw")
    pw_bse = tulos.bse("pw")
    for termi in tulos.param_nimet:
        rivit.append(
            f"| {termi} | {tulos.params[termi]:.4f} | {ols_bse[termi]:.4f} | "
            f"{nw_bse[termi]:.4f} | {pw_bse[termi]:.4f} |"
        )
    rivit.append("")

    rivit.append(
        f"- Newey–West-viiveet L = {tulos.nw_viiveet}; "
        f"Andrews–Monahan-esivalkaisun jälkeiset viiveet L = {tulos.pw_viiveet}"
    )
    rivit.append(
        f"- Päätulokseksi valittu (konservatiivisin): "
        f"**{analyysi.KOVARIANSSI_NIMET[tulos.paa_nimi]}** (suurempi SE kahdesta "
        "HAC-vaihtoehdosta BKT-kasvun kokonaisvaikutukselle)"
    )
    rivit.append(
        f"- Durbin–Watson: {tulos.dw:.3f} (2.0 = ei autokorrelaatiota; <2 → positiivinen)"
    )
    rivit.append(
        f"- Breusch–Godfrey (L={tulos.bg_viiveet}): LM={tulos.bg_lm:.3f}, "
        f"p={tulos.bg_lm_p:.4f} (H0: ei jäljellä olevaa autokorrelaatiota)"
    )

    if len(tulos.kasvu_sarakkeet) > 1:
        vaikutus, se, t_arvo, p_arvo = tulos.pitkan_aikavalin_vaikutus("konservatiivinen")
        rivit.append(
            f"- BKT-kasvun pitkän aikavälin vaikutus (Σb, {len(tulos.kasvu_sarakkeet)} "
            f"viivettä, {analyysi.KOVARIANSSI_NIMET[tulos.paa_nimi]}-SE): "
            f"Σb = {vaikutus:.4f}, SE = {se:.4f}, t = {t_arvo:.3f}, p = {p_arvo:.4f}"
        )
        f_arvo, p_yhdessa, df1, df2 = tulos.yhteismerkitsevyys("konservatiivinen")
        rivit.append(
            f"- Viiveiden yhteismerkitsevyys (Wald F, H0: kaikki BKT-viiveiden "
            f"kertoimet = 0): F({df1},{df2}) = {f_arvo:.3f}, p = {p_yhdessa:.4f}"
        )

    kynnys = tulos.kynnyskasvu("konservatiivinen")
    kynnys_v = tulos.kynnyskasvu_vuositasolla("konservatiivinen")
    if tulos.yksikko == "q/q":
        rivit.append(
            f"- Kynnyskasvu -a/Σb: {kynnys:.3f} %/neljännes → annualisoituna "
            f"**{kynnys_v:.3f} %/vuosi**"
        )
    else:
        rivit.append(f"- Kynnyskasvu -a/Σb: **{kynnys_v:.3f} %/vuosi**")
    rivit.append("")
    return "\n".join(rivit)


def md_kolmen_otoksen_taulukko(tulokset: Sequence[analyysi.RobustiTulos]) -> str:
    rivit = [
        _otsikko("2.2 Otosvertailu: koko aineisto / ilman 2020–2021 / covid-dummy", 3),
        "Keskivirheet ovat kunkin mallin konservatiivisimman HAC-vaihtoehdon "
        "mukaisia (suluissa on keskivirhe kertoimen jälkeen); -a/Σb on annualisoitu.\n",
        "| Malli | Vakio a (SE) | BKT-kerroin b (SE) | Covid-dummy (SE) | R² | N | -a/Σb, %/v |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for t in tulokset:
        a = t.params["const"]
        _, a_se, _, _ = t.kertoimen_tilastot("const")
        b_sarake = t.kasvu_sarakkeet[0]
        b = t.params[b_sarake]
        _, b_se, _, _ = t.kertoimen_tilastot(b_sarake)
        if "covid" in t.param_nimet:
            c = t.params["covid"]
            _, c_se, _, _ = t.kertoimen_tilastot("covid")
            covid_str = f"{c:.3f} ({c_se:.3f})"
        else:
            covid_str = "–"
        rivit.append(
            f"| {t.nimi} | {a:.3f} ({a_se:.3f}) | {b:.3f} ({b_se:.3f}) | "
            f"{covid_str} | {t.rsquared:.4f} | {t.nobs} | "
            f"{t.kynnyskasvu_vuositasolla('konservatiivinen'):.3f} |"
        )
    rivit.append("")
    return "\n".join(rivit)


def md_kausitasoitus(kausitasoitus: dict[str, tuple[str, str, str]]) -> str:
    rivit = [
        _otsikko("2.3 Kausitasoituksen varmistus (q/q-sarjat)", 3),
        "PxWeb-metatiedoista (GET-pyyntö taulukon metatietoihin ajon "
        "aikana) haettu ja tarkistettu, että kummankin sarjan selite "
        "mainitsee kausitasoituksen.\n",
        "| Muuttuja | Taulukko | Sisältökoodi | PxWeb-selite |",
        "|---|---|---|---|",
    ]
    for nimi, (taulukko, koodi, selite) in kausitasoitus.items():
        rivit.append(f"| {nimi} | `{taulukko}` | `{koodi}` | {selite} |")
    rivit.append("")
    return "\n".join(rivit)


def md_kausivaihtelutesti(testi: analyysi.KausivaihteluTesti, nimi: str) -> str:
    rivit = [
        _otsikko("2.5 Jäännösten kausivaihtelutesti", 3),
        f"Malli: {nimi}. Apuregressio: OLS-jäännös ~ vakio + Q2 + Q3 + Q4 "
        "(Q1 = referenssi).\n",
        "| Termi | Kerroin | SE | t | p |",
        "|---|---:|---:|---:|---:|",
    ]
    for termi in testi.apumalli.params.index:
        rivit.append(
            f"| {termi} | {testi.apumalli.params[termi]:.4f} | "
            f"{testi.apumalli.bse[termi]:.4f} | {testi.apumalli.tvalues[termi]:.3f} | "
            f"{testi.apumalli.pvalues[termi]:.4f} |"
        )
    rivit.append("")
    rivit.append(
        f"Yhteismerkitsevyys (F-testi, H0: ei kausivaihtelua jäännöksissä): "
        f"F({testi.df_osoittaja},{testi.df_nimittaja}) = {testi.f_arvo:.3f}, "
        f"p = {testi.f_p:.4f}"
    )
    if testi.f_p < 0.05:
        rivit.append(
            "\n**p < 0.05: jäännöksissä ON viitteitä jäljellä olevasta "
            "kausivaihtelusta** huolimatta kausitasoituksesta."
        )
    else:
        rivit.append(
            "\n**p ≥ 0.05: ei tilastollista näyttöä jäljellä olevasta "
            "kausivaihtelusta** jäännöksissä."
        )
    rivit.append("")
    return "\n".join(rivit)


def md_kynnyskasvu_yhteenveto(tulokset: Sequence[tuple[str, float, str]]) -> str:
    rivit = [
        _otsikko("3. Kynnyskasvu -a/Σb kaikissa spesifikaatioissa, annualisoituna"),
        "BKT:n kasvuvauhti (%/vuosi), jolla työttömyysaste ei muutu. "
        "q/q-mallien neljänneskohtainen kynnys annualisoidaan korkoa "
        "korolle -periaatteella `(1+g/100)^4 - 1`.\n",
        "| Spesifikaatio | Alkuperäinen yksikkö | Kynnyskasvu, %/vuosi |",
        "|---|---|---:|",
    ]
    for nimi, kynnys_oma, yksikko in tulokset:
        kynnys_v = analyysi.annualisoi_kynnyskasvu(kynnys_oma, yksikko)
        rivit.append(f"| {nimi} | {yksikko} | {kynnys_v:.3f} |")
    rivit.append("")
    return "\n".join(rivit)


def kirjoita_tulokset_md(
    polku: Path,
    *,
    v_v_viimeinen_havainto: str,
    q_q_viimeinen_havainto: str,
    osat: Sequence[str],
) -> None:
    """Kokoaa ja kirjoittaa ``tulokset.md``-tiedoston.

    Alkuun merkitään ajon UTC-aikaleima ja käytetyn datan viimeinen
    havainto (erikseen v/v- ja q/q-aineistolle, koska ne voivat
    periaatteessa poiketa toisistaan). Loppuosa on ``osat``-parametrissa
    valmiiksi koottuja Markdown-lohkoja (ks. tämän moduulin muut
    md_*-funktiot).
    """
    ajopaiva = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    header = [
        "# Okunin lain analyysin tulokset — Suomi",
        "",
        f"- **Ajettu:** {ajopaiva}",
        f"- **Datan viimeinen havainto (v/v-aineisto):** {v_v_viimeinen_havainto}",
        f"- **Datan viimeinen havainto (q/q-aineisto):** {q_q_viimeinen_havainto}",
        "- **Lähde:** Tilastokeskuksen PxWeb-rajapinta (StatFin), haettu "
        "ajonaikaisesti — ei kovakoodattua tai simuloitua dataa.",
        "- Tämä tiedosto on generoitu automaattisesti komennolla `python "
        "main.py` (ks. `okun_suomi/raportti.py`). Älä muokkaa käsin — "
        "muutokset ylikirjoittuvat seuraavalla ajolla. Committoi tiedosto "
        "versionhallintaan, jotta tulosten muutokset näkyvät diffinä.",
        "",
        "---",
        "",
    ]
    sisalto = "\n".join(header) + "\n".join(osat)
    polku.write_text(sisalto, encoding="utf-8")
