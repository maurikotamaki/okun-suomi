"""Datan haku Tilastokeskuksen PxWeb-rajapinnasta (StatFin-tietokanta).

Rajapinta ja taulukot on selvitetty kokeilemalla suoraan osoitteita:

* Oikea PxWeb-juuripolku on ``https://pxdata.stat.fi/PxWeb/api/v1/fi/...``
  (huomaa ``PxWeb``-segmentti — pelkkä ``/api/v1/...`` palauttaa 404:n).
* BKT:n volyymin muutos: StatFin/ntp/132h.px
  ("QNA Bruttokansantuote ja -tulo sekä tarjonta ja kysyntä neljännesvuosittain",
  1990Q1-2026Q2 [päivittyy]). Käytetään sarjaa
  taloustoimi=B1GMH (Bruttokansantuote markkinahintaan),
  contentscode=vol_vv_tyopvv2015 (työpäiväkorjatun sarjan volyymin muutos
  vuodentakaisesta, %).
* Työttömyysaste: StatFin/tyti/137h.px
  ("Väestö työmarkkina-aseman, sukupuolen ja iän mukaan, neljännesvuositiedot",
  2009Q1-2026Q2 [päivittyy]). Käytetään sarjaa sukupuoli=SSS (koko väestö),
  ikäryhmä=15-74, contentscode=tyti-Tyottomyysaste.

Miksi työttömyysaste vain vuodesta 2009 alkaen?
-------------------------------------------------
Tilastokeskuksen työvoimatutkimus uudistettiin vuoden 2021 alussa. StatFin-
tietokannan taulukko 137h sisältää uuden estimointimenetelmän mukaisesti
takautuvasti korjatut sarjat vuodesta 2009 lähtien, mutta Tilastokeskus
toteaa taulukon metatiedoissa nimenomaisesti, etteivät nämä luvut ole
vertailukelpoisia sitä vanhempien (taulukko 11c8, nyt StatFin_Passiivi-
kannassa, 1989Q1-2020Q4) tietojen kanssa. Jotta aikasarja pysyisi
menetelmällisesti *yhtenäisenä*, tässä ei yhdistetä eri vintages-sarjoja,
vaan käytetään yksinomaan nykyistä, sisäisesti yhtenäistä 137h-taulukkoa.
Tämä rajaa työttömyysasteen alkupisteeksi 2009Q1 (ja siitä laskettavan
vuosimuutoksen alkupisteeksi 2010Q1), vaikka BKT-sarja itsessään ulottuisi
kauemmas taaksepäin.

Tässä moduulissa ei ole mitään keksittyä tai simuloitua dataa: jos
rajapintaan ei saada yhteyttä tai vastaus ei ole odotetun muotoinen,
funktiot nostavat poikkeuksen sen sijaan, että palauttaisivat korvaavaa
dataa.
"""

from __future__ import annotations

import pandas as pd
import requests

PXWEB_BASE = "https://pxdata.stat.fi/PxWeb/api/v1/fi/StatFin"

GDP_TAULUKKO = f"{PXWEB_BASE}/ntp/132h.px"
GDP_KYSELY = {
    "query": [
        {
            "code": "taloustoimi_1_20180101",
            "selection": {"filter": "item", "values": ["B1GMH"]},
        },
        {
            "code": "contentscode",
            "selection": {"filter": "item", "values": ["vol_vv_tyopvv2015"]},
        },
    ],
    "response": {"format": "json-stat2"},
}

TYOTTOMYYS_TAULUKKO = f"{PXWEB_BASE}/tyti/137h.px"
TYOTTOMYYS_KYSELY = {
    "query": [
        {
            "code": "sukupuoli_9_20180101",
            "selection": {"filter": "item", "values": ["SSS"]},
        },
        {
            "code": "ikaryhma_19_20190101",
            "selection": {"filter": "item", "values": ["15-74"]},
        },
        {
            "code": "contentscode",
            "selection": {"filter": "item", "values": ["tyti-Tyottomyysaste"]},
        },
    ],
    "response": {"format": "json-stat2"},
}

