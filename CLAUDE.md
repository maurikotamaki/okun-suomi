# CLAUDE.md

Ohjeet Claudelle (ja muille avustaville tekoälyille) tässä repossa
työskentelyyn.

## Mitä tämä projekti tekee

Estimoi Okunin lain Suomen aineistolla: kuinka BKT:n volyymin kasvu
liittyy työttömyysasteen muutokseen. `main.py` ajaa koko putken —
datan haku, yhdistäminen, OLS-regressio, robustisuustarkastelu, kuvat ja
`tulokset.md`:n kirjoitus — yhdellä komennolla `python main.py`.

Rakenne:

```
okun_suomi/
  datahaku.py   # PxWeb-rajapinnasta datan hakeva moduuli (v/v- ja q/q-sarjat)
  analyysi.py   # OLS-regressio, HAC/DW/BG-diagnostiikka, otosvertailut, kuvaajat
  raportti.py   # muotoilee tulosoliot Markdownixi ja kirjoittaa tulokset.md:n
main.py         # ajaa koko putken
kuvat/          # piirretyt kuvat (aikasarjat.png, hajontakuvio.png)
tulokset.md     # versionhallittava tuloskooste, ylikirjoittuu joka ajolla
```

Ks. `README.md` tarkempi kuvaus mallista ja robustisuustarkastelusta.

## Ehdoton sääntö: data ei koskaan ole simuloitua eikä sekoita vintagejä

Nämä kaksi periaatetta ovat **ehdottomia** — niitä ei saa rikkoa millään
tekosyyllä (ei edes "väliaikaisesti testausta varten", ei edes jos
rajapinta on tilapäisesti alhaalla):

1. **Dataa ei koskaan korvata simuloidulla, keksityllä tai kovakoodatulla
   aineistolla.** Kaikki luvut haetaan ajonaikaisesti Tilastokeskuksen
   PxWeb-rajapinnasta (`okun_suomi/datahaku.py`). Jos rajapintaan ei
   saada yhteyttä, vastaus ei ole odotetun muotoinen, tai jokin
   sisältökoodi/taulukko ei löydy metatiedoista, oikea toiminta on
   **nostaa poikkeus (`RuntimeError`) ja pysäyttää ajo** — ei koskaan
   palauttaa placeholder-, fallback- tai simuloitua dataa hiljaisesti.
   Tämä koskee sekä `datahaku.py`:n funktioita että mitä tahansa uutta
   koodia, joka lisätään datan hakuun.
2. **Eri menetelmävintagejen sarjoja ei yhdistetä.** Tilastokeskuksen
   työvoimatutkimus uudistettiin 2021 alussa, ja StatFin-taulukko `137h`
   (2009Q1 alkaen) sisältää takautuvasti korjatut sarjat, jotka eivät
   Tilastokeskuksen oman metatietoilmoituksen mukaan ole
   vertailukelpoisia vanhemman, arkistoituun StatFin_Passiivi-kantaan
   siirretyn taulukon `11c8` (1989Q1–2020Q4) kanssa. Tässä projektissa
   käytetään siksi **yksinomaan** taulukkoa `137h`, eikä sitä koskaan
   yhdistetä (esim. pidemmän aikasarjan saamiseksi) taulukkoon `11c8`
   tai muuhun eri menetelmällä laskettuun vintageen. Sama periaate
   pätee yleisemmin: jos jokin StatFin-taulukko ilmoittaa metatiedoissaan
   katkoksen tai menetelmämuutoksen, sen eri puolia ei yhdistetä yhdeksi
   sarjaksi — käytetään vain sisäisesti yhtenäistä osaa, vaikka se
   lyhentäisi käytettävissä olevaa aikaväliä.

Näiden sääntöjen seurauksena aineisto alkaa käytännössä n. 2010Q1:stä
(v/v-spesifikaatio) vaikka BKT-sarja itsessään ulottuisi vuoteen 1990 —
tämä on tarkoituksellista, ei puute.

