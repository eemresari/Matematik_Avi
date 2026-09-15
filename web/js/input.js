/* input.js — TEK normalize girdi modülü (seam).
   Oyun mantığı SADECE { x:0..1, y:0..1, present:bool, gesture:'open'|'fist' } okur.

   İKİ SÜRÜCÜ DE KURULUR; paylaşılan `hand` nesnesine yalnız AKTİF olan yazar.
   `Ctrl` çalışma anında ikisi arasında geçiş yapar (sergide fare devralma).
   `?input=ws|mouse` yalnızca AÇILIŞ VARSAYILANIDIR — donmuş EXE `ws` verir,
   kaynaktan geliştirmede `mouse` varsayılan.

   Kullanım: ?input=ws&host=192.168.1.50&port=8765   (varsayılan: mouse) */
(function () {
  const MA = (window.MA = window.MA || {});

  // Paylaşılan normalize durum — tüm tüketiciler bunu okur.
  const hand = { x: 0.5, y: 0.5, present: false, gesture: "open" };

  const params = new URLSearchParams(location.search);
  let driver = (params.get("input") || "mouse").toLowerCase() === "ws" ? "ws" : "mouse";

  function stageRect() {
    const s = document.getElementById("stage");
    return s ? s.getBoundingClientRect() : { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight };
  }
  const clamp01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);

  // ---------------- FARE MODU ROZETİ ----------------
  // Ctrl'e yanlışlıkla basılırsa el takibi sessizce ölür ve sergi "bozuldu"
  // sanılır. Kalıcı rozet bunu görünür kılar. Stiller burada satır içi:
  // rozet girdi modunun bir parçası, sahnenin değil — styles.css'i kirletmez.
  let rozet = null;

  function rozetKur() {
    if (rozet || !document.body) return;
    rozet = document.createElement("div");
    rozet.id = "ma-fare-rozeti";
    rozet.textContent = "FARE MODU";
    rozet.style.cssText = [
      "position:fixed", "left:14px", "bottom:12px", "z-index:99999",
      "padding:6px 13px", "border-radius:6px",
      "font-family:'JetBrains Mono',ui-monospace,monospace",
      "font-size:12px", "font-weight:700", "letter-spacing:0.24em",
      "color:#ffd36e", "background:rgba(28,14,0,0.78)",
      "border:1px solid rgba(255,196,92,0.55)",
      "box-shadow:0 0 14px rgba(255,180,60,0.32)",
      "pointer-events:none", "user-select:none", "display:none",
    ].join(";");
    document.body.appendChild(rozet);
  }

  function rozetiGuncelle() {
    if (rozet) rozet.style.display = driver === "mouse" ? "block" : "none";
  }

  // ---------------- SÜRÜCÜ DEĞİŞTİRME ----------------
  function setDriver(ad) {
    const yeni = ad === "ws" ? "ws" : "mouse";
    if (yeni === driver) return driver;
    driver = yeni;
    // Eski sürücünün son karesi devrolmasın: açık kalmış bir "fist" yeni modda
    // anında tıklamaya dönüşür ve oyun kendiliğinden başlar.
    hand.present = false;
    hand.gesture = "open";
    if (driver === "ws") wsBaslat();
    rozetiGuncelle();
    return driver;
  }

  // ---------------- MOUSE sürücüsü ----------------
  function mouseKur() {
    window.addEventListener("mousemove", (e) => {
      if (driver !== "mouse") return;
      const r = stageRect();
      hand.x = clamp01((e.clientX - r.left) / r.width);
      hand.y = clamp01((e.clientY - r.top) / r.height);
      hand.present = e.clientX >= r.left && e.clientX <= r.left + r.width &&
                     e.clientY >= r.top && e.clientY <= r.top + r.height;
    });
    window.addEventListener("mousedown", () => { if (driver === "mouse") hand.gesture = "fist"; });
    window.addEventListener("mouseup", () => { if (driver === "mouse") hand.gesture = "open"; });
    document.addEventListener("mouseleave", () => { if (driver === "mouse") hand.present = false; });
  }

  // ---------------- WEBSOCKET sürücüsü ----------------
  // Bir kez başlar ve bağlantı AÇIK kalır: fare moduna geçilse bile dedektör
  // çalışmaya devam eder, kareler sessizce yoksayılır; Ctrl geri basıldığında
  // el takibi yeniden bağlanmayı beklemeden döner.
  // İlk `ws` moduna GİRİLENE KADAR hiç bağlanılmaz: kaynaktan geliştirmede
  // varsayılan `mouse` ve dedektör kapalıyken konsol her 5 sn'de bir
  // ERR_CONNECTION_REFUSED basardı.
  let wsBasladi = false;
  let soket = null;   // aktif bağlantı — ayarlar sekmesi komut göndermek için okur

  function wsBaslat() {
    if (wsBasladi) return;
    wsBasladi = true;
    const host = params.get("host") || location.hostname || "127.0.0.1";
    const port = params.get("port") || "8765";
    const url = `ws://${host}:${port}`;
    let backoff = 1000;

    function connect() {
      let ws;
      try { ws = new WebSocket(url); }
      catch (e) { return retry(); }
      soket = ws;

      ws.onopen = () => { backoff = 1000; };
      ws.onmessage = (ev) => {
        if (driver !== "ws") return;
        try {
          const m = JSON.parse(ev.data);
          if (typeof m.x === "number") hand.x = clamp01(m.x);
          if (typeof m.y === "number") hand.y = clamp01(m.y);
          hand.present = !!m.present;
          hand.gesture = m.gesture === "fist" ? "fist" : "open";
        } catch (_) { /* bozuk kare yoksay */ }
      };
      ws.onclose = () => { if (driver === "ws") hand.present = false; if (soket === ws) soket = null; retry(); };
      ws.onerror = () => { try { ws.close(); } catch (_) {} };
    }
    function retry() {
      setTimeout(connect, backoff);
      backoff = Math.min(backoff * 1.7, 5000); // üstel backoff, ~5s tavan
    }
    connect();
  }

  // ---------------- KOMUT KANALI (ayarlar sekmesi -> dedektör) ----------------
  // Aynı soket, TERS yön: el konumu okuma bağlantısı zaten açık/kalıcı,
  // ikinci bir bağlantı açmaya gerek yok. Bağlı değilse false döner —
  // çağıran taraf (settings.js) bunu "dedektöre ulaşılamadı" diye gösterir.
  function sendCmd(cmd) {
    if (!soket || soket.readyState !== WebSocket.OPEN) return false;
    try { soket.send(JSON.stringify({ cmd })); return true; }
    catch (_) { return false; }
  }

  function start() {
    rozetKur();
    rozetiGuncelle();
    mouseKur();
    if (driver === "ws") wsBaslat();
    // Ctrl = sürücü devri. `e.repeat` şart: basılı tutmak tek toggle üretmeli.
    // Bağlı tek diğer tuş Escape (game.js) — çakışma yok.
    window.addEventListener("keydown", (e) => {
      if (e.key !== "Control" || e.repeat) return;
      setDriver(driver === "ws" ? "mouse" : "ws");
    });
  }

  MA.input = {
    hand,
    start,
    setDriver,
    sendCmd,
    get driver() { return driver; },
    get connected() { return !!soket && soket.readyState === WebSocket.OPEN; },
  };
})();
