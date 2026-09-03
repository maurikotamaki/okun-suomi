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
# epävarmuuden. Tässä lasketaan RINNAKKAIN kolme keskivirhevaihtoehtoa:
#   - OLS (klassinen, ei robusti)
#   - Newey–West (HAC, Bartlett-ydin)
#   - Andrews–Monahan (1992) esivalkaistu HAC (VAR(1)-esivalkaisu +
#     Newey–West-ydin jäännösprosessille + "uudelleenvärjäys")
# Koska otos on pieni (~60-66 havaintoa) ja HAC-estimaattorit ovat
# tunnetusti pienessä otoksessa harhaisia ALASPÄIN (Andrews 1991), PÄÄTULOS
# on kunkin mallin osalta se HAC-vaihtoehto, joka antaa SUUREMMAN
# (konservatiivisemman) keskivirheen BKT-kasvun kokonaisvaikutukselle,
# ei automaattisesti Newey–West tai automaattisesti pienin arvo.
# ---------------------------------------------------------------------------

NW_VAHIMMAISVIIVE_VV = 4  # v/v-erotusten päällekkäisyyden takia (MA(3))
NW_VAHIMMAISVIIVE_QOQ = 1  # neljännesmuutoksissa ei rakenteellista päällekkäisyyttä
PW_VAHIMMAISVIIVE = 1  # esivalkaisun jälkeen jäännösautokorrelaatio on jo pieni


def newey_west_viiveet(havaintoja: int, vahimmaisviive: int = 1) -> int:
    """Newey–Westin (1994) nyrkkisääntö viiveiden lukumäärälle,
    floor(4*(T/100)^(2/9)), rajattuna alhaalta parametrilla ``vahimmaisviive``.
    """
    nyrkkisaanto = int(np.floor(4 * (havaintoja / 100) ** (2 / 9)))
    return max(vahimmaisviive, nyrkkisaanto, 1)


def _bartlett_painot(viiveet: int) -> np.ndarray:
    return 1 - np.arange(viiveet + 1) / (viiveet + 1.0)


def _skalaariksi(x) -> float:
    """Poimii yhden luvun statsmodelsin t_test/wald_test-tuloksesta
    riippumatta siitä, onko se 0-, 1- vai 2-ulotteinen ndarray (vaihtelee
    statsmodels-version ja syötteen muodon mukaan)."""
    return float(np.asarray(x).reshape(-1)[0])


def annualisoi_kynnyskasvu(kynnyskasvu: float, yksikko: str) -> float:
    """Muuntaa kynnyskasvun vuositasolle (%/vuosi) sen alkuperäisestä
    yksiköstä. "v/v" (vuosimuutos) on jo vuositasoinen, joten se palautuu
    sellaisenaan. "q/q" (neljännesmuutos) annualisoidaan korkoa korolle
    -periaatteella, g_v = (1+g_q/100)^4 - 1, olettaen sama kasvuvauhti
    joka neljännes (tasapainotulkinta kynnyskasvulle)."""
    if yksikko == "q/q":
        return ((1 + kynnyskasvu / 100) ** 4 - 1) * 100
    if yksikko == "v/v":
        return kynnyskasvu
    raise ValueError(f"Tuntematon yksikkö: {yksikko!r} (odotettiin 'v/v' tai 'q/q')")


def _newey_west_kovarianssi(
    ols: sm.regression.linear_model.RegressionResultsWrapper,
    vahimmaisviive: int,
) -> tuple[np.ndarray, int]:
    """Tavallinen Newey–West-HAC-kovarianssi (Bartlett-ydin, pienen otoksen
    korjaus). Käyttää statsmodelsin omaa, testattua toteutusta."""
    viiveet = newey_west_viiveet(int(ols.nobs), vahimmaisviive)
    robusti = ols.get_robustcov_results(
        cov_type="HAC", maxlags=viiveet, use_correction=True
    )
    return np.asarray(robusti.cov_params()), viiveet


