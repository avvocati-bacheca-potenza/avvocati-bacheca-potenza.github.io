#!/usr/bin/env python3
"""Aggiorna site/data/udienze.json con i documenti di trattazione delle udienze
pubblicati su www.ordineavvocatipotenza.it (sezione "Trattazione udienze").

Per ogni pagina di magistrato/collegio legge l'elenco degli allegati (PDF, DOC...),
ricava dal nome del file il giorno (o i giorni) di udienza e classifica il documento
in penale / civile / lavoro. Si conservano i documenti di udienze da 30 giorni fa in poi.

Eseguito da GitHub Actions (vedi .github/workflows/aggiorna.yml).
Esce con codice 0 e stampa "modificato=true|false". Se il sito dell'Ordine non risponde
non cambia nulla e non blocca la pubblicazione.
"""

import datetime
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

SITO = "https://www.ordineavvocatipotenza.it"
FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site", "data", "udienze.json")
GIORNI_STORICO = 30      # documenti di udienze fino a 30 giorni fa
GIORNI_FUTURO = 180      # e fino a sei mesi avanti
PAUSA = 0.3              # secondi tra una pagina e l'altra, per non pesare sul sito
TEMPO_MASSIMO = 420      # secondi: se il sito è lento ci si ferma e si tengono i dati già noti

MESI = {"gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6, "luglio": 7,
        "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
        "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6, "lug": 7, "ago": 8, "set": 9, "sett": 9,
        "ott": 10, "nov": 11, "dic": 12}


def scarica(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (OrdineAvvocatiPotenza)"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")


def con_tentativi(fn, nome, tentativi=2):
    for i in range(1, tentativi + 1):
        try:
            return fn()
        except (OSError, ValueError) as e:
            print("Avviso: %s non disponibile (tentativo %d/%d): %s" % (nome, i, tentativi, e), file=sys.stderr)
            if i < tentativi:
                time.sleep(4)
    return None


def data_valida(g, m, a):
    if a < 100:
        a += 2000
    try:
        d = datetime.date(a, m, g)
    except ValueError:
        return None
    return d if 2020 <= d.year <= 2030 else None


def date_nel_nome(nome):
    """Giorni di udienza indicati nel nome del file: 7.10.2026, 15.01.25, 22/10/2026,
    11 Settembre 2026, 23 e 24 giugno 2026..."""
    t = nome.lower()
    t = re.sub(r"\.(pdf|docx?|odt|rtf|xlsx?|p7m)$", "", t)
    trovate = set()
    for g, m, a in re.findall(r"(?<!\d)(\d{1,2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{4}|\d{2})(?!\d)", t):
        d = data_valida(int(g), int(m), int(a))
        if d:
            trovate.add(d)
    nomi_mesi = "|".join(sorted(MESI, key=len, reverse=True))
    for gruppo, mese, anno in re.findall(r"((?:\d{1,2}\s*(?:,|e|-|/|ed)?\s*)+)\s*(%s)\.?\s*(\d{4})" % nomi_mesi, t):
        for g in re.findall(r"\d{1,2}", gruppo):
            d = data_valida(int(g), MESI[mese], int(anno))
            if d:
                trovate.add(d)
    return sorted(trovate)


def nome_magistrato(slug, titolo):
    if re.match(r"dott(ssa)?-", slug):
        parti = slug.split("-")
        return ("Dott.ssa " if parti[0] == "dottssa" else "Dott. ") + " ".join(p.capitalize() for p in parti[1:])
    t = html.unescape(titolo).strip()
    return t.title() if t.isupper() else t


def classifica(percorso, titolo):
    """Restituisce (categoria, ufficio, magistrato) a partire dall'indirizzo della pagina."""
    p = percorso.replace("/trattazione-udienze/", "").split("/")
    slug = p[-1]
    magistrato = nome_magistrato(slug, titolo)
    if p[0] == "tribunale":
        sezione = p[1] if len(p) > 1 else ""
        categoria = {"sezione-penale": "penale", "sezione-civile": "civile", "sezione-lavoro": "lavoro"}.get(sezione, "civile")
        ufficio = "Tribunale"
        if "ufficio-gip-gup" in p:
            ufficio = "Tribunale – GIP/GUP"
        elif "tribunale-riesame" in p:
            ufficio = "Tribunale – Riesame"
        return categoria, ufficio, magistrato
    if p[0] == "corte-dappello":
        sezione = p[1] if len(p) > 1 else ""
        categoria = {"sezione-penale": "penale", "sezione-civile": "civile", "sezione-lavoro": "lavoro"}.get(sezione, "civile")
        if sezione in ("sezione-civile", "sezione-lavoro") and len(p) == 2:
            magistrato = "Sezione " + ("civile" if sezione == "sezione-civile" else "lavoro")
        if magistrato.lower().startswith("corte d'appello "):
            magistrato = magistrato[len("Corte d'Appello "):]
        return categoria, "Corte d'Appello", magistrato
    if p[0] == "corte-dassise":
        return "penale", "Corte d'Assise", magistrato
    if p[0] in ("tribunale-di-sorveglianza", "ufficio-di-sorveglianza"):
        return "penale", "Sorveglianza", "Tribunale di sorveglianza" if p[0] == "tribunale-di-sorveglianza" else "Ufficio di sorveglianza"
    if p[0] == "giudice-di-pace":
        if len(p) > 1 and p[1] == "giudice-di-pace-di-potenza":
            sezione = p[2] if len(p) > 2 else ""
            return ("penale" if sezione == "sezione-penale" else "civile"), "Giudice di pace di Potenza", magistrato
        luogo = re.sub(r"^giudice-di-pace-di-", "", p[1]).split("-dott")[0].replace("-", " ").title() if len(p) > 1 else ""
        luogo = luogo.replace(" Di ", " di ")
        return "", "Giudice di pace di " + luogo, ""  # penale/civile dal nome del file; senza nome del magistrato
    return "civile", "Altro", magistrato


