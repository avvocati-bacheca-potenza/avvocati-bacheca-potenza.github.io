# Ordine Avvocati Potenza — Albo e bacheca

Sito statico pubblicato con GitHub Pages: https://avvocati-bacheca-potenza.github.io

- `site/index.html`: home con logo, recapiti dell'Ordine e accesso ai servizi.
- `site/bacheca.html`: bacheca: notizie dell'Ordine + annunci di utilità.
- `site/udienze.html`: documenti di trattazione delle udienze (penale e civile) per giorno, letti dalla sezione «Trattazione udienze» del sito dell'Ordine.
- `site/mediazione.html`: Organismo di mediazione (istanze, costi, contatti, collegamento alla modulistica ufficiale).
- `site/albo.html`: albo degli iscritti (modulo ufficiale dell'Albo online incorporato).
- `site/annunci.html`: rimando alla bacheca per i vecchi link.
- `site/data/annunci.json`: annunci della bacheca (si modificano qui).
- `site/data/notizie.json`: notizie pubblicate da www.ordineavvocatipotenza.it, importate automaticamente con i loro documenti. Restano visibili 60 giorni dalla pubblicazione, poi spariscono. Quelle che riguardano le udienze (`tipo: "udienze"`) non vanno in bacheca ma nella pagina Udienze.
- `site/data/udienze.json` e `scripts/aggiorna_udienze.py`: leggono le 63 pagine dei magistrati, ricavano il giorno di udienza dal nome del file e tengono la settimana in corso, quella precedente e i prossimi sei mesi (ogni lunedì spariscono le udienze di due settimane prima; controllo ogni ora). La pagina le mostra in ordine di data decrescente.
- `scripts/importa_udienze_locali.py`, `site/data/udienze_locali.json` e `site/udienze-locali/`: documenti di udienza presi dalla cartella `~/Desktop/Sviluppo/Udienze` che l'Ordine non ha ancora pubblicato. Lo script li confronta con `udienze.json` (stesso giorno e stesso magistrato), copia i nuovi e li registra. Si lanciano a mano: `python3 scripts/importa_udienze_locali.py --prova` per vedere cosa farebbe, senza `--prova` per importare (con `--assegna "file.pdf=Dott.ssa Cognome"` se il nome non indica il magistrato). I documenti mensili (es. turni di convalida) compaiono nel riquadro «Documenti del mese». Spariscono con la stessa regola delle udienze.
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
