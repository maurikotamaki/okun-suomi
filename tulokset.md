# Okunin lain analyysin tulokset — Suomi

- **Ajettu:** 2026-10-01 11:25:38 UTC
- **Datan viimeinen havainto (v/v-aineisto):** 2026Q2
- **Datan viimeinen havainto (q/q-aineisto):** 2026Q2
- **Lähde:** Tilastokeskuksen PxWeb-rajapinta (StatFin), haettu ajonaikaisesti — ei kovakoodattua tai simuloitua dataa.
- Tämä tiedosto on generoitu automaattisesti komennolla `python main.py` (ks. `okun_suomi/raportti.py`). Älä muokkaa käsin — muutokset ylikirjoittuvat seuraavalla ajolla. Committoi tiedosto versionhallintaan, jotta tulosten muutokset näkyvät diffinä.

---
## 1. Alkuperäinen spesifikaatio (v/v, OLS)

Malli: `Δtyöttömyysaste_t = a + b · BKT_kasvu_t + e_t` (Δtyöttömyysaste = muutos vuodentakaisesta, %-yks.; BKT_kasvu = volyymin muutos vuodentakaisesta, %)

Aikaväli: 2010Q1 – 2026Q2  N = 66

| Termi | Kerroin | Keskivirhe | t-arvo | p-arvo |
|---|---:|---:|---:|---:|
| Vakio (a) | 0.2368 | 0.1107 | 2.139 | 0.0363 |
| BKT-kasvu (b) | -0.1437 | 0.0474 | -3.033 | 0.0035 |

- Selitysaste R²: 0.1256
- Kynnyskasvu -a/b: **1.648 %/vuosi** (BKT:n kasvuvauhti, jolla työttömyysaste ei muutu)

## 2. Robustisuustarkastelu

### 2.1 Koko aineisto (v/v)

N = 66, selittäjiä (vakio mukaan lukien) k = 2, vapausasteet df_resid = N-k = 64

| Termi | Kerroin | OLS-SE | NW-SE | AM-SE (esivalk.) |
|---|---:|---:|---:|---:|
| const | 0.2368 | 0.1107 | 0.1831 | 0.2880 |
| bkt_kasvu | -0.1437 | 0.0474 | 0.0217 | 0.0262 |

- Newey–West-viiveet L = 4; Andrews–Monahan-esivalkaisun jälkeiset viiveet L = 3
- Päätulokseksi valittu (konservatiivisin): **Andrews–Monahan (esivalk.)** (suurempi SE kahdesta HAC-vaihtoehdosta BKT-kasvun kokonaisvaikutukselle)
- Durbin–Watson: 0.459 (2.0 = ei autokorrelaatiota; <2 → positiivinen)
- Breusch–Godfrey (L=4): LM=39.535, p=0.0000 (H0: ei jäljellä olevaa autokorrelaatiota)
- Kynnyskasvu -a/Σb: **1.648 %/vuosi**

### 2.2 Otosvertailu: koko aineisto / ilman 2020–2021 / covid-dummy

Keskivirheet ovat kunkin mallin konservatiivisimman HAC-vaihtoehdon mukaisia (suluissa on keskivirhe kertoimen jälkeen); -a/Σb on annualisoitu.

| Malli | Vakio a (SE) | BKT-kerroin b (SE) | Covid-dummy (SE) | R² | N | -a/Σb, %/v |
|---|---:|---:|---:|---:|---:|---:|
| Koko aineisto (v/v) | 0.237 (0.288) | -0.144 (0.026) | – | 0.1256 | 66 | 1.648 |
| Ilman 2020–2021 | 0.201 (0.297) | -0.137 (0.039) | – | 0.0810 | 58 | 1.464 |
| Covid-dummy mukana | 0.203 (0.315) | -0.139 (0.027) | 0.250 (0.424) | 0.1340 | 66 | 1.457 |

### 2.3 Kausitasoituksen varmistus (q/q-sarjat)

PxWeb-metatiedoista (GET-pyyntö taulukon metatietoihin ajon aikana) haettu ja tarkistettu, että kummankin sarjan selite mainitsee kausitasoituksen.

