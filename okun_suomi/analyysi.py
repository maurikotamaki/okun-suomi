"""Okunin lain estimointi ja tulosten visualisointi.

Okunin laki muotoillaan tässä perinteiseen "muutosten" (difference) muotoon:

    Δu_t = a + b * g_t + e_t

jossa
    Δu_t = työttömyysasteen muutos vuodentakaisesta (prosenttiyksikköä)
    g_t  = BKT:n volyymin kasvu vuodentakaisesta (%)

Okunin lain mukaan kerroin ``b`` on negatiivinen: kun talouskasvu
kiihtyy, työttömyysasteen muutos hidastuu (tai kääntyy laskuun).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import acorr_breusch_godfrey
from statsmodels.stats.stattools import durbin_watson


@dataclass
class OkuninLainTulos:
    """Tiivistetty säiliö regressiotuloksille."""

    malli: sm.regression.linear_model.RegressionResultsWrapper
    aineisto: pd.DataFrame

    @property
    def vakiotermi(self) -> float:
        return self.malli.params["const"]

    @property
    def vakiotermin_keskivirhe(self) -> float:
        return self.malli.bse["const"]

    @property
    def kerroin(self) -> float:
        return self.malli.params["bkt_kasvu"]

    @property
    def kertoimen_keskivirhe(self) -> float:
        return self.malli.bse["bkt_kasvu"]

    @property
    def selitysaste(self) -> float:
        return self.malli.rsquared

    @property
    def havaintojen_maara(self) -> int:
        return int(self.malli.nobs)

    @property
    def kynnyskasvu(self) -> float:
        """Kynnyskasvu -a/b: BKT:n kasvuvauhti, jolla työttömyysaste ei
        muutu (Δu = 0), mallin pistesuureiden mukaan."""
        return -self.vakiotermi / self.kerroin


def estimoi_okunin_laki(aineisto: pd.DataFrame) -> OkuninLainTulos:
    """Estimoi OLS-regression: tyottomyysasteen_muutos ~ bkt_kasvu."""
    y = aineisto["tyottomyysasteen_muutos"]
    x = sm.add_constant(aineisto["bkt_kasvu"])
    malli = sm.OLS(y, x).fit()
    return OkuninLainTulos(malli=malli, aineisto=aineisto)


def tulosta_tulokset(tulos: OkuninLainTulos) -> None:
    """Tulostaa regressiotulokset ihmisluettavassa muodossa."""
    print("=" * 70)
    print("Okunin lain estimointi Suomen aineistolla")
    print("=" * 70)
    ensimmainen = tulos.aineisto.index.min()
    viimeinen = tulos.aineisto.index.max()
    print(f"Aikaväli:        {ensimmainen} – {viimeinen}")
    print(f"Havaintoja (N):  {tulos.havaintojen_maara}")
    print()
    print("Malli: Δtyöttömyysaste_t = a + b * BKT_kasvu_t + e_t")
    print("(Δtyöttömyysaste = muutos vuodentakaisesta, %-yks.;")
    print(" BKT_kasvu = volyymin muutos vuodentakaisesta, %)")
    print()
    print(f"{'Termi':<15}{'Kerroin':>12}{'Keskivirhe':>14}{'t-arvo':>10}{'p-arvo':>10}")
    print("-" * 70)
    print(
        f"{'Vakio (a)':<15}{tulos.vakiotermi:>12.4f}"
        f"{tulos.vakiotermin_keskivirhe:>14.4f}"
        f"{tulos.malli.tvalues['const']:>10.3f}"
        f"{tulos.malli.pvalues['const']:>10.4f}"
    )
    print(
        f"{'BKT-kasvu (b)':<15}{tulos.kerroin:>12.4f}"
        f"{tulos.kertoimen_keskivirhe:>14.4f}"
        f"{tulos.malli.tvalues['bkt_kasvu']:>10.3f}"
        f"{tulos.malli.pvalues['bkt_kasvu']:>10.4f}"
    )
    print("-" * 70)
    print(f"Selitysaste R²:  {tulos.selitysaste:.4f}")
    print(
        f"Kynnyskasvu -a/b:{tulos.kynnyskasvu:>9.3f} % "
        "(BKT:n kasvuvauhti, jolla työttömyysaste ei muutu)"
    )
    print("=" * 70)


# ---------------------------------------------------------------------------
# Robustisuustarkastelu
#
# Tämä osa TÄYDENTÄÄ yllä olevaa alkuperäistä spesifikaatiota, ei korvaa
# sitä: samat funktiot (estimoi_okunin_laki/tulosta_tulokset) toimivat
# ennallaan, ja main.py ajaa molemmat.
#
# Vuosimuutoksiin (v/v) perustuva Δu_t = u_t - u_{t-4} on peräkkäisillä
# neljänneksillä päällekkäinen (t ja t-1 jakavat kolme neljästä termistä),
# mikä synnyttää mekaanisesti MA(3)-tyyppisen autokorrelaation jäännöksiin
# (ks. esim. Hodrick 1992). Tavanomaiset OLS-keskivirheet aliarvioivat siksi
# epävarmuuden, ja niiden tilalle/rinnalle lasketaan Newey–West (HAC)
# -keskivirheet, joissa viiveiden lukumäärä on vähintään 4.
# ---------------------------------------------------------------------------

NW_VAHIMMAISVIIVE_VV = 4  # v/v-erotusten päällekkäisyyden takia (MA(3))
NW_VAHIMMAISVIIVE_QOQ = 1  # neljännesmuutoksissa ei rakenteellista päällekkäisyyttä


def newey_west_viiveet(havaintoja: int, vahimmaisviive: int = 1) -> int:
    """Newey–Westin (1994) nyrkkisääntö viiveiden lukumäärälle,
    floor(4*(T/100)^(2/9)), rajattuna alhaalta parametrilla ``vahimmaisviive``.
    """
    nyrkkisaanto = int(np.floor(4 * (havaintoja / 100) ** (2 / 9)))
    return max(vahimmaisviive, nyrkkisaanto, 1)


@dataclass
class RobustiTulos:
    """OLS-malli täydennettynä HAC-keskivirheillä ja autokorrelaatio-
    diagnostiikalla (Durbin–Watson, Breusch–Godfrey)."""

    nimi: str
    y_sarake: str
    kasvu_sarake: str
    ols: sm.regression.linear_model.RegressionResultsWrapper
    hac: sm.regression.linear_model.RegressionResultsWrapper
    hac_viiveet: int
    dw: float
    bg_lm: float
    bg_lm_p: float
    bg_viiveet: int
    paallekkaiset_muutokset: bool = True

    @property
    def params(self) -> pd.Series:
        return self.ols.params

    @property
    def rsquared(self) -> float:
        return self.ols.rsquared

    @property
    def nobs(self) -> int:
        return int(self.ols.nobs)

    def kynnyskasvu(self) -> float:
        return -self.params["const"] / self.params[self.kasvu_sarake]


def estimoi_robusti(
    aineisto: pd.DataFrame,
    y_sarake: str,
    x_sarakkeet: Sequence[str],
    nimi: str,
    kasvu_sarake: str,
    hac_vahimmaisviive: int = NW_VAHIMMAISVIIVE_VV,
    bg_viiveet: int | None = None,
    paallekkaiset_muutokset: bool = True,
) -> RobustiTulos:
    """Estimoi OLS:n ja täydentää sen HAC (Newey–West) -keskivirheillä sekä
    Durbin–Watson- ja Breusch–Godfrey-testeillä.

    ``x_sarakkeet`` voi sisältää useamman selittäjän (esim. BKT-kasvun ja
    covid-dummyn); ``kasvu_sarake`` kertoo, mikä niistä on BKT-kasvu-
    muuttuja, jota käytetään kynnyskasvun (-a/b) laskennassa.
    """
    y = aineisto[y_sarake]
    x = sm.add_constant(aineisto[list(x_sarakkeet)])

    ols = sm.OLS(y, x).fit()
    hac_viiveet = newey_west_viiveet(int(ols.nobs), vahimmaisviive=hac_vahimmaisviive)
    hac = sm.OLS(y, x).fit(
        cov_type="HAC", cov_kwds={"maxlags": hac_viiveet, "use_correction": True}
    )

    dw = float(durbin_watson(ols.resid))

    bg_L = bg_viiveet if bg_viiveet is not None else hac_viiveet
    with warnings.catch_warnings():
        # Vanhempi/uudempi statsmodels palauttaa joko plain tuplen tai
        # LMTestResult-nimikkeistön riippuen versiosta ja result_object-
        # parametrista; plain tuple -paluuarvo riittää tähän, joten
        # FutureWarning vaimennetaan tässä.
        warnings.simplefilter("ignore", FutureWarning)
        bg_lm, bg_lm_p, _bg_f, _bg_f_p = acorr_breusch_godfrey(ols, nlags=bg_L)

    return RobustiTulos(
        nimi=nimi,
        y_sarake=y_sarake,
        kasvu_sarake=kasvu_sarake,
        ols=ols,
        hac=hac,
        hac_viiveet=hac_viiveet,
        dw=dw,
        bg_lm=float(bg_lm),
        bg_lm_p=float(bg_lm_p),
        bg_viiveet=bg_L,
        paallekkaiset_muutokset=paallekkaiset_muutokset,
    )


def tulosta_hac_diagnostiikka(tulos: RobustiTulos) -> None:
    """Tulostaa HAC (Newey–West) -keskivirheet sekä DW- ja BG-testit
    alkuperäisen (tavallisen OLS:n) rinnalle."""
    print()
    print("-" * 70)
    print(f"Robustisuus: {tulos.nimi}")
    syy = (
        "korjaa autokorrelaation, joka syntyy päällekkäisistä vuosimuutoksista"
        if tulos.paallekkaiset_muutokset
        else "varmistaa keskivirheet myös jäljelle jäävän jäännösautokorrelaation varalta"
    )
    print(f"HAC (Newey–West) -keskivirheet, viiveitä L={tulos.hac_viiveet} ({syy})")
    print("-" * 70)
    print(f"{'Termi':<15}{'Kerroin':>12}{'OLS-SE':>12}{'HAC-SE':>12}{'HAC t':>10}{'HAC p':>10}")
    for termi in tulos.params.index:
        print(
            f"{termi:<15}{tulos.params[termi]:>12.4f}"
            f"{tulos.ols.bse[termi]:>12.4f}"
            f"{tulos.hac.bse[termi]:>12.4f}"
            f"{tulos.hac.tvalues[termi]:>10.3f}"
            f"{tulos.hac.pvalues[termi]:>10.4f}"
        )
    print("-" * 70)
    print(
        f"Durbin–Watson:             {tulos.dw:.3f}  "
        "(2.0 = ei autokorrelaatiota; <2 viittaa positiiviseen)"
    )
    print(
        f"Breusch–Godfrey (L={tulos.bg_viiveet}):  LM={tulos.bg_lm:.3f}, "
        f"p={tulos.bg_lm_p:.4f}  "
        "(H0: ei jäljellä olevaa autokorrelaatiota jäännöksissä)"
    )
    print(f"Kynnyskasvu -a/b:          {tulos.kynnyskasvu():.3f} %")


def tulosta_kolmen_otoksen_taulukko(tulokset: Sequence[RobustiTulos]) -> None:
    """Tulostaa rinnakkaisvertailun (kertoimet, HAC-keskivirheet, R²,
    kynnyskasvu) kolmesta (tai useammasta) mallista yhtenä taulukkona."""
    print()
    print("=" * 100)
    print("Otosvertailu: koko aineisto / ilman 2020–2021 / covid-dummy mukana")
    print("(keskivirheet ovat HAC/Newey–West-keskivirheitä, suluissa)")
    print("=" * 100)
    otsikko = (
        f"{'Malli':<32}{'Vakio a':>13}{'BKT-kerroin b':>16}"
        f"{'Covid-dummy':>14}{'R²':>8}{'N':>6}{'-a/b (%)':>11}"
    )
    print(otsikko)
    print("-" * 100)
    for t in tulokset:
        a = t.params["const"]
        a_se = t.hac.bse["const"]
        b = t.params[t.kasvu_sarake]
        b_se = t.hac.bse[t.kasvu_sarake]
        a_str = f"{a:.3f} ({a_se:.3f})"
        b_str = f"{b:.3f} ({b_se:.3f})"
        if "covid" in t.params.index:
            c = t.params["covid"]
            c_se = t.hac.bse["covid"]
            covid_str = f"{c:.3f} ({c_se:.3f})"
        else:
            covid_str = "–"
        rivi = (
            f"{t.nimi:<32}"
            f"{a_str:>13}"
            f"{b_str:>16}"
            f"{covid_str:>14}"
            f"{t.rsquared:>8.4f}"
            f"{t.nobs:>6}"
            f"{t.kynnyskasvu():>11.3f}"
        )
        print(rivi)
    print("=" * 100)


def piirra_aikasarjat(aineisto: pd.DataFrame, tiedostopolku: str) -> None:
    """Piirtää BKT:n kasvun ja työttömyysasteen muutoksen samaan kuvaan
    (kaksi y-akselia), jotta sarjojen yhteisliike näkyy ajassa."""
    aika = aineisto.index.to_timestamp()

    fig, ax1 = plt.subplots(figsize=(11, 5.5))

    varit = {"bkt": "tab:blue", "tyottomyys": "tab:red"}

    ax1.plot(
        aika,
        aineisto["bkt_kasvu"],
        color=varit["bkt"],
        label="BKT:n volyymin kasvu, % (v/v)",
    )
    ax1.axhline(0, color="grey", linewidth=0.8, linestyle=":")
    ax1.set_xlabel("Vuosineljännes")
    ax1.set_ylabel("BKT:n volyymin kasvu, % (v/v)", color=varit["bkt"])
    ax1.tick_params(axis="y", labelcolor=varit["bkt"])

    ax2 = ax1.twinx()
    ax2.plot(
        aika,
        aineisto["tyottomyysasteen_muutos"],
        color=varit["tyottomyys"],
        label="Työttömyysasteen muutos, %-yks. (v/v)",
    )
    ax2.set_ylabel(
        "Työttömyysasteen muutos, %-yks. (v/v)", color=varit["tyottomyys"]
    )
    ax2.tick_params(axis="y", labelcolor=varit["tyottomyys"])

    viivat_1, nimet_1 = ax1.get_legend_handles_labels()
    viivat_2, nimet_2 = ax2.get_legend_handles_labels()
    ax1.legend(viivat_1 + viivat_2, nimet_1 + nimet_2, loc="upper right")

    plt.title("BKT:n kasvu ja työttömyysasteen muutos, Suomi")
    fig.tight_layout()
    fig.savefig(tiedostopolku, dpi=150)
    plt.close(fig)


def piirra_hajontakuvio(tulos: OkuninLainTulos, tiedostopolku: str) -> None:
    """Piirtää hajontakuvion (BKT-kasvu vs. työttömyysasteen muutos) ja
    OLS-mallin sovitesuoran."""
    aineisto = tulos.aineisto

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(
        aineisto["bkt_kasvu"],
        aineisto["tyottomyysasteen_muutos"],
        alpha=0.7,
        edgecolor="none",
        label="Havainnot (neljännesvuosi)",
    )

    x_ala, x_yla = aineisto["bkt_kasvu"].min(), aineisto["bkt_kasvu"].max()
    x_viiva = pd.Series([x_ala, x_yla])
    y_viiva = tulos.vakiotermi + tulos.kerroin * x_viiva
    ax.plot(
        x_viiva,
        y_viiva,
        color="tab:red",
        linewidth=2,
        label=(
            f"OLS-sovite: Δu = {tulos.vakiotermi:.3f} "
            f"+ {tulos.kerroin:.3f} · BKT-kasvu"
        ),
    )

    ax.axhline(0, color="grey", linewidth=0.8, linestyle=":")
    ax.axvline(0, color="grey", linewidth=0.8, linestyle=":")
    ax.set_xlabel("BKT:n volyymin kasvu, % (v/v)")
    ax.set_ylabel("Työttömyysasteen muutos, %-yks. (v/v)")
    ax.set_title("Okunin laki: Suomi")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(tiedostopolku, dpi=150)
    plt.close(fig)
