/* settings.js — oyun içi ayarlar sekmesi (kalibrasyon + kamera ayarları).
   El taratma ekranı bitince sol-üst köşede küçük bir dişli ikonu belirir;
   tıklanınca küçük bir panel açılır. Gerçek iş NATIVE tarafta olur
   (python/mapping/calibrate.py'nin OpenCV penceresi, camera_settings.py'nin
   tkinter penceresi) — burada yalnız MA.input.sendCmd ile komut tetiklenir
   ve sonucu bildiren bir durum satırı gösterilir. */
(function () {
  const MA = (window.MA = window.MA || {});

  let gear = null, panel = null, statusEl = null, revealed = false;

  function css(el, obj) { Object.assign(el.style, obj); }

  function makeBtn(label, cmd) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = label;
    css(b, {
      display: 'block', width: '100%', marginBottom: '7px',
      padding: '7px 8px', borderRadius: '6px', cursor: 'pointer',
      background: 'rgba(125,243,255,0.08)', color: '#eef1ff',
      border: '1px solid rgba(125,243,255,0.25)', fontSize: '11.5px',
      fontFamily: 'inherit', textAlign: 'left',
    });
    b.addEventListener('click', () => gonder(cmd, label));
    return b;
  }

  function gonder(cmd, label) {
    const ok = !!(MA.input && MA.input.sendCmd && MA.input.sendCmd(cmd));
    if (ok) {
      statusEl.textContent = label + ' başlatıldı…';
      statusEl.style.color = '#34F5A6';
      hidePanel();
    } else {
      statusEl.textContent = 'Dedektöre bağlı değil (el takibi WS modunda mı?).';
      statusEl.style.color = '#FF5470';
    }
  }

  function build() {
    if (gear) return;

    gear = document.createElement('button');
    gear.id = 'ma-ayarlar-dislisi';
    gear.type = 'button';
    gear.title = 'Ayarlar';
    gear.textContent = '⚙';
    css(gear, {
      position: 'fixed', left: '10px', top: '10px', zIndex: 99999,
      width: '30px', height: '30px', borderRadius: '50%',
      background: 'rgba(11,10,26,0.55)', color: '#7df3ff',
      border: '1px solid rgba(125,243,255,0.35)',
      fontSize: '16px', lineHeight: '28px', textAlign: 'center',
      cursor: 'pointer', padding: '0', display: 'none',
      fontFamily: "'JetBrains Mono',ui-monospace,monospace",
      boxShadow: '0 0 10px rgba(0,235,255,0.15)',
    });
    gear.addEventListener('click', togglePanel);
    document.body.appendChild(gear);

    panel = document.createElement('div');
    panel.id = 'ma-ayarlar-paneli';
    css(panel, {
      position: 'fixed', left: '10px', top: '48px', zIndex: 99999,
      width: '210px', padding: '12px',
      background: 'rgba(11,10,26,0.92)', border: '1px solid rgba(125,243,255,0.3)',
      borderRadius: '10px', boxShadow: '0 8px 28px rgba(0,0,0,0.5)',
      fontFamily: "'JetBrains Mono',ui-monospace,monospace",
      display: 'none', color: '#eef1ff',
    });

    const baslik = document.createElement('div');
    baslik.textContent = 'AYARLAR';
    css(baslik, { fontSize: '11px', letterSpacing: '0.18em', color: '#9F5FFF', marginBottom: '10px' });
    panel.appendChild(baslik);

    panel.appendChild(makeBtn('Kalibrasyonu Başlat', 'kalibrasyon'));
    panel.appendChild(makeBtn('Kamera Ayarları', 'kamera_ayarlari'));

    statusEl = document.createElement('div');
    css(statusEl, { fontSize: '10.5px', marginTop: '8px', minHeight: '14px', color: '#a9a4d6' });
    panel.appendChild(statusEl);

    document.body.appendChild(panel);

    // Panel dışına tıklayınca kapat.
    document.addEventListener('click', (e) => {
      if (!panel || panel.style.display === 'none') return;
      if (e.target === gear || panel.contains(e.target)) return;
      hidePanel();
    });
  }

  function togglePanel(e) {
    e.stopPropagation();
    if (panel.style.display === 'none') showPanel(); else hidePanel();
  }
  function showPanel() { panel.style.display = 'block'; statusEl.textContent = ''; }
  function hidePanel() { panel.style.display = 'none'; }

  // El taratma ekranı tamamlanınca game.js bunu çağırır.
  function reveal() {
    build();
    revealed = true;
    gear.style.display = 'block';
  }

  MA.settings = { reveal, get revealed() { return revealed; } };
})();
