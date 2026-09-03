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

from dataclasses import dataclass

import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.api as sm


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
    print("=" * 70)


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
