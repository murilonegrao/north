"""FX spike: fetch the same days from the ECB (SDMX API) and the Banco Central
do Brasil (PTAX, Olinda OData API) and compare USD->BRL.

Each output row has the shape of the `fx_rates` table:
base, quote, rate, on_date, source_url  (1 base = rate quote).

Usage: python3 -I spikes/fx/fx_probe.py <raw_dir> [start YYYY-MM-DD] [end YYYY-MM-DD]
Example: python3 -I spikes/fx/fx_probe.py spikes/_raw/fx 2026-11-16 2026-11-20
Standard library only. Downloaded files are read as data, never executed.
"""

import csv
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

UA = "north-research-spike"
ECB = "https://data-api.ecb.europa.eu/service/data/EXR/D.{cur}.EUR.SP00.A"
BCB = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
       "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,"
       "dataFinalCotacao=@dataFinalCotacao)")
CURRENCIES = ["USD", "BRL", "CAD", "GBP", "AUD"]

_last = {}


def get(url):
    """GET with a generic UA and at most 1 request per second per host."""
    host = urllib.parse.urlparse(url).netloc
    wait = 1.1 - (time.monotonic() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    _last[host] = time.monotonic()
    return body


def ecb(raw, start, end):
    """ECB reference rates: 1 EUR = OBS_VALUE <currency>."""
    url = ECB.format(cur="+".join(CURRENCIES)) + "?" + urllib.parse.urlencode(
        {"startPeriod": start, "endPeriod": end, "format": "csvdata"})
    body = get(url)
    (raw / f"ecb_{start}_{end}.csv").write_bytes(body)
    rows = []
    for r in csv.DictReader(io.StringIO(body.decode("utf-8"))):
        rows.append({"base": "EUR", "quote": r["CURRENCY"],
                     "rate": Decimal(r["OBS_VALUE"]),
                     "on_date": r["TIME_PERIOD"], "source_url": url})
    return rows


def bcb(raw, start, end, currency):
    """PTAX: BRL per 1 unit of the currency. Keeps only the closing bulletin."""
    def mdy(d):
        y, m, dd = d.split("-")
        return f"{m}-{dd}-{y}"
    qs = urllib.parse.urlencode({
        "@moeda": f"'{currency}'", "@dataInicial": f"'{mdy(start)}'",
        "@dataFinalCotacao": f"'{mdy(end)}'", "$format": "json",
        "$select": "cotacaoCompra,cotacaoVenda,paridadeCompra,paridadeVenda,"
                   "dataHoraCotacao,tipoBoletim"})
    url = BCB + "?" + qs
    body = get(url)
    (raw / f"bcb_ptax_{currency}_{start}_{end}.json").write_bytes(body)
    rows = []
    for r in json.loads(body)["value"]:
        if r["tipoBoletim"] != "Fechamento":
            continue
        rows.append({"base": currency, "quote": "BRL",
                     "rate": Decimal(str(r["cotacaoVenda"])),
                     "on_date": r["dataHoraCotacao"][:10], "source_url": url,
                     "buy": r["cotacaoCompra"]})
    return rows


def main(raw_dir, start, end):
    raw = Path(raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    e = ecb(raw, start, end)
    print("ECB (1 EUR = x):")
    for r in e:
        print(f"  {r['on_date']} EUR/{r['quote']} {r['rate']}")
    ptax = []
    for cur in ["USD", "EUR", "CAD", "GBP", "AUD"]:
        ptax += bcb(raw, start, end, cur)
    print("BCB PTAX closing (1 unit = x BRL, selling rate):")
    for r in ptax:
        print(f"  {r['on_date']} {r['base']}/BRL sell {r['rate']} buy {r['buy']}")

    # USD->BRL: PTAX directly vs ECB cross (EUR/BRL / EUR/USD).
    by = {(r["on_date"], r["quote"]): r["rate"] for r in e}
    q = Decimal("0.0001")
    print("USD->BRL comparison (ECB cross vs PTAX sell):")
    for r in ptax:
        if r["base"] != "USD":
            continue
        d = r["on_date"]
        if (d, "BRL") in by and (d, "USD") in by:
            cross = (by[(d, "BRL")] / by[(d, "USD")]).quantize(q, ROUND_HALF_EVEN)
            print(f"  {d} ECB cross {cross}  PTAX {r['rate']}  "
                  f"diff {(cross - r['rate']).quantize(q)}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0] if a else "spikes/_raw/fx",
         a[1] if len(a) > 1 else "2026-11-16",
         a[2] if len(a) > 2 else "2026-11-20")