def _andrews_monahan_kovarianssi(
    ols: sm.regression.linear_model.RegressionResultsWrapper,
    vahimmaisviive: int = PW_VAHIMMAISVIIVE,
) -> tuple[np.ndarray, int]:
    """Andrews & Monahan (1992) esivalkaistu HAC-kovarianssi.

    Statsmodels ei tarjoa esivalkaisua valmiina, joten se on toteutettu
    tässä manuaalisesti standardimenetelmällä (vrt. R:n sandwich-paketin
    ``vcovHAC(..., prewhite = TRUE)``):

    1. Muodostetaan havaintokohtaiset "pisteet" xu_t = x_t · u_t (x_t =
       selittäjärivi, u_t = OLS-jäännös).
    2. Sovitetaan pisteprosessiin VAR(1): xu_t = A·xu_{t-1} + v_t (A
       estimoidaan pienimmän neliösumman menetelmällä). v_t on
       "esivalkaistu" jäännösprosessi, jonka pitäisi olla huomattavasti
       vähemmän autokorreloitunut kuin xu_t itse.
    3. Lasketaan v:n Newey–West-kovarianssi (Bartlett-ydin) tavalliseen
       tapaan.
    4. "Uudelleenvärjätään" tulos AR(1)-rakenteen mukaisesti:
       Ω = (I−A)⁻¹ Ω_v (I−A′)⁻¹.
    5. Muodostetaan lopullinen sandwich-kovarianssi (X'X)⁻¹ Ω (X'X)⁻¹, ja
       kerrotaan samalla pienen otoksen korjauksella kuin Newey–Westissä.

    Toteutus on validoitu niin, että jos esivalkaisuaskel ohitetaan (A=0),
    tulos täsmää statsmodelsin omaan ``cov_type="HAC"``-tulokseen
    numeerisesti tarkasti.
    """
    x = np.asarray(ols.model.exog)
    u = np.asarray(ols.resid)
    xu = x * u[:, None]
    n, k = xu.shape

    xu_viive = xu[:-1]
    xu_nyt = xu[1:]
    # xu_t ≈ xu_{t-1} @ A  (rivivektorimuoto; pystyvektorimuodossa
    # xu_t = A' xu_{t-1} + v_t)
    A, *_ = np.linalg.lstsq(xu_viive, xu_nyt, rcond=None)
    v = xu_nyt - xu_viive @ A

    viiveet = newey_west_viiveet(v.shape[0], vahimmaisviive)
    painot = _bartlett_painot(viiveet)
    S_v = painot[0] * (v.T @ v)
    for lag in range(1, viiveet + 1):
        s = v[lag:].T @ v[:-lag]
        S_v += painot[lag] * (s + s.T)

    A_pysty = A.T
    I = np.eye(k)
    IA_inv = np.linalg.inv(I - A_pysty)
    S_varjatty = IA_inv @ S_v @ IA_inv.T

    XtX_inv = np.asarray(ols.normalized_cov_params)
    kovarianssi = XtX_inv @ S_varjatty @ XtX_inv.T
    kovarianssi *= n / (n - k)
    return kovarianssi, viiveet


