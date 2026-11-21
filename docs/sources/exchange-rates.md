# Source: exchange rates (`fx_rates`)

Open item 5 of the UML model. RN-07 and RP-09(f): every amount has a currency, and conversion to the profile currency uses a dated rate with a source, shown next to the result.

Date of the spike: 2026-11-20.

## Summary

- Compared three official, free sources: **ECB** euro reference rates, **Banco Central do Brasil PTAX**, **Federal Reserve H.10**.
- **Recommendation: ECB as the single primary source.** It covers every currency we need now and later (USD, BRL, CAD, GBP, AUD, EUR, and ~25 more), has a stable SDMX API with no key, and allows reuse with attribution. Any pair is computed as a cross through EUR on the same day.
- **PTAX is the natural second source** if the product must match the official Brazilian rate for BRL profiles. In the test week the ECB cross differed from PTAX by −0.47% to +0.14% (table below).
- H.10 covers the right currencies but we could not call it by machine during the spike (Fed site in maintenance; FRED API needs a key).

## Comparison

| | ECB euro reference rates | BCB PTAX (Olinda) | Federal Reserve H.10 |
|---|---|---|---|
| Endpoint | `https://data-api.ecb.europa.eu/service/data/EXR/D.{CUR}.EUR.SP00.A` | `https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/` (`Moedas`, `CotacaoMoedaPeriodo`, `CotacaoDolarPeriodo`...) | `https://www.federalreserve.gov/releases/h10/current/` (page); Data Download Program `https://www.federalreserve.gov/datadownload/` (CSV); FRED series such as `DEXBZUS` |
| Base | 1 EUR = x currency | 1 unit of currency = x BRL (also *paridade* against USD) | currency units per 1 USD; USD per unit for AUD, EUR, NZD, GBP |
| Currencies | 29 against EUR on 2026-11-20, BRL included | 10: AUD, CAD, CHF, DKK, EUR, GBP, JPY, NOK, SEK, USD (from the `Moedas` endpoint) | 23 currencies, Brazil included, plus broad/AFE/EME indexes |
| Frequency | daily, around 16:00 CET on TARGET working days | daily, Brazilian business days: opening, intermediate and closing bulletins; closing = mean of the day's four dealer polls | daily values, published weekly (latest: 2026-11-16) |
| Format | SDMX: CSV (`format=csvdata`), JSON, XML | OData: JSON, XML, CSV | HTML, CSV (DDP); JSON/CSV via FRED API |
| History | daily since the euro's launch (1999); start date not tested | period queries work; earliest date not tested | not tested |
| Key | no | no | DDP: no. FRED API: yes (`api_key` required, HTTP 400 without it) |
| Terms | "free use of the information ... the ECB must be cited as the source"; modifications must be stated. Rates are "for information purposes only"; "using the rates for transaction purposes is strongly discouraged" | Dataset license: Open Data Commons Open Database License (ODbL) (dadosabertos.bcb.gov.br) | US federal data; terms not checked |
| Spike result | **works** (HTTP 200) | **works** (HTTP 200) | DDP returned a maintenance page (HTTP 503); FRED CSV timed out; FRED API needs a key |

## Real calls (2026-11-20)

ECB, five currencies, one week:

```
GET https://data-api.ecb.europa.eu/service/data/EXR/D.USD+BRL+CAD+GBP+AUD.EUR.SP00.A?startPeriod=2026-11-16&endPeriod=2026-11-20&format=csvdata
```

Selected rows (1 EUR = x):

| Date | USD | BRL | CAD | GBP | AUD |
|---|---|---|---|---|---|
| 2026-11-19 | 1.0992 | 6.4765 | 1.5719 | 0.83581 | 1.6378 |
| 2026-11-20 | 1.099 | 6.5259 | 1.5723 | 0.83735 | 1.6487 |

BCB PTAX, USD, same week (closing bulletin, selling rate):

```
GET https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@moeda='USD'&@dataInicial='11-16-2026'&@dataFinalCotacao='11-20-2026'&$format=json
```

USD → BRL, ECB cross (EUR/BRL ÷ EUR/USD, 4 decimals) vs PTAX selling:

| Date | ECB cross | PTAX sell | Difference |
|---|---|---|---|
| 2026-11-16 | 5.7053 | 5.7324 | −0.0271 |
| 2026-11-17 | 5.7821 | 5.7851 | −0.0030 |
| 2026-11-18 | 5.8186 | 5.8102 | +0.0084 |
| 2026-11-19 | 5.8920 | 5.8889 | +0.0031 |
| 2026-11-20 | — | no rate | Brazilian national holiday (Black Consciousness Day); ECB published |

Each source has gaps on its own holidays. The lookup must take the latest rate **on or before** the requested date and show that date.

## Mapping to `fx_rates`

The table already has `base`, `quote`, `rate`, `on_date`, `source_url`. Proposal:

- Store the rows exactly as published: ECB as `base = EUR`, `quote = USD|BRL|...`; PTAX as `base = USD|EUR|...`, `quote = BRL`. Do not store derived cross rates.
- Add `source` (`ecb`, `bcb_ptax`) and, for PTAX, `rate_type` (`sell`/`buy`) or store only the selling rate. Unique key `(source, base, quote, on_date)`.
- `source_url` = the API query used (as in the script) or the human page of the source.
- `CostEstimate.fx_used` lists both legs of a cross (EUR/USD and EUR/BRL of the same day), so the user sees what was used.
- Use `numeric` for `rate` (the ECB publishes up to 5 significant decimals, e.g. GBP 0.83305) and `Decimal` in Python.

## Update frequency (proposal)

A daily job after 16:00 CET (ECB) that loads the last 10 days (idempotent upsert, covers holidays and late fixes). One request per day is enough. A first load can pull the full history in one call per currency group.

## Limitations

- ECB rates are reference rates, not transaction rates. That is fine for an estimate, but the UI must say "estimated with the ECB reference rate of <date>".
- Crosses through EUR are not identical to the local official rate (up to ~0.5% in the test week).
- PTAX only quotes against BRL. It does not serve a profile in another currency.
- The ECB list may not cover every profile currency a future user wants. Check the 29 currencies before promising a currency in the profile.

## Needs a human decision

1. ECB only, or ECB plus PTAX for BRL profiles.
2. Selling or buying rate when PTAX is used (the script uses selling).
3. Whether to add `source` (and `rate_type`) to `fx_rates` in the UML.

## Files

- Script: `spikes/fx/fx_probe.py` (`python3 -I spikes/fx/fx_probe.py spikes/_raw/fx 2026-11-16 2026-11-20`)
- Raw: `spikes/_raw/fx/ecb_2026-11-16_2026-11-20.csv`, `spikes/_raw/fx/bcb_ptax_{USD,EUR,CAD,GBP,AUD}_2026-11-16_2026-11-20.json`, `spikes/_raw/fx/bcb_moedas.json`
