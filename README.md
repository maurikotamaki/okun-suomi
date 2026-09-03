# okun-suomi

Okunin lain estimointi Suomen aineistolla: kuinka BKT:n volyymin kasvu
liittyy työttömyysasteen muutokseen. Data haetaan ajossa suoraan
Tilastokeskuksen [PxWeb-rajapinnasta](https://pxdata.stat.fi/) — mitään
lukuja ei ole kovakoodattu tai simuloitu koodiin.

## Rakenne

```
okun_suomi/
  datahaku.py   # PxWeb-rajapinnasta datan hakeva moduuli
  analyysi.py   # Okunin lain OLS-regressio ja kuvaajat
main.py         # ajaa koko putken: haku -> yhdistäminen -> regressio -> kuvat
requirements.txt
kuvat/          # tähän tallentuvat piirretyt kuvat (aikasarjat.png, hajontakuvio.png)
```

## Käytetty data

Rajapinnan oikea polku selvitettiin kokeilemalla (`https://pxdata.stat.fi/api/v1/...`
palauttaa 404 — oikea juuri on `https://pxdata.stat.fi/PxWeb/api/v1/fi/...`).

| Sarja | Taulukko | Rajaus | Sisältö |
|---|---|---|---|
| BKT:n volyymin kasvu | `StatFin/ntp/132h.px` | taloustoimi `B1GMH` (BKT markkinahintaan), `vol_vv_tyopvv2015` | Työpäiväkorjatun sarjan volyymin muutos vuodentakaisesta, % |
| Työttömyysaste | `StatFin/tyti/137h.px` | sukupuoli `SSS` (koko väestö), ikäryhmä `15-74` | Työttömyysaste, % |

Molemmat ovat neljännesvuositason, kausivaihtelultaan siistiytyviä
**vuosimuutossarjoja** (verrataan aina samaan neljännekseen vuotta
aiemmin) — tämä poistaa kausivaihtelun ilman erillistä kausitasoitusta ja
mahdollistaa suoraan vertailukelpoisten sarjojen käytön.

### Miksi työttömyysaste alkaa vasta 2009/2010?

BKT-sarja on saatavilla StatFinissä vuodesta 1990 lähtien, mutta
työvoimatutkimus **uudistettiin vuoden 2021 alussa**, ja Tilastokeskus
toteaa StatFin-taulukon 137h metatiedoissa nimenomaisesti, että sen
takautuvasti korjatut sarjat (2009Q1 alkaen) **eivät ole
vertailukelpoisia** vanhemman, arkistoituun StatFin_Passiivi-kantaan
siirretyn taulukon 11c8 (1989Q1–2020Q4) kanssa. Jotta lopullinen aikasarja
olisi tehtävänannon mukaisesti **yhtenäinen**, tässä ei yhdistetä kahta eri
menetelmävintagea, vaan käytetään yksinomaan nykyistä, sisäisesti
johdonmukaista taulukkoa 137h. Tämä rajaa käytettävissä olevan, aidosti
yhtenäisen aineiston noin **2010Q1 alkaen** (vuosimuutos vaatii neljä
edeltävää havaintoa), vaikka BKT-sarja itsessään ulottuisi kauemmas.
Rajapinta ja taulukot voi vaihtaa `okun_suomi/datahaku.py`:ssä, jos pidempi
mutta epäyhtenäinen sarja on tarkoituksenmukaisempi johonkin toiseen
käyttötarkoitukseen.

Jos rajapintaan ei ajohetkellä saada yhteyttä tai vastaus on odottamaton,
`datahaku.py` nostaa selkeän poikkeuksen — se ei koskaan korvaa dataa
keksityllä tai simuloidulla aineistolla.

## Malli

Okunin laki estimoidaan muutosten (first-difference) muodossa:

```
Δtyöttömyysaste_t = a + b · BKT_kasvu_t + e_t
```

jossa `Δtyöttömyysaste_t` on työttömyysasteen muutos vuodentakaisesta
(prosenttiyksikköä) ja `BKT_kasvu_t` BKT:n volyymin kasvu vuodentakaisesta
(%). Okunin lain mukaan kerroin `b` on negatiivinen.

## Asennus ja ajo

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Skripti tulostaa:
1. mitä dataa rajapinnasta haettiin (havaintomäärät, aikaväli, näyte),
2. OLS-regressiotulokset (kertoimet, keskivirheet, t- ja p-arvot, R²),

ja tallentaa hakemistoon `kuvat/`:
- `aikasarjat.png` — BKT:n kasvu ja työttömyysasteen muutos samassa
  kuvassa (kaksi y-akselia),
- `hajontakuvio.png` — hajontakuvio BKT-kasvusta ja työttömyysasteen
  muutoksesta OLS-sovitesuoralla.

## Esimerkkitulos

Ajettuna 2026-09-03 aineistolla 2010Q1–2026Q2 (N=66):

```
Termi               Kerroin    Keskivirhe    t-arvo    p-arvo
----------------------------------------------------------------------
Vakio (a)            0.2397        0.1103     2.172    0.0335
BKT-kasvu (b)       -0.1469        0.0471    -3.117    0.0027
----------------------------------------------------------------------
Selitysaste R²:  0.1318
```

Kerroin on tilastollisesti merkitsevä ja etumerkiltään Okunin lain
mukainen (negatiivinen), mutta selitysaste on matala — Suomen
työttömyysasteen vaihtelusta valtaosa selittyy muilla tekijöillä kuin
pelkällä BKT:n kasvulla. Koska data haetaan rajapinnasta joka ajokerralla,
tarkat luvut päivittyvät Tilastokeskuksen datan päivittyessä.
