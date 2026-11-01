/* Ledger report pages (4.U3; ported from docs/design/ledger-screens.html): the Record Submission sheet and the Close Ticket
   dialog open in place over the page they belong to, the Report Draft page switches report type in place, and a change that
   redirects shows its toast on the page it lands on. Everything works without this file: every sheet has its own address
   (the server renders the page under it with the sheet open) and every form posts normally.
   Sheet machinery lives here, not in ledger.js, until it's merged with PR 2's copy (4.U2). */
(function () {
  'use strict';
  var app = document.getElementById('app');
  if (!app) return;
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  function $(id) { return document.getElementById(id); }

  /* The service clock: the page carries the service's "now" (core.clock, which follows a fixed test clock); the browser's
     clock is never read. Time moves forward from it with performance.now(), as in ledger.js. */
  var T0 = Date.parse(app.getAttribute('data-now')), P0 = performance.now();
  if (isNaN(T0)) T0 = 0;
  function nowMs() { return T0 + (performance.now() - P0); }
  /* A fixed test clock (PUT /test/clock) doesn't move in the service, so "now" doesn't move here either */
  function formNow(form) { var f = form && form.hasAttribute('data-clock-fixed') && Date.parse(form.getAttribute('data-now')); return f || nowMs(); }

  /* Times as people type them: "YYYY-MM-DD HH:MM[:SS]" in UTC */
  function parseUtc(s) { var m = /^\s*(\d{4})-(\d{2})-(\d{2})[ Tt](\d{2}):(\d{2})(?::(\d{2}))?\s*(?:UTC|Z)?\s*$/i.exec(s || ''); if (!m) return NaN; return Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)); }
  function fmtUtc(ms) { return new Date(Math.floor(ms / 1000) * 1000).toISOString().replace('T', ' ').slice(0, 19); }
  function span(ms) { var m = Math.round(Math.abs(ms) / 60000), d = Math.floor(m / 1440), h = Math.floor(m / 60) % 24; return d ? d + ' d ' + h + ' h' : Math.floor(m / 60) + ' h ' + (m % 60) + ' m'; }
  var BADGE = { submitted: ['submitted', 'Submitted'], late: ['late', 'Submitted late'] };
  function urlKey(u) { var a = new URL(u, location.href); return a.pathname + a.search; }

  /* ---------- Toasts (the shell's #toast) ---------- */
  function toast(title, body, ok) {
    var t = $('toast'); if (!t) return;
    $('toast-title').textContent = title; $('toast-body').textContent = body || '';
    t.querySelector('svg use').setAttribute('href', ok ? '#i-check' : '#i-hourglass');
    t.classList.toggle('ok', !!ok);
    t.classList.add('show'); clearTimeout(toast.t); toast.t = setTimeout(function () { t.classList.remove('show'); }, 3400);
  }
  /* A change that redirected left a toast for this page: it rises in once the page has arrived */
  (function () {
    var t = $('toast'), title = t && t.getAttribute('data-flash-title');
    if (!title) return;
    t.removeAttribute('data-flash-title');
    setTimeout(function () { toast(title, t.getAttribute('data-flash-body'), true); }, reduceMotion.matches ? 0 : 280);
  })();

  /* ---------- Segmented control: the indicator slides to the selected segment ---------- */
  function placeInd(seg, instant) {
    var on = seg.querySelector('[aria-current="page"], [aria-pressed="true"]'), ind = seg.querySelector('.ind');
    if (!on || !ind) return;
    if (instant) ind.style.transition = 'none';
    ind.style.width = on.offsetWidth + 'px';
    ind.style.transform = 'translateX(' + on.offsetLeft + 'px)';
    if (instant) { ind.offsetWidth; ind.style.transition = ''; }
    seg.classList.add('ind-ready');
  }
  var tabs = $('rp-tabs');
  if (tabs) {
    placeInd(tabs, true);
    window.addEventListener('resize', function () { placeInd(tabs, true); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { placeInd(tabs, true); });
    var cur = tabs.querySelector('[aria-current="page"]');
    if (cur && cur.scrollIntoView && tabs.scrollWidth > tabs.clientWidth) tabs.scrollLeft = cur.offsetLeft - 8;
  }

  /* ---------- Fetching pages: a sheet's own address renders it, so the server is the one source of its markup ---------- */
  var pages = {};
  function fetchDoc(url) {
    var key = urlKey(url);
    if (!pages[key]) {
      pages[key] = fetch(key, { credentials: 'same-origin', headers: { Accept: 'text/html' } }).then(function (res) {
        if (res.redirected || !res.ok) throw new Error('not a page');
        return res.text();
      }).then(function (html) { return new DOMParser().parseFromString(html, 'text/html'); });
      pages[key].catch(function () { delete pages[key]; });
    }
    return pages[key];
  }

  /* ---------- Sheets: slide up over the current page, scrim behind, the page inert; leave the same way ---------- */
  var layer = $('sheet-layer');
  var sheet = { card: null, url: '', pushed: false, opener: null }, ignorePop = 0;
  function cards() { return layer ? [].slice.call(layer.querySelectorAll('.sheet-card')) : []; }
  function cardFor(url) { var k = urlKey(url); return cards().filter(function (c) { return urlKey(c.getAttribute('data-sheet-url')) === k; })[0] || null; }
  function focusables(card) { return [].filter.call(card.querySelectorAll('a[href], button:not([disabled]), input:not([type="hidden"]):not([disabled])'), function (e) { return e.offsetParent !== null || e === document.activeElement; }); }
  function focusFirst(card) {
    var f = card.querySelector('.input.invalid') || card.querySelector('.alert.error') && card.querySelector('#rs-at') || card.querySelector('.sh-body .input:not([disabled])') || card.querySelector('.dlg-actions .btn');
    if (f) f.focus({ preventScroll: true });
  }
  function openSheet(card, opts) {
    opts = opts || {};
    if (sheet.card === card) return;
    clearTimeout(layer.t);
    sheet.opener = opts.opener || (document.activeElement !== document.body ? document.activeElement : null);
    cards().forEach(function (c) { c.hidden = c !== card; });
    sheet.card = card; sheet.url = urlKey(card.getAttribute('data-sheet-url')); sheet.pushed = !!opts.push;
    if (opts.fresh) resetCard(card);
    setup(card);
    layer.hidden = false; layer.offsetWidth; layer.classList.add('open'); app.inert = true;
    if (opts.push && urlKey(location.href) !== sheet.url) history.pushState({ ledgerSheet: sheet.url }, '', sheet.url);
    setTimeout(function () { if (sheet.card === card) focusFirst(card); }, 80);
  }
  function closeSheet(opts) {
    opts = opts || {};
    var card = sheet.card; if (!card) return;
    sheet.card = null; layer.classList.remove('open'); app.inert = false;
    layer.t = setTimeout(function () { if (!sheet.card) { layer.hidden = true; card.hidden = true; } }, 260);
    if (!opts.navigating) {
      var back = sheet.opener && document.contains(sheet.opener) ? sheet.opener : openerFor(sheet.url);
      if (back && back.focus) back.focus({ preventScroll: true });
    }
    if (opts.fromPop || opts.navigating) return;
    if (sheet.pushed) { ignorePop++; history.back(); }
    else history.replaceState(null, '', layer.getAttribute('data-base'));
  }
  /* Where focus goes when a sheet that arrived with the page closes: the control that opens it */
  function openerFor(url) {
    var k = urlKey(url), all = document.querySelectorAll('[data-sheet-open]');
    for (var i = 0; i < all.length; i++) { var u = all[i].getAttribute('data-sheet-open') || all[i].getAttribute('href'); if (u && urlKey(u) === k) return all[i].closest('.menu') ? document.querySelector('[aria-controls="' + all[i].closest('.menu').id + '"]') : all[i]; }
    return null;
  }
  function showSheet(url, opener) {
    var card = cardFor(url);
    if (card) { openSheet(card, { push: true, opener: opener, fresh: true }); return; }
    fetchDoc(url).then(function (doc) {
      var src = doc.querySelector('#sheet-layer .sheet-card[data-sheet-url]:not([hidden])');
      if (!src) throw new Error('no sheet');
      var c = cardFor(url); if (c) c.remove();
      c = document.importNode(src, true); c.hidden = true; layer.appendChild(c);
      openSheet(c, { push: true, opener: opener });
    }).catch(function () { location.assign(url); });
  }
  /* A sheet opened again in place starts fresh, as in the prototype: the time is now, nothing typed, no old errors */
  function resetCard(card) {
    var at = card.querySelector('#rs-at'); if (!at) return;
    at.value = fmtUtc(formNow(at.form)); card.querySelector('#rs-ref').value = '';
    [].forEach.call(card.querySelectorAll('.alert.error'), function (a) { a.remove(); });
    [].forEach.call(card.querySelectorAll('.field'), function (f) { setErr(f, ''); });
    at.dispatchEvent(new Event('input'));
  }

  if (layer) {
    /* The page arrived with its sheet open (its own address): play the opening, as if it was clicked */
    var initial = layer.classList.contains('open') ? cards().filter(function (c) { return !c.hidden; })[0] : null;
    if (initial) {
      sheet.card = initial; sheet.url = urlKey(location.href); sheet.pushed = false;
      setup(initial);
      if (!reduceMotion.matches) { layer.classList.remove('open'); layer.offsetWidth; requestAnimationFrame(function () { layer.classList.add('open'); }); }
      app.inert = true;
      setTimeout(function () { if (sheet.card === initial) focusFirst(initial); }, 80);
    }
    cards().forEach(setup);
  }

  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var t = e.target;
    var op = t.closest('[data-sheet-open]');
    if (op && layer && !layer.contains(op)) {
      e.preventDefault();
      var opener = op, menu = op.closest('.menu');
      if (menu) { menu.hidden = true; var mb = document.querySelector('[aria-controls="' + menu.id + '"]'); if (mb) { mb.setAttribute('aria-expanded', 'false'); opener = mb; } }
      showSheet(op.getAttribute('data-sheet-open') || op.getAttribute('href'), opener);
      return;
    }
    if (layer && sheet.card && t.closest('[data-close]') && layer.contains(t)) { e.preventDefault(); closeSheet(); return; }
    var copy = t.closest('[data-copy-report]');
    if (copy) {
      var text = copy.getAttribute('data-copy-report');
      try { navigator.clipboard.writeText(text).then(function () { toast('Report copied', "Paste it into the authority's reporting form.", true); }, function () { toast('Copy blocked', 'Select the report text and copy it instead.'); }); }
      catch (err) { toast('Copy blocked', 'Select the report text and copy it instead.'); }
      return;
    }
    var tab = t.closest('#rp-tabs > a');
    if (tab && tab.getAttribute('aria-current') !== 'page') { e.preventDefault(); switchReport(tab.getAttribute('href'), true); }
  });
  /* Start loading a sheet the moment it's pressed */
  document.addEventListener('pointerdown', function (e) {
    var op = e.target.closest && e.target.closest('[data-sheet-open]');
    if (op && layer && !cardFor(op.getAttribute('data-sheet-open') || op.getAttribute('href'))) fetchDoc(op.getAttribute('data-sheet-open') || op.getAttribute('href')).catch(function () {});
  }, true);
  /* Esc closes; Tab stays inside; "/" doesn't open the command field behind the sheet */
  window.addEventListener('keydown', function (e) {
    if (!sheet.card) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeSheet(); return; }
    if (e.key === '/') { e.stopPropagation(); return; }
    if (e.key === 'Tab') {
      var f = focusables(sheet.card); if (!f.length) return;
      var i = f.indexOf(document.activeElement);
      if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && (i === f.length - 1 || i < 0)) { e.preventDefault(); f[0].focus(); }
    }
  }, true);
  window.addEventListener('popstate', function () {
    if (ignorePop) { ignorePop--; syncReport(); return; }
    var here = urlKey(location.href);
    if (sheet.card && sheet.url !== here) closeSheet({ fromPop: true });
    var c = layer && cardFor(here);
    if (c && !sheet.card) { openSheet(c, {}); return; }
    syncReport();
  });

  /* ---------- Fields: one line of error text under the field ---------- */
  function setErr(field, msg) {
    var e = field.querySelector('.err'), inp = field.querySelector('.input'); if (!e) return;
    e.querySelector('span').textContent = msg || ''; e.hidden = !msg;
    if (inp) { inp.classList.toggle('invalid', !!msg); if (msg) inp.setAttribute('aria-invalid', 'true'); else inp.removeAttribute('aria-invalid'); }
  }

  /* ---------- One POST, then either the page it lands on or the sheet again with the API's errors ---------- */
  function busy(btn, on) {
    if (!btn) return;
    if (on) { btn.dataset.label = btn.textContent; btn.classList.add('busy'); btn.setAttribute('aria-busy', 'true'); btn.innerHTML = '<span class="spin" aria-hidden="true"></span><span class="sr-only">' + btn.dataset.label + '</span>'; }
    else { btn.classList.remove('busy'); btn.removeAttribute('aria-busy'); btn.textContent = btn.dataset.label || btn.textContent; }
  }
  function post(form, btn, card) {
    if (form.dataset.sending) return;
    form.dataset.sending = '1'; busy(btn, true);
    fetch(form.action, { method: 'POST', body: new FormData(form), credentials: 'same-origin', redirect: 'manual', headers: { Accept: 'text/html' } }).then(function (res) {
      if (res.type === 'opaqueredirect' || (res.status >= 300 && res.status < 400)) {
        /* Done: the sheet leaves, then the ticket page arrives with the toast (the sheet's address leaves history) */
        closeSheet({ navigating: true });
        setTimeout(function () { location.replace(form.getAttribute('data-done')); }, reduceMotion.matches ? 0 : 200);
        return;
      }
      return res.text().then(function (html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        var fresh = doc.querySelector('.sheet-card[data-sheet="' + card.getAttribute('data-sheet') + '"]');
        if (!fresh) { location.assign(form.getAttribute('data-done')); return; }
        card.replaceChildren.apply(card, [].map.call(fresh.childNodes, function (n) { return document.importNode(n, true); }));
        setup(card); focusFirst(card);
      });
    }).catch(function () {
      delete form.dataset.sending; busy(btn, false);
      toast("Couldn't reach Ledger", 'Check your connection and try again.');
    });
  }

  function setup(card) {
    if (card.getAttribute('data-sheet') === 'record') setupRecord(card);
    else if (card.getAttribute('data-sheet') === 'close') setupClose(card);
  }

  /* ---------- Record Submission ---------- */
  function setupRecord(card) {
    var form = card.querySelector('#rs-form'); if (!form || form._ready) return; form._ready = true;
    var at = form.querySelector('#rs-at'), out = form.querySelector('#rs-outcome'), go = card.querySelector('#rs-go');
    var due = Date.parse(form.getAttribute('data-due')), aware = Date.parse(form.getAttribute('data-aware')), blocked = form.hasAttribute('data-blocked');
    var shown = '';
    /* On time or late: the entered time against the report's due_at, both as the API gave them. The API decides whether
       the time is allowed, so the preview only shows for a time between awareness and now, and says nothing otherwise. */
    function update() {
      if (blocked) return;
      var t = parseUtc(at.value), key = '', html = '';
      if (!isNaN(t) && !isNaN(due) && t <= formNow(form) && (isNaN(aware) || t >= aware)) {
        var onTime = t <= due, b = BADGE[onTime ? 'submitted' : 'late'];
        key = onTime ? 'on' : 'late';
        html = '<span class="badge ' + b[0] + '"><svg class="i" aria-hidden="true"><use href="#i-check"/></svg>' + b[1] + '</span><span>' +
          (t === due ? 'Right at the deadline.' : onTime ? span(due - t) + ' before the deadline.' : span(t - due) + ' after the deadline.') + '</span>';
      }
      out.innerHTML = html;
      if (key && key !== shown) { out.classList.remove('enter'); out.offsetWidth; out.classList.add('enter'); }
      shown = key;
    }
    at.addEventListener('input', function () { setErr(at.closest('.field'), ''); update(); });
    at.addEventListener('blur', function () { if (at.value.trim() && isNaN(parseUtc(at.value))) setErr(at.closest('.field'), 'Use the format 2026-10-29 14:00:00.'); });
    var ref = form.querySelector('#rs-ref');
    ref.addEventListener('input', function () { setErr(ref.closest('.field'), ''); });
    form.querySelector('#rs-now').addEventListener('click', function () { at.value = fmtUtc(formNow(form)); setErr(at.closest('.field'), ''); update(); });
    form.addEventListener('submit', function (e) { e.preventDefault(); if (!go.disabled) post(form, go, card); });
    update();
  }

  /* ---------- Close Ticket ---------- */
  function setupClose(card) {
    var form = card.querySelector('#cl-form'); if (!form || form._ready) return; form._ready = true;
    form.addEventListener('submit', function (e) { e.preventDefault(); post(form, card.querySelector('#cl-go'), card); });
  }

  /* ---------- Report Draft: switch report type in place. The indicator slides at once; the old draft leaves first, then
     the new one rises in. Back and Forward do the same. ---------- */
  var swapToken = 0;
  function switchReport(url, push) {
    var swap = $('rp-swap'); if (!swap || !tabs) { location.assign(url); return; }
    var k = urlKey(url), token = ++swapToken;
    [].forEach.call(tabs.querySelectorAll('a'), function (a) { if (urlKey(a.getAttribute('href')) === k) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    placeInd(tabs);
    if (push) history.pushState({ ledgerReport: k }, '', k);
    swap.classList.remove('entering'); swap.classList.add('leaving');
    var left = new Promise(function (r) { setTimeout(r, reduceMotion.matches ? 150 : 140); });
    Promise.all([fetchDoc(k), left]).then(function (r) {
      if (token !== swapToken) return;
      var doc = r[0], next = doc.getElementById('rp-swap'); if (!next) throw new Error('no draft');
      delete pages[k];   /* drafts change as the ticket does: fetch again next time */
      swap.innerHTML = next.innerHTML; swap.setAttribute('data-kind', next.getAttribute('data-kind'));
      document.title = doc.title;
      var nl = doc.getElementById('sheet-layer');
      if (layer && nl) {
        layer.setAttribute('data-base', nl.getAttribute('data-base'));
        cards().forEach(function (c) { if (c !== sheet.card) c.remove(); });
        [].forEach.call(nl.querySelectorAll('.sheet-card'), function (c) { var n = document.importNode(c, true); n.hidden = true; layer.appendChild(n); setup(n); });
      }
      swap.classList.remove('leaving'); swap.offsetWidth; swap.classList.add('entering');
      swap.addEventListener('animationend', function done() { swap.classList.remove('entering'); swap.removeEventListener('animationend', done); });
    }).catch(function () { if (token === swapToken) location.assign(k); });
  }
  function syncReport() {
    var swap = $('rp-swap'); if (!swap || !tabs) return;
    var m = /\/reports\/([a-z_]+)$/.exec(location.pathname);
    if (m && m[1] !== swap.getAttribute('data-kind')) switchReport(location.pathname, false);
  }
})();
