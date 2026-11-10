#!/usr/bin/env python3
"""Importa nel sito i documenti di udienza che si trovano nella cartella locale
~/Desktop/Sviluppo/Udienze e non sono ancora pubblicati sul sito dell'Ordine.

Per ogni file ricava il giorno di udienza (o il mese, per i documenti mensili) e il magistrato dal nome,
controlla se in site/data/udienze.json c'è già un documento dello stesso magistrato nello stesso giorno
e, se non c'è, copia il file in site/udienze-locali/ e lo registra in site/data/udienze_locali.json.

Uso:  python3 scripts/importa_udienze_locali.py [--prova] [--cartella PERCORSO]
          [--assegna "nome file=Dott.ssa Cognome"] [--titolo "nome file=Titolo da mostrare"]
Con --prova non si scrive nulla. I file senza magistrato riconoscibile vanno indicati con --assegna.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import unicodedata

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
from aggiorna_udienze import date_nel_nome, MESI  # noqa: E402

SITE = os.path.join(QUI, "..", "site")
FILE_LOCALI = os.path.join(SITE, "data", "udienze_locali.json")
FILE_SITO = os.path.join(SITE, "data", "udienze.json")
CARTELLA_FILE = os.path.join(SITE, "udienze-locali")
CARTELLA_DEFAULT = os.path.expanduser("~/Desktop/Sviluppo/Udienze")
ESTENSIONI = (".pdf", ".doc", ".docx", ".odt", ".rtf")

# Cognome nel nome del file -> (categoria, ufficio, magistrato come sul sito)
TRIBUNALE = {"cirillo": "Dott. Cirillo", "di iesu": "Dott. Di Iesu", "rotondi": "Dott. Rotondi", "verardi": "Dott. Verardi",
             "battista": "Dott.ssa Battista", "bonamico": "Dott.ssa Bonamico", "caprio": "Dott.ssa Caprio",
             "cristofaro": "Dott.ssa Cristofaro", "loffredo": "Dott.ssa Loffredo", "malafronte": "Dott.ssa Malafronte",
             "mirone": "Dott.ssa Mirone", "rizzo": "Dott.ssa Rizzo", "rossi": "Dott.ssa Rossi", "stante": "Dott.ssa Stante"}
GIP = {"amodeo": "Dott. Amodeo", "pignata": "Dott. Pignata", "setola": "Dott. Setola", "iura": "Dott.ssa Iura",
       "petrocelli": "Dott.ssa Petrocelli", "rotondi": "Dott. Rotondi", "malafronte": "Dott.ssa Malafronte"}
COLLEGI = {r"\bcoll(?:egio|\.)?\s*a\b": "Collegio A", r"\bcoll(?:egio|\.)?\s*b\b": "Collegio B"}


def normalizza(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def slug(nome):
    base, ext = os.path.splitext(nome)
    return re.sub(r"[^a-z0-9]+", "-", normalizza(base)).strip("-")[:70] + ext.lower()


def riconosci(nome, assegnato=None):
    """Elenco di (categoria, ufficio, magistrato) possibili per il file."""
    n = normalizza(os.path.splitext(nome)[0])
    if assegnato:
        return [("penale", "Tribunale", assegnato)]
    gip = "statino" in n
    trovati = []
    for chiave, m in (GIP if gip else TRIBUNALE).items():
        if re.search(r"\b%s\b" % chiave, n):
            trovati.append(("penale", "Tribunale – GIP/GUP" if gip else "Tribunale", m))
    for rx, m in COLLEGI.items():
        if re.search(rx, n):
            trovati.append(("penale", "Tribunale", m))
    return trovati


def mese_nel_nome(nome):
    n = normalizza(os.path.splitext(nome)[0])
    m = re.search(r"\b(%s)\s+(\d{4})\b" % "|".join(k for k in MESI if len(k) > 4), n)
    return "%04d-%02d" % (int(m.group(2)), MESI[m.group(1)]) if m else None


def dimensione(percorso):
    return "%.2f KB" % (os.path.getsize(percorso) / 1024)


def inizio_finestra(oggi):
    return oggi - datetime.timedelta(days=oggi.weekday() + 7)  # lunedì della settimana scorsa


def fine_mese(mese):
    anno, m = int(mese[:4]), int(mese[5:])
    primo_succ = datetime.date(anno + (m == 12), m % 12 + 1, 1)
    return primo_succ - datetime.timedelta(days=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cartella", default=CARTELLA_DEFAULT)
    ap.add_argument("--prova", action="store_true")
    ap.add_argument("--assegna", action="append", default=[])
    ap.add_argument("--titolo", action="append", default=[])
    args = ap.parse_args()
    assegna = dict(x.split("=", 1) for x in args.assegna)
    titoli = dict(x.split("=", 1) for x in args.titolo)

    sito = json.load(open(FILE_SITO, encoding="utf-8"))["udienze"]
    pubblicati = {}
    for d in sito:
        pubblicati.setdefault(d["data"], set()).add(d["magistrato"])
    locali = json.load(open(FILE_LOCALI, encoding="utf-8")) if os.path.exists(FILE_LOCALI) else {"documenti": []}
    noti = {d["sha1"] for d in locali["documenti"]}

    oggi = datetime.date.today()
    da = inizio_finestra(oggi)
    nuovi, esito = [], []
    for nome in sorted(os.listdir(args.cartella)):
        percorso = os.path.join(args.cartella, nome)
        if nome.startswith(".") or not nome.lower().endswith(ESTENSIONI) or not os.path.isfile(percorso):
            continue
        sha1 = hashlib.sha1(open(percorso, "rb").read()).hexdigest()
        if sha1 in noti:
            esito.append(("già importato", nome, "")); continue
        giorni = [g for g in date_nel_nome(nome)]
        mese = None if giorni else mese_nel_nome(nome)
        if not giorni and not mese:
            esito.append(("DA VERIFICARE", nome, "nessuna data riconoscibile nel nome")); continue
        if giorni and max(giorni) < da:
            esito.append(("troppo vecchio", nome, "udienza prima di %s" % da)); continue
        if mese and fine_mese(mese) < da:
            esito.append(("troppo vecchio", nome, "mese %s" % mese)); continue
        cand = riconosci(nome, assegna.get(nome))
        if not cand and not mese:
            esito.append(("DA VERIFICARE", nome, "magistrato non riconosciuto: usare --assegna")); continue
        if mese and not cand:
            cand = [("penale", "Tribunale", assegna.get(nome, "Sezione penale"))]
        # già pubblicato sul sito dell'Ordine? (stesso giorno e stesso magistrato)
        if giorni and any(m in pubblicati.get(g.isoformat(), set()) for g in giorni for _, _, m in cand):
            esito.append(("già sul sito", nome, "%s %s" % (giorni[0], cand[0][2]))); continue
        categoria, ufficio, magistrato = cand[0]
        voce = {"data": giorni[0].isoformat() if giorni else None, "mese": mese, "categoria": categoria, "ufficio": ufficio,
                "magistrato": magistrato, "titolo": titoli.get(nome) or os.path.splitext(nome)[0].strip(),
                "url": "udienze-locali/" + slug(nome), "dimensione": dimensione(percorso), "sha1": sha1,
                "origine": nome, "importato_il": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
        # più giorni nel nome: una voce per giorno (stesso file)
        for g in (giorni[1:] if giorni else []):
            nuovi.append(dict(voce, data=g.isoformat(), sha1=sha1 + g.isoformat()))
        nuovi.append(voce)
        esito.append(("DA IMPORTARE", nome, "%s | %s" % (voce["data"] or voce["mese"], magistrato)))
        if not args.prova:
            os.makedirs(CARTELLA_FILE, exist_ok=True)
            shutil.copyfile(percorso, os.path.join(SITE, voce["url"]))

    for stato, nome, nota in esito:
        print("%-14s %-62s %s" % (stato, nome[:62], nota))
    if args.prova or not nuovi:
        print("\n(prova: nulla scritto)" if args.prova else "\nNessun documento nuovo.")
        return
    locali["documenti"] = sorted(locali["documenti"] + nuovi, key=lambda d: (d["data"] or d["mese"] or "", d["magistrato"]))
    json.dump(locali, open(FILE_LOCALI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(FILE_LOCALI, "a").write("\n")
    print("\nImportati %d documenti in %s" % (len(nuovi), os.path.relpath(FILE_LOCALI)))


if __name__ == "__main__":
    main()