@dataclass
class RobustiTulos:
    """OLS-malli täydennettynä kolmella keskivirhevaihtoehdolla (OLS,
    Newey–West, Andrews–Monahan-esivalkaistu HAC) ja autokorrelaatio-
    diagnostiikalla (Durbin–Watson, Breusch–Godfrey).

    ``kasvu_sarakkeet`` on lista BKT-kasvu-selittäjistä: yhden alkion
    lista tavallisessa mallissa, useamman alkion lista viivemallissa,
    jolloin niiden kertoimien SUMMA tulkitaan BKT-kasvun pitkän aikavälin
    kokonaisvaikutukseksi. ``yksikko`` kertoo, ovatko selittäjät
    vuosimuutoksia ("v/v") vai neljännesmuutoksia ("q/q") — tätä
    käytetään kynnyskasvun annualisointiin.
    """

    nimi: str
    y_sarake: str
    kasvu_sarakkeet: list[str]
    yksikko: str
    ols: sm.regression.linear_model.RegressionResultsWrapper
    nw_cov: np.ndarray
    nw_viiveet: int
    pw_cov: np.ndarray
    pw_viiveet: int
    dw: float
    bg_lm: float
    bg_lm_p: float
    bg_viiveet: int

    @property
    def params(self) -> pd.Series:
        return self.ols.params

    @property
    def param_nimet(self) -> list[str]:
        return list(self.params.index)

    @property
    def rsquared(self) -> float:
        return self.ols.rsquared

    @property
    def nobs(self) -> int:
        return int(self.ols.nobs)

    def _kovarianssi(self, nimi: str) -> np.ndarray:
        if nimi == "ols":
            return np.asarray(self.ols.cov_params())
        if nimi == "nw":
            return self.nw_cov
        if nimi == "pw":
            return self.pw_cov
        if nimi == "konservatiivinen":
            return self.pw_cov if self.paa_nimi == "pw" else self.nw_cov
        raise ValueError(f"Tuntematon kovarianssin nimi: {nimi!r}")

    def _lineaarikombinaatio(
        self, sarakkeet: Sequence[str], kovarianssin_nimi: str
    ) -> tuple[float, float, float, float]:
        """(estimaatti, keskivirhe, t-arvo, p-arvo) sarakkeiden kertoimien
        summalle, annetulla kovarianssimatriisilla."""
        r = np.zeros(len(self.param_nimet))
        for sarake in sarakkeet:
            r[self.param_nimet.index(sarake)] = 1.0
        cov = self._kovarianssi(kovarianssin_nimi)
        tt = self.ols.t_test(r, cov_p=cov)
        estimaatti = _skalaariksi(tt.effect)
        se = _skalaariksi(tt.sd)
        t_arvo = _skalaariksi(tt.tvalue)
        p_arvo = _skalaariksi(tt.pvalue)
        return estimaatti, se, t_arvo, p_arvo

    @property
    def paa_nimi(self) -> str:
        """Kumpi HAC-vaihtoehdoista (nw/pw) valitaan PÄÄTULOKSEKSI: se,
        joka antaa suuremman (konservatiivisemman) keskivirheen BKT-kasvun
        pitkän aikavälin vaikutukselle. Ei koskaan valita pienintä."""
        _, nw_se, _, _ = self._lineaarikombinaatio(self.kasvu_sarakkeet, "nw")
        _, pw_se, _, _ = self._lineaarikombinaatio(self.kasvu_sarakkeet, "pw")
        return "pw" if pw_se >= nw_se else "nw"

    @property
    def paa_viiveet(self) -> int:
        return self.pw_viiveet if self.paa_nimi == "pw" else self.nw_viiveet

    def bse(self, kovarianssin_nimi: str) -> pd.Series:
        cov = self._kovarianssi(kovarianssin_nimi)
        return pd.Series(np.sqrt(np.diag(cov)), index=self.param_nimet)

    def kertoimen_tilastot(
        self, sarake: str, kovarianssin_nimi: str = "konservatiivinen"
    ) -> tuple[float, float, float, float]:
        """(estimaatti, keskivirhe, t-arvo, p-arvo) yhdelle yksittäiselle
        selittäjälle (esim. vakiotermille tai covid-dummylle)."""
        return self._lineaarikombinaatio([sarake], kovarianssin_nimi)

    def pitkan_aikavalin_vaikutus(
        self, kovarianssin_nimi: str = "konservatiivinen"
    ) -> tuple[float, float, float, float]:
        """(estimaatti, keskivirhe, t-arvo, p-arvo) BKT-kasvun kertoimien
        summalle (= pitkän aikavälin kokonaisvaikutus). Yhden selittäjän
        malleissa tämä on sama kuin kyseisen kertoimen oma tilastollinen
        testi."""
        return self._lineaarikombinaatio(self.kasvu_sarakkeet, kovarianssin_nimi)

    def kynnyskasvu(self, kovarianssin_nimi: str = "konservatiivinen") -> float:
        """Kynnyskasvu -a / Σb, mallin OMASSA taajuudessa (v/v tai q/q)."""
        vaikutus, *_ = self.pitkan_aikavalin_vaikutus(kovarianssin_nimi)
        return -self.params["const"] / vaikutus

    def kynnyskasvu_vuositasolla(
        self, kovarianssin_nimi: str = "konservatiivinen"
    ) -> float:
        """Kynnyskasvu annualisoituna (%/vuosi), jotta v/v- ja
        q/q-spesifikaatiot ovat vertailukelpoisia. v/v-malleissa arvo on
        jo vuositasoinen. q/q-malleissa neljänneskasvu annualisoidaan
        korkoa korolle -periaatteella: g_v = (1+g_q/100)^4 - 1, koska BKT
        kasvaisi samalla vauhdilla joka neljännes tasapainossa."""
        g = self.kynnyskasvu(kovarianssin_nimi)
        return annualisoi_kynnyskasvu(g, self.yksikko)

    def yhteismerkitsevyys(
        self, kovarianssin_nimi: str = "konservatiivinen"
    ) -> tuple[float, float, int, int]:
        """Waldin F-testi H0: kaikki kasvu_sarakkeet-kertoimet ovat
        (yhdessä) nollia. Palauttaa (F, p, df_osoittaja, df_nimittäjä)."""
        k = len(self.param_nimet)
        R = np.zeros((len(self.kasvu_sarakkeet), k))
        for i, sarake in enumerate(self.kasvu_sarakkeet):
            R[i, self.param_nimet.index(sarake)] = 1.0
        cov = self._kovarianssi(kovarianssin_nimi)
        wt = self.ols.wald_test(R, cov_p=cov, use_f=True)
        return (
            float(wt.statistic),
            float(wt.pvalue),
            int(round(wt.df_num)),
            int(round(wt.df_denom)),
        )