# Vaihtoehtoista neljännesmuutos-spesifikaatiota varten: kausitasoitettu BKT:n
# volyymin muutos edellisneljänneksestä (sama taulukko 132h kuin edellä, eri
# "Tiedot"-sisältökoodi).
GDP_QOQ_KYSELY = {
    "query": [
        {
            "code": "taloustoimi_1_20180101",
            "selection": {"filter": "item", "values": ["B1GMH"]},
        },
        {
            "code": "contentscode",
            "selection": {"filter": "item", "values": ["vol_kk_kausitvv2015"]},
        },
    ],
    "response": {"format": "json-stat2"},
}

# Kausitasoitettu työttömyysaste on saatavilla vain kuukausitasolla
# (StatFin/tyti/135z.px, "kausitasoitettu sarja"). Neljännesmuutos-
# spesifikaatiossa se lasketaan kuukausikeskiarvoina neljännesvuositasolle,
# jotta se on vertailukelpoinen kausitasoitetun neljännes-BKT:n kanssa.
TYOTTOMYYS_KUUKAUSI_TAULUKKO = f"{PXWEB_BASE}/tyti/135z.px"
TYOTTOMYYS_KUUKAUSI_KYSELY = {
    "query": [
        {
            "code": "contentscode",
            "selection": {"filter": "item", "values": ["Tyottaste_kausi"]},
        },
    ],
    "response": {"format": "json-stat2"},
}

AIKAMUUTTUJAT = ("timeperiod_q", "Vuosineljännes", "timeperiod_m", "Kuukausi")


def _hae_json_stat2(url: str, kysely: dict) -> dict:
    """Tekee POST-kyselyn PxWeb-rajapintaan ja palauttaa JSON-stat2-vastauksen.

    Ei koskaan palauta korvaavaa/simuloitua dataa: verkko- tai
    rajapintavirheessä nostetaan poikkeus, joka kertoo mikä meni pieleen.
    """
    try:
        vastaus = requests.post(url, json=kysely, timeout=30)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"PxWeb-rajapintaan ({url}) ei saatu yhteyttä: {exc}"
        ) from exc

    if vastaus.status_code != 200:
        raise RuntimeError(
            f"PxWeb-rajapinta ({url}) vastasi statuksella "
            f"{vastaus.status_code}: {vastaus.text[:500]}"
        )

    try:
        data = vastaus.json()
    except ValueError as exc:
        raise RuntimeError(
            f"PxWeb-rajapinnan ({url}) vastausta ei voitu tulkita JSON:ksi"
        ) from exc

    return data


def _hae_taulukon_metatiedot(taulukko_url: str) -> dict:
    """Hakee PxWeb-taulukon metatiedot (GET-pyyntö, ei kyselyrunkoa) —
    sisältää mm. jokaisen muuttujan koodit ja niiden selitetekstit.
    Samat ei-koskaan-korvaavaa-dataa -periaatteet kuin ``_hae_json_stat2``.
    """
    try:
        vastaus = requests.get(taulukko_url, timeout=30)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"PxWeb-taulukon metatietoja ({taulukko_url}) ei saatu: {exc}"
        ) from exc

    if vastaus.status_code != 200:
        raise RuntimeError(
            f"PxWeb-taulukko ({taulukko_url}) vastasi statuksella "
            f"{vastaus.status_code}: {vastaus.text[:500]}"
        )

    try:
        return vastaus.json()
    except ValueError as exc:
        raise RuntimeError(
            f"PxWeb-taulukon ({taulukko_url}) metatietoja ei voitu tulkita JSON:ksi"
        ) from exc