def pagine_udienze():
    sitemap = scarica(SITO + "/sitemap")
    return sorted(set(re.findall(r'<a href="(/trattazione-udienze[^"]*)"', sitemap)))


def allegati(pagina_html):
    i = pagina_html.find('class="field-items"')
    corpo = (pagina_html[i:] if i >= 0 else pagina_html).split("<footer")[0]
    trovati = []
    for m in re.finditer(r'<a href="(https://www\.ordineavvocatipotenza\.it/sites/default/files/[^"]+)"[^>]*>([^<]+)</a>'
                         r'(?:</span>\s*</td>\s*<td>([^<]*)</td>)?', corpo):
        trovati.append((m.group(1), html.unescape(m.group(2)).strip(), (m.group(3) or "").strip()))
    return trovati


def main():
    with open(FILE, encoding="utf-8") as f:
        precedente = json.load(f)
    noti = {(d["url"], d["magistrato"]): d for d in precedente.get("udienze", [])}

    percorsi = con_tentativi(pagine_udienze, "sitemap")
    if not percorsi:
        print("modificato=false")
        return
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and datetime.datetime.utcnow().minute >= 30:
        print("modificato=false")  # i controlli programmati sulle udienze partono una volta all'ora
        return

    oggi = datetime.date.today()
    da, a = oggi - datetime.timedelta(days=GIORNI_STORICO), oggi + datetime.timedelta(days=GIORNI_FUTURO)
    adesso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    raccolti, pagine_ok = {}, 0
    inizio = time.time()
    for percorso in percorsi:
        if time.time() - inizio > TEMPO_MASSIMO:
            pagina = None  # tempo esaurito: per le pagine restanti restano i documenti già noti
        else:
            pagina = con_tentativi(lambda: scarica(SITO + percorso), percorso)
            time.sleep(PAUSA)
        if pagina is None:
            # pagina non raggiungibile: si tengono i documenti già noti di quel magistrato
            for k, d in noti.items():
                if d.get("pagina") == percorso:
                    raccolti[k] = d
            continue
        pagine_ok += 1
        titolo_m = re.search(r"<title>(.*?)</title>", pagina, re.S)
        titolo = titolo_m.group(1).split("|")[0].strip() if titolo_m else ""
        categoria, ufficio, magistrato = classifica(percorso, titolo)
        for url, nome, dimensione in allegati(pagina):
            giorni = [g for g in date_nel_nome(urllib.parse.unquote(nome)) if da <= g <= a]
            if not giorni:
                continue
            cat = categoria or ("penale" if "penal" in nome.lower() else "civile")
            chiave = (url, magistrato)
            for g in giorni:
                raccolti[(url, magistrato, g.isoformat())] = {
                    "data": g.isoformat(), "categoria": cat, "ufficio": ufficio, "magistrato": magistrato,
                    "titolo": re.sub(r"\.(pdf|docx?|odt|rtf|xlsx?)$", "", nome, flags=re.I).strip(),
                    "url": url, "dimensione": dimensione, "pagina": percorso,
                    "rilevato_il": next((d["rilevato_il"] for k, d in noti.items() if k == chiave and d.get("rilevato_il")), adesso),
                }

    if pagine_ok == 0:
        print("modificato=false")
        return
    elenco = sorted(raccolti.values(), key=lambda d: (d["data"], d["categoria"], d["ufficio"], d["magistrato"], d["titolo"]))
    nuovo = {"da": da.isoformat(), "pagine_lette": pagine_ok, "pagine_totali": len(percorsi),
             "fonte": SITO + "/trattazione-udienze", "udienze": elenco}
    vecchio_cmp = {k: v for k, v in precedente.items() if k != "aggiornato_il"}
    modificato = nuovo != vecchio_cmp
    if modificato:
        nuovo["aggiornato_il"] = adesso
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(nuovo, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print("Udienze: %d documenti da %d pagine" % (len(elenco), pagine_ok), file=sys.stderr)
    print("modificato=%s" % str(modificato).lower())


if __name__ == "__main__":
    main()