def estimoi_robusti(
    aineisto: pd.DataFrame,
    y_sarake: str,
    x_sarakkeet: Sequence[str],
    nimi: str,
    kasvu_sarakkeet: Sequence[str],
    yksikko: str = "v/v",
    nw_vahimmaisviive: int = NW_VAHIMMAISVIIVE_VV,
    pw_vahimmaisviive: int = PW_VAHIMMAISVIIVE,
    bg_viiveet: int | None = None,
) -> RobustiTulos:
    """Estimoi OLS:n ja täydentää sen kolmella keskivirhevaihtoehdolla
    (OLS, Newey–West, Andrews–Monahan-esivalkaistu HAC) sekä
    Durbin–Watson- ja Breusch–Godfrey-testeillä.

    ``x_sarakkeet`` voi sisältää useamman selittäjän (esim. BKT-kasvun eri
    viiveet ja/tai covid-dummyn); ``kasvu_sarakkeet`` kertoo, mitkä niistä
    ovat BKT-kasvu-muuttujia, joiden kertoimien summaa käytetään pitkän
    aikavälin vaikutuksen ja kynnyskasvun (-a/Σb) laskennassa.
    """
    y = aineisto[y_sarake]
    x = sm.add_constant(aineisto[list(x_sarakkeet)])

    ols = sm.OLS(y, x).fit()

    nw_cov, nw_viiveet = _newey_west_kovarianssi(ols, nw_vahimmaisviive)
    pw_cov, pw_viiveet = _andrews_monahan_kovarianssi(ols, pw_vahimmaisviive)

    dw = float(durbin_watson(ols.resid))

    bg_L = bg_viiveet if bg_viiveet is not None else nw_viiveet
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
        kasvu_sarakkeet=list(kasvu_sarakkeet),
        yksikko=yksikko,
        ols=ols,
        nw_cov=nw_cov,
        nw_viiveet=nw_viiveet,
        pw_cov=pw_cov,
        pw_viiveet=pw_viiveet,
        dw=dw,
        bg_lm=float(bg_lm),
        bg_lm_p=float(bg_lm_p),
        bg_viiveet=bg_L,
    )


