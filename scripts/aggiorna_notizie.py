#!/usr/bin/env python3
"""Aggiorna site/data/notizie.json con le notizie pubblicate su www.ordineavvocatipotenza.it.

Eseguito da GitHub Actions ogni 30 minuti (vedi .github/workflows/aggiorna.yml).
Fonti: feed RSS (ultime 10 notizie, con allegati) e prima pagina della bacheca.
Tiene solo le notizie pubblicate a partire da "dal" (in notizie.json) e non cancella
quelle già salvate quando escono dal feed.

Esce con codice 0 e stampa "modificato=true|false" per il workflow.
"""

import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import timezone, timedelta

SITO = "https://www.ordineavvocatipotenza.it"
RSS = SITO + "/rss.xml"
BACHECA = SITO + "/bacheca_home?page=0"
FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site", "data", "notizie.json")
ITALIA = timezone(timedelta(hours=1))  # sufficiente per ricavare il giorno di pubblicazione


def scarica(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (OrdineAvvocatiPotenza)"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def testo(frammento):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", frammento))).strip()


def assoluto(href):
    return urllib.parse.urljoin(SITO + "/", href.strip())


def da_rss():
    radice = ET.fromstring(scarica(RSS).encode("utf-8"))
    notizie = []
    for item in radice.iter("item"):
        descrizione = html.unescape(item.findtext("description") or "")
        allegati = []
        for m in re.finditer(r'<a href="([^"]+)"[^>]*>(.*?)</a>(?:\s*</span>\s*</td>\s*<td>([^<]*)</td>)?', descrizione, re.S):
            nome = testo(m.group(2))
            if nome:
                allegati.append({"nome": nome, "url": assoluto(m.group(1)), "dimensione": (m.group(3) or "").strip()})
        corpo = testo(re.sub(r"<table.*?</table>", " ", descrizione, flags=re.S))
        corpo = re.sub(r"^(Allegato Dimensione|Allegati:)\s*", "", corpo)
        data = parsedate_to_datetime(item.findtext("pubDate")).astimezone(ITALIA).strftime("%Y-%m-%d")
        notizie.append({"link": assoluto(item.findtext("link") or ""), "titolo": testo(item.findtext("title") or ""),
                        "data": data, "testo": corpo[:600] or None, "allegati": allegati})
    return notizie


def da_bacheca():
    return [{"link": assoluto(m.group(4)), "titolo": testo(m.group(5)),
             "data": "%s-%s-%s" % (m.group(3), m.group(2), m.group(1)), "testo": None, "allegati": []}
            for m in re.finditer(r'views-field-created">\s*(\d{2})/(\d{2})/(\d{4})\s*</td>.*?<a href="([^"]+)"[^>]*>(.*?)</a>',
                                 scarica(BACHECA), re.S)]


def con_tentativi(fn, nome, tentativi=3):
    """Esegue fn(); se il sito dell'Ordine ha un problema momentaneo riprova, altrimenti restituisce None."""
    for i in range(1, tentativi + 1):
        try:
            return fn()
        except (OSError, ET.ParseError, ValueError) as e:
            print("Avviso: %s non disponibile (tentativo %d/%d): %s" % (nome, i, tentativi, e), file=sys.stderr)
            if i < tentativi:
                time.sleep(4)
    return None


def main():
    with open(FILE, encoding="utf-8") as f:
        stato = json.load(f)
    dal = stato["dal"]
    salvate = {n["link"]: n for n in stato["notizie"]}

    dalla_bacheca = con_tentativi(da_bacheca, "bacheca")
    dal_feed = con_tentativi(da_rss, "feed RSS")
    if dalla_bacheca is None and dal_feed is None:
        # Il sito dell'Ordine non risponde: non è un motivo per bloccare la pubblicazione del sito.
        print("modificato=false")
        return

    raccolte = {n["link"]: n for n in (dalla_bacheca or [])}
    raccolte.update({n["link"]: n for n in (dal_feed or [])})  # il feed ha più dettagli

    adesso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for link, n in raccolte.items():
        if n["data"] < dal:
            continue
        if link in salvate:
            vecchia = salvate[link]
            vecchia["testo"] = n["testo"] or vecchia.get("testo")
            vecchia["allegati"] = n["allegati"] or vecchia.get("allegati", [])
            vecchia["titolo"] = n["titolo"]
        else:
            salvate[link] = dict(n, rilevato_il=adesso)
            print("Nuova notizia:", n["data"], n["titolo"], file=sys.stderr)

    nuovo = dict(stato, notizie=sorted(salvate.values(), key=lambda n: (n["data"], n["rilevato_il"]), reverse=True))
    modificato = nuovo != stato
    if modificato:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(nuovo, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print("modificato=%s" % str(modificato).lower())


if __name__ == "__main__":
    main()
