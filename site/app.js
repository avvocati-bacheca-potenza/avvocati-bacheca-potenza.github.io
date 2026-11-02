// Web app: registra il service worker, gestisce il pulsante "Condividi" e,
// alla prima visita, propone di installare l'app.
(() => {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
  }

  // Si condivide sempre l'indirizzo principale del sito, mai quello della singola pagina.
  const LINK_CONDIVISIONE = "https://avvocati-bacheca-potenza.github.io";

  function avviso(testo) {
    const el = document.createElement("div");
    el.className = "avviso-breve";
    el.textContent = testo;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2600);
  }

  document.addEventListener("click", async e => {
    if (!e.target.closest("[data-condividi]")) return;
    const dati = {title: "Ordine Avvocati Potenza", text: "Bacheca annunci e albo degli iscritti", url: LINK_CONDIVISIONE};
    if (navigator.share) {
      try { await navigator.share(dati); } catch (err) {}
      return;
    }
    try {
      await navigator.clipboard.writeText(LINK_CONDIVISIONE);
      avviso("Link copiato: " + LINK_CONDIVISIONE.replace("https://", ""));
    } catch (err) {
      prompt("Copia il link:", LINK_CONDIVISIONE);
    }
  });

  // Pulsanti "Copia": copiano il valore negli appunti (con ripiego per i browser che non lo permettono).
  async function copia(testo) {
    try { await navigator.clipboard.writeText(testo); return true; } catch (err) {}
    const t = document.createElement("textarea");
    t.value = testo; t.setAttribute("readonly", ""); t.style.cssText = "position:fixed;top:0;left:0;opacity:0";
    document.body.appendChild(t); t.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (err) {}
    t.remove();
    return ok;
  }

  document.addEventListener("click", async e => {
    const b = e.target.closest("[data-copia]");
    if (!b) return;
    const ok = await copia(b.dataset.copia);
    const prima = b.dataset.etichetta || b.textContent;
    b.dataset.etichetta = prima;
    b.textContent = ok ? "Copiato ✓" : "Non copiato";
    b.classList.toggle("fatto", ok);
    clearTimeout(b._timer);
    b._timer = setTimeout(() => { b.textContent = prima; b.classList.remove("fatto"); }, 1800);
  });

  const installata = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  let rifiutato = false;
  try { rifiutato = localStorage.getItem("installaRifiutato") === "1"; } catch (e) {}
  if (installata || rifiutato) return;

  const ua = navigator.userAgent;
  const ios = /iPhone|iPad|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const safari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua);

  function banner(testo, azione) {
    const el = document.createElement("div");
    el.className = "installa";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-label", "Installa l'app");
    el.innerHTML = `<img src="img/icona-192.png" alt="" width="44" height="44">
      <div class="installa-testo"><strong>Installa l'app Avvocati PZ</strong><span>${testo}</span></div>
      <div class="installa-bottoni">${azione ? '<button class="btn piccolo" data-installa>Installa</button>' : ""}
        <button class="btn secondario piccolo" data-chiudi>${azione ? "Non ora" : "Ho capito"}</button></div>`;
    document.body.appendChild(el);
    el.querySelector("[data-chiudi]").addEventListener("click", () => {
      try { localStorage.setItem("installaRifiutato", "1"); } catch (e) {}
      el.remove();
    });
    if (azione) el.querySelector("[data-installa]").addEventListener("click", async () => {
      el.remove();
      await azione();
    });
  }

  // Chrome, Edge, Android: il browser permette di mostrare il proprio invito all'installazione.
  window.addEventListener("beforeinstallprompt", e => {
    e.preventDefault();
    banner("Aprila dalla schermata Home, a schermo intero, senza barra dell'indirizzo.", async () => {
      e.prompt();
      await e.userChoice;
    });
  });

  // iPhone e iPad: Safari non ha un invito automatico, si spiega il passaggio.
  if (ios && safari) {
    banner('Tocca <span class="icona-condividi" aria-label="Condividi">⬆︎</span> <b>Condividi</b> e poi <b>Aggiungi alla schermata Home</b>.');
  }
})();