KOVARIANSSI_NIMET = {"ols": "OLS", "nw": "Newey–West", "pw": "Andrews–Monahan (esivalk.)"}


def tulosta_hac_diagnostiikka(tulos: RobustiTulos) -> None:
    """Tulostaa OLS-, Newey–West- ja Andrews–Monahan-keskivirheet
    rinnakkain, kertoo kumpi HAC-vaihtoehdoista on valittu konservatiivi-
    seksi päätulokseksi, sekä DW-, BG- ja kynnyskasvutiedot."""
    print()
    print("-" * 78)
    print(f"Robustisuus: {tulos.nimi}")
    print(
        f"Keskivirheet: OLS vs. Newey–West (L={tulos.nw_viiveet}) vs. "
        f"Andrews–Monahan-esivalkaistu HAC (L={tulos.pw_viiveet} "
        "esivalkaisun jälkeen)"
    )
    k_params = len(tulos.param_nimet)
    df_resid = tulos.nobs - k_params
    print(
        f"N = {tulos.nobs}   selittäjiä vakio mukaan lukien k = {k_params}   "
        f"vapausasteet (df_resid = N-k) = {df_resid}"
    )
    print("-" * 78)
    print(
        f"{'Termi':<15}{'Kerroin':>11}{'OLS-SE':>11}{'NW-SE':>11}{'AM-SE':>11}"
    )
    ols_bse = tulos.bse("ols")
    nw_bse = tulos.bse("nw")
    pw_bse = tulos.bse("pw")
    for termi in tulos.param_nimet:
        print(
            f"{termi:<15}{tulos.params[termi]:>11.4f}"
            f"{ols_bse[termi]:>11.4f}"
            f"{nw_bse[termi]:>11.4f}"
            f"{pw_bse[termi]:>11.4f}"
        )
    print("-" * 78)
    print(
        f"Päätulokseksi valittu (konservatiivisin): "
        f"{KOVARIANSSI_NIMET[tulos.paa_nimi]} "
        "— pienessä otoksessa HAC-keskivirheet ovat tunnetusti alaspäin "
        "harhaisia, joten päätuloksena käytetään suurempaa SE:tä, ei "
        "kummankaan menetelmän pienintä arvoa."
    )
    print(
        f"Durbin–Watson:              {tulos.dw:.3f}  "
        "(2.0 = ei autokorrelaatiota; <2 viittaa positiiviseen)"
    )
    print(
        f"Breusch–Godfrey (L={tulos.bg_viiveet}):   LM={tulos.bg_lm:.3f}, "
        f"p={tulos.bg_lm_p:.4f}  "
        "(H0: ei jäljellä olevaa autokorrelaatiota jäännöksissä)"
    )

    if len(tulos.kasvu_sarakkeet) > 1:
        vaikutus, se, t_arvo, p_arvo = tulos.pitkan_aikavalin_vaikutus("konservatiivinen")
        print(
            f"BKT-kasvun pitkän aikavälin vaikutus (Σb, {len(tulos.kasvu_sarakkeet)} "
            f"viivettä, {KOVARIANSSI_NIMET[tulos.paa_nimi]}-SE):"
        )
        print(f"  Σb = {vaikutus:.4f}  SE = {se:.4f}  t = {t_arvo:.3f}  p = {p_arvo:.4f}")
        f_arvo, p_yhdessa, df1, df2 = tulos.yhteismerkitsevyys("konservatiivinen")
        print(
            f"Viiveiden yhteismerkitsevyys (Wald F, H0: kaikki BKT-viiveiden "
            f"kertoimet = 0): F({df1},{df2}) = {f_arvo:.3f}, p = {p_yhdessa:.4f}"
        )

    kynnys = tulos.kynnyskasvu("konservatiivinen")
    kynnys_v = tulos.kynnyskasvu_vuositasolla("konservatiivinen")
    if tulos.yksikko == "q/q":
        print(
            f"Kynnyskasvu -a/Σb:          {kynnys:.3f} % / neljännes "
            f"→ annualisoituna {kynnys_v:.3f} % / vuosi"
        )
    else:
        print(f"Kynnyskasvu -a/Σb:          {kynnys_v:.3f} % / vuosi")


