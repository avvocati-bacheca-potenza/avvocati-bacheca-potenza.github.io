# Ordine Avvocati Potenza — Albo e bacheca

Sito statico pubblicato con GitHub Pages: https://avvocati-bacheca-potenza.github.io

- `site/index.html`: home con logo, recapiti dell'Ordine e accesso ai servizi.
- `site/bacheca.html`: bacheca: notizie dell'Ordine + annunci di utilità.
- `site/mediazione.html`: Organismo di mediazione (istanze, costi, contatti, collegamento alla modulistica ufficiale).
- `site/albo.html`: albo degli iscritti (modulo ufficiale dell'Albo online incorporato).
- `site/annunci.html`: rimando alla bacheca per i vecchi link.
- `site/data/annunci.json`: annunci della bacheca (si modificano qui).
- `site/data/notizie.json`: notizie importate automaticamente da www.ordineavvocatipotenza.it.
- `scripts/aggiorna_notizie.py`: legge RSS e bacheca dell'Ordine e aggiorna `notizie.json`.
- `.github/workflows/aggiorna.yml`: ogni 30 minuti controlla le notizie; a ogni modifica ripubblica il sito.

## Aggiungere o togliere un annuncio

Modifica `site/data/annunci.json` (anche dal sito di GitHub: apri il file, matita ✏️, "Commit changes").
Il sito si ripubblica da solo in circa un minuto.

```json
{
  "id": 5,
  "titolo": "Titolo",
  "testo": "Testo dell'annuncio",
  "categoria": "Varie",
  "autore": null,
  "link": null,
  "in_evidenza": false,
  "pubblicato_il": "2026-11-02",
  "scade_il": null
}
```

Categorie: Uffici giudiziari, Udienze e rinvii, Formazione, Bandi e incarichi, Sostituzioni e colleghi, Varie.
Un annuncio con `pubblicato_il` futuro compare da quel giorno; dopo `scade_il` sparisce.
**Regola dei 30 giorni:** se `scade_il` è `null`, l'annuncio resta visibile al massimo 30 giorni dalla
pubblicazione (giorno di pubblicazione compreso), poi sparisce da solo. Vale anche per le notizie dell'Ordine.
Gli annunci scaduti restano nel file e si possono ripubblicare cambiando le date.

## Notizie dell'Ordine

Si mostrano solo quelle pubblicate dalla data `dal` in `site/data/notizie.json` (oggi 2026-11-01).
GitHub può ritardare di qualche minuto i controlli programmati; il controllo si può avviare a mano da
Actions → "Aggiorna e pubblica" → "Run workflow".