def hae_sisaltokoodin_selite(taulukko_url: str, sisaltokoodi: str) -> str:
    """Hakee PxWeb-taulukon metatiedoista annetun "Tiedot"-sisältökoodin
    virallisen selitetekstin (esim. ``"Tyottaste_kausi"`` ->
    ``"Työttömyysaste, %, kausitasoitettu sarja"``).

    Tätä käytetään ajonaikaisesti VARMISTAMAAN — ei vain oletetaan
    dokumentaation tai koodin nimen perusteella — mikä sarja todella on
    valittu ja onko se kausitasoitettu.
    """
    data = _hae_taulukon_metatiedot(taulukko_url)
    for muuttuja in data.get("variables", []):
        if muuttuja.get("code") == "contentscode" or muuttuja.get("text") == "Tiedot":
            for koodi, teksti in zip(muuttuja["values"], muuttuja["valueTexts"]):
                if koodi == sisaltokoodi:
                    return teksti
    raise RuntimeError(
        f"Sisältökoodia {sisaltokoodi!r} ei löytynyt taulukon {taulukko_url} "
        "metatiedoista."
    )


def varmista_qoq_kausitasoitus() -> dict[str, str]:
    """Varmistaa PxWeb-metatiedoista (ajonaikaisesti, ei pelkän koodin
    nimen perusteella), että neljännesmuutos-spesifikaation MOLEMMAT
    sarjat — BKT:n q/q-kasvu ja työttömyysasteen taso, josta q/q-muutos
    lasketaan — ovat todella kausitasoitettuja PxWebin oman selitetekstin
    mukaan. Nostaa poikkeuksen, jos selitteessä ei mainita kausitasoitusta.

    Palauttaa sanakirjan {sarja: (taulukko, sisältökoodi, selite)}.
    """
    bkt_koodi = GDP_QOQ_KYSELY["query"][1]["selection"]["values"][0]
    tyottomyys_koodi = TYOTTOMYYS_KUUKAUSI_KYSELY["query"][0]["selection"]["values"][0]

    bkt_selite = hae_sisaltokoodin_selite(GDP_TAULUKKO, bkt_koodi)
    tyottomyys_selite = hae_sisaltokoodin_selite(
        TYOTTOMYYS_KUUKAUSI_TAULUKKO, tyottomyys_koodi
    )

    tulos = {
        "BKT:n neljännesmuutos (bkt_kasvu_qoq_L*)": (
            GDP_TAULUKKO,
            bkt_koodi,
            bkt_selite,
        ),
        "Työttömyysasteen taso, josta q/q-muutos lasketaan": (
            TYOTTOMYYS_KUUKAUSI_TAULUKKO,
            tyottomyys_koodi,
            tyottomyys_selite,
        ),
    }

    for nimi, (_taulukko, _koodi, selite) in tulos.items():
        if "kausitasoi" not in selite.lower():
            raise RuntimeError(
                f"{nimi}: PxWeb-metatietojen selite ({selite!r}) ei mainitse "
                "kausitasoitusta — väärä sisältökoodi valittu?"
            )

    return tulos


def _pxweb_leima_jaksoksi(leima: str) -> pd.Period:
    """Muuttaa PxWebin aikaleiman ("1990Q1" tai "2010M01") pandas Periodiksi.

    Neljännesleimat pandas osaa jäsentää sellaisenaan, mutta kuukausileimat
    (muotoa "2010M01") eivät kelpaa pandasin omalle jäsentäjälle sellaisenaan
    ("M" sekoittuu minuutti-tunnisteeseen), joten ne muunnetaan ensin
    ISO-muotoon "2010-01".
    """
    if "Q" in leima:
        return pd.Period(leima, freq="Q")
    if "M" in leima:
        vuosi, kuukausi = leima.split("M")
        return pd.Period(f"{vuosi}-{kuukausi}", freq="M")
    raise RuntimeError(f"Tunnistamaton PxWeb-aikaleima: {leima!r}")


