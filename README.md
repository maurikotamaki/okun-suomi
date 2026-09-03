# okun-suomi

Okunin lain estimointi Suomen aineistolla: kuinka BKT:n volyymin kasvu
liittyy työttömyysasteen muutokseen. Data haetaan ajossa suoraan
Tilastokeskuksen [PxWeb-rajapinnasta](https://pxdata.stat.fi/) — mitään
lukuja ei ole kovakoodattu tai simuloitu koodiin.

## Rakenne

```
okun_suomi/
  datahaku.py   # PxWeb-rajapinnasta datan hakeva moduuli (v/v- ja q/q-sarjat)
  analyysi.py   # OLS-regressio, HAC/DW/BG-diagnostiikka, otosvertailut, kuvaajat
main.py         # ajaa koko putken: haku -> yhdistäminen -> regressio -> robustisuus -> kuvat
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

### Onko taulukossa 137h katkos vuoden 2021 uudistuksen kohdalla?

Ei — **taulukon 137h sisällä ei ole katkosta**. Sekä 137h:n että sen
kuukausivastineen (135z) metatiedoissa Tilastokeskus toteaa suoraan:

> "Työvoimatutkimus on uudistettu vuoden 2021 alussa. Taulukko sisältää
> uuden estimointimenetelmän mukaisiksi **takautuvasti korjatut**
> aikasarjat, jotka eivät ole vertailukelpoisia aiempien vuosien tietojen
> kanssa. Tämä taulukko 137h korvaa taulukon 11c8, joka on siirretty
> arkistokantaan."

Toisin sanoen: koko taulukon 137h julkaistu aikaväli (2009Q1 lähtien)
on laskettu **yhdellä ja samalla**, uuden (2021) menetelmän mukaisella
tavalla — vuoden 2021 kohdalla ei siis ole metodologista hyppyä sarjan
sisällä, koska myös 2009–2020 on korjattu jälkikäteen vastaamaan uutta
menetelmää. Katkos on sen sijaan taulukon **rajalla**: vanhempi,
alkuperäisellä (pre-2021) menetelmällä laskettu sarja on eri taulukossa
(11c8, StatFin_Passiivi, 1989Q1–2020Q4), eikä sitä Tilastokeskuksen oman
ilmoituksen mukaan pidä yhdistää 137h:n kanssa. Juuri tästä syystä tässä
projektissa käytetään yksinomaan taulukkoa 137h eikä yhdistetä sitä
arkistoituun 11c8:aan (ks. yllä "Miksi työttömyysaste alkaa vasta
2009/2010?").

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
2. OLS-regressiotulokset alkuperäiselle spesifikaatiolle (kertoimet,
   keskivirheet, t- ja p-arvot, R², kynnyskasvu),
3. robustisuustarkastelun: HAC-keskivirheet ja autokorrelaatiodiagnostiikka,
   otosvertailutaulukon ja vaihtoehtoisen neljännesmuutos-spesifikaation
   (ks. alla "Robustisuustarkastelu"),

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
Kynnyskasvu -a/b:    1.632 % (BKT:n kasvuvauhti, jolla työttömyysaste ei muutu)
```

Kerroin on tilastollisesti merkitsevä ja etumerkiltään Okunin lain
mukainen (negatiivinen), mutta selitysaste on matala — Suomen
työttömyysasteen vaihtelusta valtaosa selittyy muilla tekijöillä kuin
pelkällä BKT:n kasvulla. Koska data haetaan rajapinnasta joka ajokerralla,
tarkat luvut päivittyvät Tilastokeskuksen datan päivittyessä.

## Robustisuustarkastelu

Alkuperäistä spesifikaatiota ei ole poistettu — `okun_suomi/analyysi.py`
sisältää edelleen `estimoi_okunin_laki`/`tulosta_tulokset` ennallaan,
ja `main.py` ajaa alla kuvatut tarkastelut sen **rinnalla**.

### 1. HAC (Newey–West) -keskivirheet, Durbin–Watson, Breusch–Godfrey

Peräkkäiset vuosimuutokset (`u_t - u_{t-4}` neljänneksiltä t ja t-1)
jakavat kolme neljästä termistään, mikä synnyttää mekaanisesti MA(3)-
tyyppisen autokorrelaation jäännöksiin. Tavalliset OLS-keskivirheet eivät
ota tätä huomioon, joten niiden rinnalle lasketaan Newey–West-keskivirheet
(viiveitä vähintään 4, nyrkkisääntönä `floor(4·(T/100)^(2/9))`), sekä
Durbin–Watson- ja Breusch–Godfrey-testit tavallisen OLS:n jäännöksille:

```
Termi               Kerroin      OLS-SE      HAC-SE     HAC t     HAC p
const                0.2397      0.1103      0.1817     1.319    0.1871
bkt_kasvu           -0.1469      0.0471      0.0222    -6.612    0.0000
----------------------------------------------------------------------
Durbin–Watson:             0.466  (2.0 = ei autokorrelaatiota; <2 viittaa positiiviseen)
Breusch–Godfrey (L=4):  LM=39.130, p=0.0000  (H0: ei jäljellä olevaa autokorrelaatiota)
```

Durbin–Watson (0.47) ja Breusch–Godfrey (p≈0) vahvistavat odotetun,
voimakkaan positiivisen autokorrelaation — päällekkäiset vuosimuutokset
eivät siis ole tilastollisesti harmittomia, ja tavallisten OLS-
keskivirheiden sijaan pitäisi tukeutua HAC-versioon.

Huomionarvoista: vakiotermin HAC-keskivirhe on suurempi kuin OLS-
keskivirhe (odotetusti, positiivisen autokorrelaation vuoksi), mutta
BKT-kertoimen HAC-keskivirhe on pienempi kuin OLS-keskivirhe. Tämä ei ole
virhe — se johtuu siitä, että HAC korjaa selittäjän ja jäännöksen
**yhteisautokovarianssia** (score-prosessia `x_t·e_t`), ei pelkästään
jäännöksen omaa autokorrelaatiota, ja koska myös BKT-kasvu itse on
vahvasti autokorreloitunut (vuosimuutos), tulos voi mennä kumpaankin
suuntaan. Tulos on vakaa eri viivemäärillä (L=1…10 antaa BKT-kertoimen
HAC-keskivirheeksi 0.021–0.033), joten kyse ei ole L=4:n sattumasta.

### 2. Otosvertailu: koko aineisto / ilman 2020–2021 / covid-dummy

Sama v/v-spesifikaatio kolmella otoksella, keskivirheet HAC:

```
Malli                                 Vakio a   BKT-kerroin b   Covid-dummy      R²     N   -a/b (%)
----------------------------------------------------------------------------------------------------
Koko aineisto (v/v)             0.240 (0.182)  -0.147 (0.022)             –  0.1318    66      1.632
Ilman 2020–2021                 0.206 (0.205)  -0.143 (0.032)             –  0.0881    58      1.445
Covid-dummy mukana              0.206 (0.202)  -0.142 (0.026) 0.248 (0.308)  0.1400    66      1.446
```

Johtopäätös: koronavuodet eivät ajaa tulosta. BKT-kerroin pysyy lähes
muuttumattomana (-0.147 → -0.143/-0.142) riippumatta siitä, poistetaanko
2020–2021 kokonaan vai kontrolloidaanko niiden vaikutus dummy-muuttujalla.
Covid-dummyn oma kerroin (0.248) ei ole tilastollisesti merkitsevä
(HAC-keskivirhe 0.308) — koronashokki näkyy siis pääasiassa suurina
BKT- ja työttömyysheilahteluina, ei systemaattisena tasosiirtymänä sen
jälkeen, kun BKT:n vaikutus on jo kontrolloitu.

### 3. Vaihtoehtoinen spesifikaatio: neljännesmuutokset (q/q)

Vuosimuutosten sijaan malli estimoidaan myös kausitasoitetuilla
**neljännesmuutoksilla**: BKT:n kausitasoitettu volyymin muutos
edellisneljänneksestä (`StatFin/ntp/132h.px`, sisältökoodi
`vol_kk_kausitvv2015`) selittäjänä ja kausitasoitetun työttömyysasteen
neljännesmuutos selitettävänä. Kausitasoitettu työttömyysaste on
saatavilla vain kuukausitasolla (`StatFin/tyti/135z.px`, "kausitasoitettu
sarja"), joten se aggregoidaan neljännesvuosikeskiarvoiksi ennen
erotuksen laskemista.

```
Termi               Kerroin      OLS-SE      HAC-SE     HAC t     HAC p
const                0.0438      0.0476      0.0542     0.808    0.4194
bkt_kasvu_qoq       -0.0830      0.0372      0.0320    -2.596    0.0094
----------------------------------------------------------------------
Durbin–Watson:             1.928  (2.0 = ei autokorrelaatiota)
Breusch–Godfrey (L=3):  LM=4.362, p=0.2249  (ei viitettä jäännösautokorrelaatiosta)
```

Kerroin on edelleen negatiivinen ja tilastollisesti merkitsevä (p≈0.01),
mutta itseisarvoltaan pienempi kuin v/v-spesifikaatiossa — odotettua,
koska yhden neljänneksen BKT-shokki ehtii vaikuttaa työttömyyteen vasta
osittain saman neljänneksen aikana. Durbin–Watson (1.93) ja
Breusch–Godfrey (p=0.22) osoittavat, ettei jäännöksissä ole enää
merkittävää autokorrelaatiota — tämä vahvistaa, että v/v-spesifikaation
voimakas autokorrelaatio (DW=0.47) johtuu nimenomaan vuosimuutosten
päällekkäisyydestä eikä esimerkiksi puuttuvista selittäjistä.

### 4. Kynnyskasvu (-a/b) kaikissa spesifikaatioissa

BKT:n kasvuvauhti, jolla työttömyysaste ei (mallin pistesuureiden mukaan)
muutu:

| Spesifikaatio | Kynnyskasvu, % |
|---|---|
| Alkuperäinen / koko aineisto (v/v) | 1.63 |
| Ilman 2020–2021 (v/v) | 1.45 |
| Covid-dummy, ei-covid-tila (v/v) | 1.45 |
| Neljännesmuutokset (q/q) | 0.53 |

V/v-spesifikaatioiden kynnyskasvu (~1.4–1.6 %) on yhdenmukainen ja
lähellä Suomen pitkän aikavälin trendikasvua. Q/q-spesifikaation
matalampi kynnyskasvu (0.53 %) on odotettu seuraus siitä, että yhden
neljänneksen kerroin on itsessään pienempi (osa BKT-shokin vaikutuksesta
työttömyyteen realisoituu vasta myöhemmillä neljänneksillä, jotka v/v-
spesifikaatiossa ovat implisiittisesti mukana neljän neljänneksen
ikkunassa). Lukuja ei pidä tulkita tarkkoina ennusteina — kyse on
pistesuureista ilman epävarmuusväliä.

**Huom:** koska data haetaan rajapinnasta joka ajokerralla ja
Tilastokeskus päivittää sekä uusimpia neljänneksiä että joskus
takautuvia tarkistuksia, tässä esitetyt luvut (ajettu 2026-09-03) voivat
poiketa hieman siitä, mitä `python main.py` tulostaa myöhemmin ajettuna.