| Muuttuja | Taulukko | Sisältökoodi | PxWeb-selite |
|---|---|---|---|
| BKT:n neljännesmuutos (bkt_kasvu_qoq_L*) | `https://pxdata.stat.fi/PxWeb/api/v1/fi/StatFin/ntp/132h.px` | `vol_kk_kausitvv2015` | Kausitasoitetun ja työpäiväkorjatun sarjan volyymin muutos edellisneljänneksestä, % |
| Työttömyysasteen taso, josta q/q-muutos lasketaan | `https://pxdata.stat.fi/PxWeb/api/v1/fi/StatFin/tyti/135z.px` | `Tyottaste_kausi` | Työttömyysaste, %, kausitasoitettu sarja |

### 2.4 Neljännesmuutokset, viiveet 0-4 (q/q)

N = 65, selittäjiä (vakio mukaan lukien) k = 6, vapausasteet df_resid = N-k = 59

| Termi | Kerroin | OLS-SE | NW-SE | AM-SE (esivalk.) |
|---|---:|---:|---:|---:|
| const | 0.1053 | 0.0483 | 0.0452 | 0.0414 |
| bkt_kasvu_qoq_L0 | -0.1035 | 0.0363 | 0.0322 | 0.0313 |
| bkt_kasvu_qoq_L1 | -0.1000 | 0.0371 | 0.0338 | 0.0363 |
| bkt_kasvu_qoq_L2 | -0.0764 | 0.0367 | 0.0251 | 0.0253 |
| bkt_kasvu_qoq_L3 | -0.0246 | 0.0371 | 0.0227 | 0.0229 |
| bkt_kasvu_qoq_L4 | -0.0783 | 0.0360 | 0.0237 | 0.0220 |

- Newey–West-viiveet L = 3; Andrews–Monahan-esivalkaisun jälkeiset viiveet L = 3
- Päätulokseksi valittu (konservatiivisin): **Andrews–Monahan (esivalk.)** (suurempi SE kahdesta HAC-vaihtoehdosta BKT-kasvun kokonaisvaikutukselle)
- Durbin–Watson: 2.153 (2.0 = ei autokorrelaatiota; <2 → positiivinen)
- Breusch–Godfrey (L=3): LM=3.479, p=0.3235 (H0: ei jäljellä olevaa autokorrelaatiota)
- BKT-kasvun pitkän aikavälin vaikutus (Σb, 5 viivettä, Andrews–Monahan (esivalk.)-SE): Σb = -0.3829, SE = 0.0811, t = -4.724, p = 0.0000
- Viiveiden yhteismerkitsevyys (Wald F, H0: kaikki BKT-viiveiden kertoimet = 0): F(5,59) = 9.700, p = 0.0000
- Kynnyskasvu -a/Σb: 0.275 %/neljännes → annualisoituna **1.105 %/vuosi**

### 2.5 Jäännösten kausivaihtelutesti

Malli: Neljännesmuutokset, viiveet 0-4 (q/q). Apuregressio: OLS-jäännös ~ vakio + Q2 + Q3 + Q4 (Q1 = referenssi).

| Termi | Kerroin | SE | t | p |
|---|---:|---:|---:|---:|
| const | -0.0074 | 0.0864 | -0.086 | 0.9319 |
| Q_2 | -0.0468 | 0.1204 | -0.389 | 0.6987 |
| Q_3 | 0.0876 | 0.1222 | 0.717 | 0.4762 |
| Q_4 | -0.0077 | 0.1222 | -0.063 | 0.9499 |

Yhteismerkitsevyys (F-testi, H0: ei kausivaihtelua jäännöksissä): F(3,61) = 0.439, p = 0.7258

**p ≥ 0.05: ei tilastollista näyttöä jäljellä olevasta kausivaihtelusta** jäännöksissä.

## 3. Kynnyskasvu -a/Σb kaikissa spesifikaatioissa, annualisoituna

BKT:n kasvuvauhti (%/vuosi), jolla työttömyysaste ei muutu. q/q-mallien neljänneskohtainen kynnys annualisoidaan korkoa korolle -periaatteella `(1+g/100)^4 - 1`.

| Spesifikaatio | Alkuperäinen yksikkö | Kynnyskasvu, %/vuosi |
|---|---|---:|
| Alkuperäinen (v/v, OLS, ei-robusti) | v/v | 1.648 |
| Koko aineisto (v/v, konservatiivinen HAC) | v/v | 1.648 |
| Ilman 2020–2021 (v/v, konservatiivinen HAC) | v/v | 1.464 |
| Covid-dummy, ei-covid-tila (v/v, konservatiivinen HAC) | v/v | 1.457 |
| Neljännesmuutokset, Σb viiveille 0-4 (q/q, konservatiivinen HAC) | q/q | 1.105 |