def _poimi_aikasarja(data: dict, sarjan_nimi: str) -> pd.Series:
    """Muuttaa yhden JSON-stat2-vastauksen aikasarjaksi (pandas Series).

    Oletus: kaikki muut ulottuvuudet paitsi aikamuuttuja on rajattu
    kyselyssä yhteen arvoon, jolloin ``value``-taulukko vastaa suoraan
    aikamuuttujan järjestystä.
    """
    aika_koodi = next((k for k in AIKAMUUTTUJAT if k in data["dimension"]), None)
    if aika_koodi is None:
        raise RuntimeError(
            f"Vastauksesta ei löytynyt tunnettua aikamuuttujaa "
            f"({', '.join(AIKAMUUTTUJAT)}); löytyneet: "
            f"{list(data['dimension'].keys())}"
        )

    kategoriat = data["dimension"][aika_koodi]["category"]["index"]
    jarjestetyt_leimat = sorted(kategoriat, key=lambda leima: kategoriat[leima])
    arvot = data["value"]

    if len(arvot) != len(jarjestetyt_leimat):
        raise RuntimeError(
            "PxWeb-vastauksen arvojen määrä ei täsmää aikaleimojen määrään "
            "— kysely on ehkä rajannut useamman kuin yhden arvon jollekin "
            "muulle ulottuvuudelle kuin ajalle."
        )

    jakso_indeksi = pd.PeriodIndex(
        [_pxweb_leima_jaksoksi(leima) for leima in jarjestetyt_leimat]
    )
    return pd.Series(arvot, index=jakso_indeksi, name=sarjan_nimi, dtype="float64")


def hae_bkt_kasvu() -> pd.Series:
    """Hakee BKT:n volyymin muutoksen (%, vuodentakaisesta) neljännesvuosittain.

    Lähde: StatFin/ntp/132h.px, taloustoimi B1GMH (BKT markkinahintaan),
    työpäiväkorjatun sarjan volyymin muutos vuodentakaisesta.
    """
    data = _hae_json_stat2(GDP_TAULUKKO, GDP_KYSELY)
    return _poimi_aikasarja(data, "bkt_kasvu")


def hae_tyottomyysaste() -> pd.Series:
    """Hakee työttömyysasteen (%) neljännesvuosittain, koko väestö 15-74v.

    Lähde: StatFin/tyti/137h.px, sukupuoli SSS, ikäryhmä 15-74.
    """
    data = _hae_json_stat2(TYOTTOMYYS_TAULUKKO, TYOTTOMYYS_KYSELY)
    return _poimi_aikasarja(data, "tyottomyysaste")


def hae_ja_yhdista() -> pd.DataFrame:
    """Hakee molemmat sarjat, laskee työttömyysasteen vuosimuutoksen ja
    yhdistää ne yhteiseksi, aukottomaksi aikasarja-DataFrameksi.

    Palauttaa DataFramen, jonka indeksi on neljännesvuosi (PeriodIndex,
    freq="Q") ja sarakkeet:
        - ``bkt_kasvu``: BKT:n volyymin muutos, % vuodentakaisesta
        - ``tyottomyysaste``: työttömyysaste, %
        - ``tyottomyysasteen_muutos``: työttömyysasteen muutos
          vuodentakaisesta, prosenttiyksikköä (u_t - u_{t-4})

    Vain rivit, joilta löytyy arvo jokaiseen sarakkeeseen, säilytetään —
    tämä rajaa lopullisen aineiston pisimpään yhtenäiseen jaksoon, jolta
    molemmat sarjat ovat saatavilla (käytännössä 2010Q1 alkaen, koska
    työttömyysasteen vuosimuutos vaatii neljä edeltävää havaintoa).
    """
    bkt = hae_bkt_kasvu()
    tyottomyys = hae_tyottomyysaste()

    tyottomyys_muutos = (tyottomyys - tyottomyys.shift(4)).rename(
        "tyottomyysasteen_muutos"
    )

    df = pd.concat([bkt, tyottomyys, tyottomyys_muutos], axis=1)
    df = df.sort_index()
    df = df.dropna(subset=["bkt_kasvu", "tyottomyysasteen_muutos"])
    df["covid"] = df.index.year.isin([2020, 2021]).astype(int)
    return df


