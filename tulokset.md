# Okunin lain analyysin tulokset — Suomi

- **Ajettu:** 2026-09-03 19:08:21 UTC
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
| Vakio (a) | 0.2397 | 0.1103 | 2.172 | 0.0335 |
| BKT-kasvu (b) | -0.1469 | 0.0471 | -3.117 | 0.0027 |

- Selitysaste R²: 0.1318
- Kynnyskasvu -a/b: **1.632 %/vuosi** (BKT:n kasvuvauhti, jolla työttömyysaste ei muutu)

## 2. Robustisuustarkastelu

### 2.1 Koko aineisto (v/v)

N = 66, selittäjiä (vakio mukaan lukien) k = 2, vapausasteet df_resid = N-k = 64

| Termi | Kerroin | OLS-SE | NW-SE | AM-SE (esivalk.) |
|---|---:|---:|---:|---:|
| const | 0.2397 | 0.1103 | 0.1817 | 0.2830 |
| bkt_kasvu | -0.1469 | 0.0471 | 0.0222 | 0.0270 |

- Newey–West-viiveet L = 4; Andrews–Monahan-esivalkaisun jälkeiset viiveet L = 3
- Päätulokseksi valittu (konservatiivisin): **Andrews–Monahan (esivalk.)** (suurempi SE kahdesta HAC-vaihtoehdosta BKT-kasvun kokonaisvaikutukselle)
- Durbin–Watson: 0.466 (2.0 = ei autokorrelaatiota; <2 → positiivinen)
- Breusch–Godfrey (L=4): LM=39.130, p=0.0000 (H0: ei jäljellä olevaa autokorrelaatiota)
- Kynnyskasvu -a/Σb: **1.632 %/vuosi**

### 2.2 Otosvertailu: koko aineisto / ilman 2020–2021 / covid-dummy

Keskivirheet ovat kunkin mallin konservatiivisimman HAC-vaihtoehdon mukaisia (suluissa on keskivirhe kertoimen jälkeen); -a/Σb on annualisoitu.

| Malli | Vakio a (SE) | BKT-kerroin b (SE) | Covid-dummy (SE) | R² | N | -a/Σb, %/v |
|---|---:|---:|---:|---:|---:|---:|
| Koko aineisto (v/v) | 0.240 (0.283) | -0.147 (0.027) | – | 0.1318 | 66 | 1.632 |
| Ilman 2020–2021 | 0.206 (0.296) | -0.143 (0.040) | – | 0.0881 | 58 | 1.445 |
| Covid-dummy mukana | 0.206 (0.313) | -0.142 (0.029) | 0.248 (0.423) | 0.1400 | 66 | 1.446 |

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
| const | 0.1066 | 0.0474 | 0.0451 | 0.0415 |
| bkt_kasvu_qoq_L0 | -0.1100 | 0.0359 | 0.0322 | 0.0312 |
| bkt_kasvu_qoq_L1 | -0.0905 | 0.0367 | 0.0353 | 0.0381 |
| bkt_kasvu_qoq_L2 | -0.0747 | 0.0362 | 0.0244 | 0.0243 |
| bkt_kasvu_qoq_L3 | -0.0222 | 0.0367 | 0.0217 | 0.0218 |
| bkt_kasvu_qoq_L4 | -0.0805 | 0.0357 | 0.0240 | 0.0225 |

- Newey–West-viiveet L = 3; Andrews–Monahan-esivalkaisun jälkeiset viiveet L = 3
- Päätulokseksi valittu (konservatiivisin): **Andrews–Monahan (esivalk.)** (suurempi SE kahdesta HAC-vaihtoehdosta BKT-kasvun kokonaisvaikutukselle)
- Durbin–Watson: 2.115 (2.0 = ei autokorrelaatiota; <2 → positiivinen)
- Breusch–Godfrey (L=3): LM=3.999, p=0.2616 (H0: ei jäljellä olevaa autokorrelaatiota)
- BKT-kasvun pitkän aikavälin vaikutus (Σb, 5 viivettä, Andrews–Monahan (esivalk.)-SE): Σb = -0.3779, SE = 0.0787, t = -4.803, p = 0.0000
- Viiveiden yhteismerkitsevyys (Wald F, H0: kaikki BKT-viiveiden kertoimet = 0): F(5,59) = 9.762, p = 0.0000
- Kynnyskasvu -a/Σb: 0.282 %/neljännes → annualisoituna **1.133 %/vuosi**

### 2.5 Jäännösten kausivaihtelutesti

Malli: Neljännesmuutokset, viiveet 0-4 (q/q). Apuregressio: OLS-jäännös ~ vakio + Q2 + Q3 + Q4 (Q1 = referenssi).

| Termi | Kerroin | SE | t | p |
|---|---:|---:|---:|---:|
| const | -0.0049 | 0.0851 | -0.058 | 0.9541 |
| Q_2 | -0.0280 | 0.1185 | -0.237 | 0.8137 |
| Q_3 | 0.0715 | 0.1203 | 0.594 | 0.5546 |
| Q_4 | -0.0217 | 0.1203 | -0.181 | 0.8573 |

Yhteismerkitsevyys (F-testi, H0: ei kausivaihtelua jäännöksissä): F(3,61) = 0.291, p = 0.8316

**p ≥ 0.05: ei tilastollista näyttöä jäljellä olevasta kausivaihtelusta** jäännöksissä.

## 3. Kynnyskasvu -a/Σb kaikissa spesifikaatioissa, annualisoituna

BKT:n kasvuvauhti (%/vuosi), jolla työttömyysaste ei muutu. q/q-mallien neljänneskohtainen kynnys annualisoidaan korkoa korolle -periaatteella `(1+g/100)^4 - 1`.

| Spesifikaatio | Alkuperäinen yksikkö | Kynnyskasvu, %/vuosi |
|---|---|---:|
| Alkuperäinen (v/v, OLS, ei-robusti) | v/v | 1.632 |
| Koko aineisto (v/v, konservatiivinen HAC) | v/v | 1.632 |
| Ilman 2020–2021 (v/v, konservatiivinen HAC) | v/v | 1.445 |
| Covid-dummy, ei-covid-tila (v/v, konservatiivinen HAC) | v/v | 1.446 |
| Neljännesmuutokset, Σb viiveille 0-4 (q/q, konservatiivinen HAC) | q/q | 1.133 |