Jos jokin muutos näyttäisi vaativan jommankumman säännön rikkomista
(esim. "täytetään puuttuva neljännes interpoloimalla" tai "yhdistetään
137h ja 11c8 pidemmän sarjan saamiseksi"), älä tee sitä oma-aloitteisesti
— pysähdy ja kysy käyttäjältä.

## Käytetyt taulukkotunnukset ja sisältökoodit

Rajapinnan juuri: `https://pxdata.stat.fi/PxWeb/api/v1/fi/StatFin`
(huom. `PxWeb`-segmentti — pelkkä `/api/v1/...` palauttaa 404:n).

| Sarja | Taulukko | Rajaukset | Sisältökoodi (`contentscode`) | Kausitasoitus |
|---|---|---|---|---|
| BKT:n volyymin v/v-kasvu | `StatFin/ntp/132h.px` | `taloustoimi=B1GMH` | `vol_vv_tyopvv2015` | ei (työpäiväkorjattu, v/v poistaa kausivaihtelun) |
| BKT:n volyymin q/q-kasvu | `StatFin/ntp/132h.px` | `taloustoimi=B1GMH` | `vol_kk_kausitvv2015` | kyllä (varmistetaan ajonaikaisesti metatiedoista) |
| Työttömyysaste (v/v-spesifikaatio) | `StatFin/tyti/137h.px` | `sukupuoli=SSS`, `ikaryhma=15-74` | `tyti-Tyottomyysaste` | ei |
| Työttömyysaste, kuukausi (q/q-spesifikaatio) | `StatFin/tyti/135z.px` | – | `Tyottaste_kausi` | kyllä (varmistetaan ajonaikaisesti metatiedoista) |

**Ei koskaan käytetä:** `StatFin_Passiivi/tyti/11c8.px` (vanha,
pre-2021-menetelmän työttömyysaste-taulukko) — ks. yllä oleva sääntö
vintagejen yhdistämisestä.

q/q-spesifikaation molempien sarjojen kausitasoitus varmistetaan
ajonaikaisesti PxWeb-metatiedoista (`datahaku.varmista_qoq_kausitasoitus`)
— ei vain oleteta sisältökoodin nimen perusteella. Jos taulukoita,
rajauksia tai sisältökoodeja muutetaan, päivitä myös tämä taulukko ja
README.md:n vastaava kuvaus.

## Muita konventioita

- **Kieli:** koodi, kommentit, tuloste ja dokumentaatio ovat suomeksi
  (muuttuja- ja funktionimet, docstringit, `tulokset.md`, README).
  Pidä uusi koodi samassa tyylissä.
- **Ei verkkokutsuja testien/CI:n aikana ilman tarkoitusta:** rajapintaa
  kutsutaan vain `main.py`:n ajossa (tai vastaavassa tarkoituksellisessa
  skriptissä), ei taustalla tai testien sivuvaikutuksena.
- **Virheenkäsittely:** kaikki `datahaku.py`:n verkko-/jäsennysvirheet
  nostetaan `RuntimeError`-poikkeuksina selkeällä viestillä; `main.py`
  ottaa nämä kiinni ylimmällä tasolla ja tulostaa virheen `stderr`:iin
  palauttaen poistumiskoodin 1 — ei jatka puutteellisella datalla.
- **`tulokset.md` ja `kuvat/`:** näitä ei muokata käsin — ne ylikirjoittaa
  aina `python main.py`:n ajo. Committoi ne sellaisenaan ajon jälkeen,
  jotta git-historia näyttää tulosten muutokset ajojen välillä (esim.
  Tilastokeskuksen datapäivitysten myötä).
- **Robustisuustarkastelun rakenne säilytetään:** `analyysi.py`:n
  alkuperäistä, ei-robustia spesifikaatiota (`estimoi_okunin_laki`) ei
  poisteta uusien lisäysten tieltä — uudet tarkastelut lisätään sen
  rinnalle, ei sijaan.
- **Pitkän aikavälin vaikutus q/q-mallissa:** käytä aina viivekertoimien
  summaa (Σb), ei pelkkää kontemporaanista kerrointa (b₀), ja annualisoi
  kynnyskasvut korkoa korolle -periaatteella (`(1+g)^4 - 1`), ei
  kertomalla neljällä, kun v/v- ja q/q-tuloksia verrataan keskenään.