@dataclass
class KausivaihteluTesti:
    """Apuregression jäännös ~ vakio + Q2/Q3/Q4-dummyt (Q1 referenssinä)
    tulos, jolla testataan onko mallin OLS-jäännöksissä jäljellä
    systemaattista kausivaihtelua siitä huolimatta, että selittäjät on jo
    kausitasoitettu."""

    apumalli: sm.regression.linear_model.RegressionResultsWrapper
    f_arvo: float
    f_p: float
    df_osoittaja: int
    df_nimittaja: int


def testaa_jaannosten_kausivaihtelu(tulos: RobustiTulos) -> KausivaihteluTesti:
    """Regressoi ``tulos``-mallin (tavallisen OLS:n) jäännökset
    neljännesdummyilla (Q2, Q3, Q4; Q1 on referenssi) ja testaa niiden
    yhteismerkitsevyyden F-testillä.

    Tämä on erillinen, HAC-analyysistä riippumaton tarkistus: jos
    kausitasoitetuissa sarjoissa on siitä huolimatta jäänyt jäljelle
    systemaattista neljänneksestä toiseen toistuvaa vaihtelua (esim.
    epätäydellisen kausitasoituksen takia), se näkyisi tässä
    apuregressiossa merkitsevinä kausidummyina — mikä voisi selittää
    myös yksittäisten viivekertoimien (esim. L4 vs. L3) epätasaisuutta.

    Vaatii, että ``tulos.ols.resid``-indeksi on ``pd.PeriodIndex``
    (freq="Q"), jotta neljännesnumero (1-4) on pääteltävissä.
    """
    resid = tulos.ols.resid
    if not isinstance(resid.index, pd.PeriodIndex):
        raise TypeError(
            "testaa_jaannosten_kausivaihtelu vaatii PeriodIndex(freq='Q') "
            f"-indeksin jäännöksille, saatiin {type(resid.index)}"
        )

    neljannes = pd.Series(resid.index.quarter, index=resid.index, name="Q")
    dummyt = pd.get_dummies(neljannes, prefix="Q", drop_first=True).astype(float)
    x = sm.add_constant(dummyt)
    apumalli = sm.OLS(resid, x).fit()

    return KausivaihteluTesti(
        apumalli=apumalli,
        f_arvo=float(apumalli.fvalue),
        f_p=float(apumalli.f_pvalue),
        df_osoittaja=int(apumalli.df_model),
        df_nimittaja=int(apumalli.df_resid),
    )


