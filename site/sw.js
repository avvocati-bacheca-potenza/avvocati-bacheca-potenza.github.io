// Service worker: permette l'installazione come app e l'apertura anche senza connessione.
// Sempre prima la rete (così annunci e notizie sono aggiornati), la copia salvata solo se offline.
const CACHE = "oap-v4";
const BASE = ["./", "index.html", "bacheca.html", "albo.html", "mediazione.html", "udienze.html", "style.css", "app.js", "manifest.webmanifest",
              "img/logo.png", "img/icona-192.png", "data/annunci.json", "data/notizie.json", "data/udienze.json"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(BASE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(chiavi => Promise.all(chiavi.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  e.respondWith(
    fetch(e.request)
      .then(r => {
        if (r.ok) { const copia = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copia)); }
        return r;
      })
      .catch(() => caches.match(e.request, {ignoreSearch: true}))
  );
});