def hae_bkt_kasvu_qoq() -> pd.Series:
    """Hakee kausitasoitetun BKT:n volyymin muutoksen (%, edellisneljänneksestä).

    Lähde: StatFin/ntp/132h.px, taloustoimi B1GMH, kausitasoitetun ja
    työpäiväkorjatun sarjan volyymin muutos edellisneljänneksestä.
    """
    data = _hae_json_stat2(GDP_TAULUKKO, GDP_QOQ_KYSELY)
    return _poimi_aikasarja(data, "bkt_kasvu_qoq")


def hae_tyottomyysaste_kausitasoitettu_kk() -> pd.Series:
    """Hakee kausitasoitetun työttömyysasteen (%) kuukausittain.

    Lähde: StatFin/tyti/135z.px, "Työttömyysaste, %, kausitasoitettu sarja".
    """
    data = _hae_json_stat2(TYOTTOMYYS_KUUKAUSI_TAULUKKO, TYOTTOMYYS_KUUKAUSI_KYSELY)
    return _poimi_aikasarja(data, "tyottomyysaste_kausi_kk")


def hae_ja_yhdista_qoq(maksimiviive: int = 4) -> pd.DataFrame:
    """Muodostaa vaihtoehtoisen, neljännesmuutoksiin perustuvan aineiston,
    mukaan lukien BKT-kasvun viiveet 0..``maksimiviive`` neljännestä.

    BKT-sarja on jo valmiiksi kausitasoitettu ja ilmaistu edellisneljänneksen
    muutoksena. Työttömyysaste on saatavilla kausitasoitettuna vain
    kuukausitasolla, joten se ensin aggregoidaan neljännesvuosikeskiarvoiksi
    (vaatii kaikki kolme kuukautta samalta neljännekseltä) ja muutetaan
    sitten neljännesmuutokseksi (u_t - u_{t-1}, prosenttiyksikköä).

    BKT:n viiveet lasketaan täydestä, vuodesta 1990 alkavasta
    BKT-sarjasta ennen työttömyysaineistoon yhdistämistä, jotta viiveiden
    lisääminen ei turhaan lyhennä lopullista otosta (viiveille riittää
    historiaa jo ennen työttömyysaineiston alkua v. 2010).

    Palauttaa DataFramen sarakkeilla ``bkt_kasvu_qoq_L0`` (kontemporaani-
    nen) ... ``bkt_kasvu_qoq_L{maksimiviive}`` sekä
    ``tyottomyysasteen_muutos_qoq``.
    """
    bkt_qoq = hae_bkt_kasvu_qoq()
    viiveet = {
        f"bkt_kasvu_qoq_L{i}": bkt_qoq.shift(i) for i in range(maksimiviive + 1)
    }
    bkt_viiveet = pd.DataFrame(viiveet)

    tyottomyys_kk = hae_tyottomyysaste_kausitasoitettu_kk()

    kuukausiryhma = tyottomyys_kk.resample("Q")
    tyottomyys_q = kuukausiryhma.mean().where(kuukausiryhma.count() == 3)
    tyottomyys_q.index = tyottomyys_q.index.asfreq("Q")
    tyottomyys_q = tyottomyys_q.rename("tyottomyysaste_kausi_q")

    tyottomyys_muutos_qoq = (tyottomyys_q - tyottomyys_q.shift(1)).rename(
        "tyottomyysasteen_muutos_qoq"
    )

    df = pd.concat([bkt_viiveet, tyottomyys_q, tyottomyys_muutos_qoq], axis=1)
    df = df.sort_index()
    vaaditut_sarakkeet = list(viiveet.keys()) + ["tyottomyysasteen_muutos_qoq"]
    df = df.dropna(subset=vaaditut_sarakkeet)
    return df