def tulosta_kausivaihtelutesti(testi: KausivaihteluTesti, nimi: str) -> None:
    print()
    print(f"Jäännösten kausivaihtelutesti: {nimi}")
    print("(apuregressio: OLS-jäännös ~ vakio + Q2 + Q3 + Q4; Q1 = referenssi)")
    print(f"{'Termi':<12}{'Kerroin':>11}{'SE':>11}{'t':>9}{'p':>9}")
    for termi in testi.apumalli.params.index:
        print(
            f"{termi:<12}{testi.apumalli.params[termi]:>11.4f}"
            f"{testi.apumalli.bse[termi]:>11.4f}"
            f"{testi.apumalli.tvalues[termi]:>9.3f}"
            f"{testi.apumalli.pvalues[termi]:>9.4f}"
        )
    print(
        f"Yhteismerkitsevyys (F-testi, H0: ei kausivaihtelua jäännöksissä): "
        f"F({testi.df_osoittaja},{testi.df_nimittaja}) = {testi.f_arvo:.3f}, "
        f"p = {testi.f_p:.4f}"
    )
    if testi.f_p < 0.05:
        print(
            "  -> p < 0.05: jäännöksissä ON viitteitä jäljellä olevasta "
            "kausivaihtelusta huolimatta kausitasoituksesta."
        )
    else:
        print(
            "  -> p >= 0.05: ei tilastollista näyttöä jäljellä olevasta "
            "kausivaihtelusta jäännöksissä."
        )


def tulosta_kolmen_otoksen_taulukko(tulokset: Sequence[RobustiTulos]) -> None:
    """Tulostaa rinnakkaisvertailun (kertoimet, konservatiivisimman
    HAC-vaihtoehdon keskivirheet, R², vuositasoinen kynnyskasvu) kolmesta
    (tai useammasta) mallista yhtenä taulukkona."""
    print()
    print("=" * 106)
    print("Otosvertailu: koko aineisto / ilman 2020–2021 / covid-dummy mukana")
    print(
        "(keskivirheet ovat kunkin mallin konservatiivisimman HAC-vaihtoehdon "
        "mukaisia, suluissa — ks. yllä; -a/Σb on vuositasoinen)"
    )
    print("=" * 106)
    otsikko = (
        f"{'Malli':<32}{'Vakio a':>13}{'BKT-kerroin b':>16}"
        f"{'Covid-dummy':>14}{'R²':>8}{'N':>6}{'-a/b, %/v':>12}"
    )
    print(otsikko)
    print("-" * 106)
    for t in tulokset:
        a = t.params["const"]
        _, a_se, _, _ = t.kertoimen_tilastot("const")
        b_sarake = t.kasvu_sarakkeet[0]
        b = t.params[b_sarake]
        _, b_se, _, _ = t.kertoimen_tilastot(b_sarake)
        a_str = f"{a:.3f} ({a_se:.3f})"
        b_str = f"{b:.3f} ({b_se:.3f})"
        if "covid" in t.param_nimet:
            c = t.params["covid"]
            _, c_se, _, _ = t.kertoimen_tilastot("covid")
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
            f"{t.kynnyskasvu_vuositasolla('konservatiivinen'):>12.3f}"
        )
        print(rivi)
    print("=" * 106)


def tulosta_kynnyskasvu_yhteenveto(
    tulokset: Sequence[tuple[str, float, str]],
) -> None:
    """Tulostaa kaikkien spesifikaatioiden kynnyskasvun samassa,
    annualisoidussa yksikössä (%/vuosi), merkiten selvästi kunkin
    spesifikaation alkuperäisen taajuuden (v/v tai q/q).

    ``tulokset`` on lista (nimi, kynnyskasvu_omassa_yksikössä, yksikkö)
    -kolmikoita — näin sama funktio kelpaa niin ``RobustiTulos``-
    olioille (``t.kynnyskasvu()``, ``t.yksikko``) kuin alkuperäisen,
    ei-robustin OLS-spesifikaation tulokselle.
    """
    print()
    print("=" * 78)
    print("Kynnyskasvu -a/Σb kaikissa spesifikaatioissa, annualisoituna")
    print("(BKT:n kasvuvauhti, %/vuosi, jolla työttömyysaste ei muutu)")
    print("=" * 78)
    for nimi, kynnys_oma, yksikko in tulokset:
        kynnys_v = annualisoi_kynnyskasvu(kynnys_oma, yksikko)
        print(f"  {nimi:<44}{kynnys_v:>9.3f} %/v   (alkup. yksikkö: {yksikko})")
    print("=" * 78)


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
