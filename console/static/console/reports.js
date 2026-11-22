/* Ledger report pages (4.U3; ported from docs/design/ledger-screens.html): what's particular to the Record Submission sheet
   (the on-time or late preview), copying a report, and the Report Draft page switching report type in place. Opening,
   closing and saving sheets, toasts, and refreshing the page after a save are ledger.js's (its Sheets block); this file sets
   up a Record Submission card whenever one arrives ('sheet:ready'). Everything works without this file: every sheet has
   its own address and every form posts normally. */
(function () {
  'use strict';
  var app = document.getElementById('app');
  if (!app) return;
  var L = window.Ledger || {};
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  function $(id) { return document.getElementById(id); }
  function toast(title, body, ok) { if (L.toast) L.toast(title, body, ok); }

  /* The service clock: the page carries the service's "now" (core.clock, which follows a fixed test clock); the browser's
     clock is never read. Time moves forward from it with performance.now(), as in ledger.js. */
  var T0, P0, W0;
  function syncNow() { T0 = Date.parse(app.getAttribute('data-now')); P0 = performance.now(); W0 = Date.now(); if (isNaN(T0)) T0 = 0; }
  syncNow();
  document.addEventListener('ledger:refreshed', syncNow);
  /* Elapsed time is a difference of the browser's clocks, never its absolute time. performance.now() can stall while a laptop
     sleeps, so the larger of the two differences wins and "now" never falls behind. */
  function nowMs() { return T0 + Math.max(performance.now() - P0, Date.now() - W0); }
  /* A fixed test clock (PUT /test/clock) doesn't move in the service, so "now" doesn't move here either */
  function formNow(form) { var f = form && form.hasAttribute('data-clock-fixed') && Date.parse(form.getAttribute('data-now')); return f || nowMs(); }

  /* Times as people type them: "YYYY-MM-DD HH:MM[:SS]" in UTC */
  /* A time that doesn't exist (2026-02-30, 25:00) is NaN, not the date it would roll over to */
  function parseUtc(s) {
    var m = /^\s*(\d{4})-(\d{2})-(\d{2})[ Tt](\d{2}):(\d{2})(?::(\d{2}))?\s*(?:UTC|Z)?\s*$/i.exec(s || ''); if (!m) return NaN;
    var t = Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)), d = new Date(t);
    return d.getUTCFullYear() === +m[1] && d.getUTCMonth() === m[2] - 1 && d.getUTCDate() === +m[3] && d.getUTCHours() === +m[4] && d.getUTCMinutes() === +m[5] && d.getUTCSeconds() === +(m[6] || 0) ? t : NaN;
  }
  function fmtUtc(ms) { return new Date(Math.floor(ms / 1000) * 1000).toISOString().replace('T', ' ').slice(0, 19); }
  function span(ms) { var m = Math.round(Math.abs(ms) / 60000), d = Math.floor(m / 1440), h = Math.floor(m / 60) % 24; return d ? d + ' d ' + h + ' h' : Math.floor(m / 60) + ' h ' + (m % 60) + ' m'; }
  var BADGE = { submitted: ['submitted', 'Submitted'], late: ['late', 'Submitted late'] };
  function urlKey(u) { var a = new URL(u, location.href); return a.pathname + a.search; }

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
  document.addEventListener('ledger:refreshed', function () { tabs = $('rp-tabs'); if (tabs) placeInd(tabs, true); });
  if (tabs) {
    placeInd(tabs, true);
    window.addEventListener('resize', function () { placeInd(tabs, true); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { placeInd(tabs, true); });
    var cur = tabs.querySelector('[aria-current="page"]');
    if (cur && cur.scrollIntoView && tabs.scrollWidth > tabs.clientWidth) tabs.scrollLeft = cur.offsetLeft - 8;
  }

  /* ---------- Fields: one line of error text under the field ---------- */
  function setErr(field, msg) {
    var e = field.querySelector('.err'), inp = field.querySelector('.input'); if (!e) return;
    e.querySelector('span').textContent = msg || ''; e.hidden = !msg;
    if (inp) { inp.classList.toggle('invalid', !!msg); if (msg) inp.setAttribute('aria-invalid', 'true'); else inp.removeAttribute('aria-invalid'); }
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
    at.addEventListener('blur', function () {
      if (!at.value.trim() || !isNaN(parseUtc(at.value))) return;
      var shaped = /^\s*\d{4}-\d{2}-\d{2}[ Tt]\d{2}:\d{2}(:\d{2})?\s*(UTC|Z)?\s*$/i.test(at.value);
      setErr(at.closest('.field'), shaped ? "That isn't a real date and time." : 'Use the format 2026-10-29 14:00:00.');
    });
    var ref = form.querySelector('#rs-ref');
    ref.addEventListener('input', function () { setErr(ref.closest('.field'), ''); });
    form.querySelector('#rs-now').addEventListener('click', function () { at.value = fmtUtc(formNow(form)); setErr(at.closest('.field'), ''); update(); });
    /* Saving is ledger.js's; a blocked report doesn't post */
    form.addEventListener('submit', function (e) { if (go.disabled) e.preventDefault(); });
    update();
  }

  /* A sheet opened again in place starts fresh, as in the prototype: the time is now, nothing typed, no old errors */
  function resetCard(card) {
    var at = card.querySelector('#rs-at'); if (!at) return;
    at.value = fmtUtc(formNow(at.form)); card.querySelector('#rs-ref').value = '';
    [].forEach.call(card.querySelectorAll('.alert.error'), function (a) { a.remove(); });
    [].forEach.call(card.querySelectorAll('.field'), function (f) { setErr(f, ''); });
    at.dispatchEvent(new Event('input'));
  }
  function setupAll(root) { [].forEach.call(root.querySelectorAll('.sheet-card[data-sheet="record"]'), setupRecord); }
  setupAll(document);
  document.addEventListener('sheet:ready', function (e) { if (e.target.matches('.sheet-card[data-sheet="record"]')) setupRecord(e.target); });
  document.addEventListener('sheet:open', function (e) { if (e.target.matches('.sheet-card[data-sheet="record"]')) resetCard(e.target); });

  document.addEventListener('click', function (e) {
    var copy = e.target.closest('[data-copy-report]');
    if (copy) {
      var text = copy.getAttribute('data-copy-report');
      try { navigator.clipboard.writeText(text).then(function () { toast('Report copied', "Paste it into the authority's reporting form.", true); }, function () { toast('Copy blocked', 'Select the report text and copy it instead.'); }); }
      catch (err) { toast('Copy blocked', 'Select the report text and copy it instead.'); }
      return;
    }
    var tab = e.target.closest('#rp-tabs > a');
    if (tab && tab.getAttribute('aria-current') !== 'page' && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey) { e.preventDefault(); switchReport(tab.getAttribute('href'), true); }
  });
  /* Back and Forward between report types (ledger.js asks: it handles sheets) */
  document.addEventListener('ledger:history', function (e) { if (syncReport()) e.preventDefault(); });

  /* ---------- Report Draft: switch report type in place. The indicator slides at once; the old draft leaves first, then
     the new one rises in. Back and Forward do the same. ---------- */
  var swapToken = 0;
  function switchReport(url, push) {
    var swap = $('rp-swap'); if (!swap || !tabs) { location.assign(url); return; }
    var k = urlKey(url), token = ++swapToken;
    [].forEach.call(tabs.querySelectorAll('a'), function (a) { if (urlKey(a.getAttribute('href')) === k) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    placeInd(tabs);
    if (push) history.pushState({ ledgerReport: k }, '', k);
    if (L.shown) L.shown(k);
    swap.classList.remove('entering'); swap.classList.add('leaving');
    var left = new Promise(function (r) { setTimeout(r, reduceMotion.matches ? 150 : 140); });
    var page = fetch(k, { credentials: 'same-origin', headers: { Accept: 'text/html' } }).then(function (res) {
      if (res.redirected || !res.ok) throw new Error('not a page');
      return res.text();
    }).then(function (html) { return new DOMParser().parseFromString(html, 'text/html'); });
    Promise.all([page, left]).then(function (r) {
      if (token !== swapToken) return;
      var doc = r[0], next = doc.getElementById('rp-swap'); if (!next) throw new Error('no draft');
      swap.innerHTML = next.innerHTML; swap.setAttribute('data-kind', next.getAttribute('data-kind'));
      if (L.adopt) L.adopt(doc);
      document.title = doc.title;
      /* This report type's Record Submission sheet */
      var layer = $('sheet-layer'), nl = doc.getElementById('sheet-layer'), open = L.openCard && L.openCard();
      if (layer && nl) {
        layer.setAttribute('data-base', nl.getAttribute('data-base'));
        [].forEach.call(layer.querySelectorAll(':scope > .sheet-card'), function (c) { if (c !== open) c.remove(); });
        [].forEach.call(nl.querySelectorAll(':scope > .sheet-card'), function (c) { var n = document.importNode(c, true); n.hidden = true; layer.appendChild(n); if (L.cardReady) L.cardReady(n); });
      }
      swap.classList.remove('leaving'); swap.offsetWidth; swap.classList.add('entering');
      swap.addEventListener('animationend', function done() { swap.classList.remove('entering'); swap.removeEventListener('animationend', done); });
    }).catch(function () { if (token === swapToken) location.assign(k); });
  }
  /* Whether this address is a report type this page shows (switching to it if needed) */
  function syncReport() {
    var swap = $('rp-swap'); if (!swap || !tabs || location.search) return false;
    var m = /\/reports\/([a-z_]+)$/.exec(location.pathname);
    if (!m) return false;
    if (m[1] !== swap.getAttribute('data-kind')) switchReport(location.pathname, false);
    return true;
  }
})();
