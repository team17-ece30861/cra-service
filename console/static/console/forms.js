/* New Ticket, Edit Ticket and Triage sheets (4.U2 part 2; ported from docs/design/ledger-screens.html). Checks here are
   only help while typing (a required field left empty, a CVE ID or time in the wrong shape): the API judges every value,
   and its answer comes back under the fields. Opening and closing the sheets is ledger.js's job (the Sheets block). */
(function () {
  'use strict';
  var L = window.Ledger || {};
  var reduceMotion = L.reduceMotion || window.matchMedia('(prefers-reduced-motion: reduce)');
  function nowMs() { return L.nowMs ? L.nowMs() : NaN; }
  var TIME_FORMAT = 'Use the format 2026-10-29 14:00:00.';
  var CVE = /^CVE-\d{4}-\d{4,}$/;

  function parseUtc(s) { var m = /^\s*(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?\s*(?:UTC|Z)?\s*$/i.exec(s || ''); if (!m) return NaN; return Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)); }
  function fmtUtc(ms) { return new Date(ms).toISOString().replace('T', ' ').slice(0, 19); }
  function laterMsg() { return "That's later than now. Enter a time at or before " + fmtUtc(nowMs()) + ' UTC.'; }
  function split(text) { return (text || '').split(/[\n,]/).map(function (v) { return v.trim(); }).filter(Boolean); }

  /* One line under the field, a red ring on its control */
  function setErr(field, msg) {
    if (!field) return;
    var e = field.querySelector('.err'), ctl = field.querySelector('.input, .textarea, .select, .chips-input');
    if (e) { e.querySelector('span').textContent = msg || ''; e.hidden = !msg; }
    if (ctl) ctl.classList.toggle('invalid', !!msg);
    [].forEach.call(field.querySelectorAll('input:not([type="hidden"]), textarea, select'), function (c) { if (c.type !== 'radio') { if (msg) c.setAttribute('aria-invalid', 'true'); else c.removeAttribute('aria-invalid'); } });
    field.classList.toggle('invalid-group', !!msg && !ctl);
  }
  function hasErr(form) { return !!form.querySelector('.field:not(:has([data-chips])) .err:not([hidden])'); }

  /* ---------- Chips (versions, member states): the typed text input becomes chips plus one hidden value ---------- */
  function initChips(box, onChange) {
    var inp = box.querySelector('input'), field = box.closest('.field'), form = box.closest('form');
    var eu = box.hasAttribute('data-eu') ? (form.getAttribute('data-eu') || '').split(' ') : null;
    var hidden = document.createElement('input');
    hidden.type = 'hidden'; hidden.name = inp.name; inp.removeAttribute('name');
    box.appendChild(hidden);
    var values = [];
    box._values = function () { return values.slice(); };
    box._initial = inp.hasAttribute('data-initial') ? split(inp.getAttribute('data-initial')) : null;
    function sync() { hidden.value = values.join('\n'); onChange(); }
    function chip(v) {
      var c = document.createElement('span'); c.className = 'chip'; c.textContent = v + ' ';
      var x = document.createElement('button'); x.type = 'button'; x.setAttribute('aria-label', 'Remove ' + v);
      x.innerHTML = '<svg class="i sm" aria-hidden="true"><use href="#i-x"/></svg>';
      x.addEventListener('click', function () { remove(c, v); inp.focus(); });
      c.appendChild(x); box.insertBefore(c, inp);
    }
    function remove(c, v) {
      var i = values.indexOf(v); if (i < 0) return;
      values.splice(i, 1); setErr(field, null); sync();
      if (reduceMotion.matches) { c.remove(); return; }
      c.classList.add('leaving'); c.addEventListener('animationend', function () { c.remove(); }, { once: true });
    }
    function add(raw) {
      var v = raw.trim().replace(/,$/, '').trim(); if (!v) return true;
      if (eu) {
        v = v.toUpperCase();
        if (eu.indexOf(v) < 0) { setErr(field, v === 'EL' ? 'Use GR for Greece.' : v + " isn't an EU member state code."); return false; }
      }
      setErr(field, null);
      if (values.indexOf(v) < 0) { values.push(v); chip(v); sync(); }
      return true;
    }
    split(inp.value).forEach(function (v) { if (eu) v = v.toUpperCase(); if (values.indexOf(v) < 0) { values.push(v); chip(v); } });
    [].forEach.call(box.querySelectorAll('.chip'), function (c) { c.style.animation = 'none'; });
    inp.value = ''; hidden.value = values.join('\n');
    box._commit = function () { if (inp.value.trim() && add(inp.value)) inp.value = ''; };
    box.addEventListener('click', function (e) { if (e.target === box) inp.focus(); });
    inp.addEventListener('input', function () { if (inp.value.indexOf(',') >= 0) { inp.value.split(',').slice(0, -1).forEach(add); inp.value = inp.value.split(',').pop(); } });
    inp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); if (add(inp.value)) inp.value = ''; }
      else if (e.key === 'Backspace' && !inp.value && values.length) {
        var last = box.querySelectorAll('.chip:not(.leaving)'); last = last[last.length - 1];
        if (last) remove(last, values[values.length - 1]);
      }
    });
    inp.addEventListener('blur', function () { box._commit(); });
  }

  /* ---------- New Ticket / Edit Ticket ---------- */
  function initTicketForm(form) {
    var card = form.closest('.sheet-card'), go = card.querySelector('[data-go]'), edit = form.getAttribute('data-mode') === 'edit';
    var more = form.querySelector('.sh-more');
    function current(el) { return el.classList.contains('chips-input') ? el._values().join('\n') : el.value.trim(); }
    function initial(el) { return el.classList.contains('chips-input') ? (el._initial || []).join('\n') : (el.getAttribute('data-initial') || '').trim(); }
    var tracked = [];
    function update() {
      var n = 0;
      if (edit) {
        tracked.forEach(function (el) {
          var diff = current(el) !== initial(el); if (diff) n++;
          el.closest('.field').classList.toggle('changed', diff);
        });
      }
      var ok = edit ? n > 0 : [].every.call(form.querySelectorAll('[data-req]'), function (el) { return el.value.trim(); });
      go.disabled = !ok || hasErr(form);
    }
    [].forEach.call(form.querySelectorAll('[data-chips]'), function (box) { initChips(box, update); if (box._initial) tracked.push(box); });
    [].forEach.call(form.querySelectorAll('[data-initial]'), function (el) { if (!el.closest('[data-chips]')) tracked.push(el); });

    /* Typing in a field clears its error (you're fixing it); leaving it checks again */
    form.addEventListener('input', function (e) { var fl = e.target.closest('.field'); if (fl && !e.target.closest('[data-chips]')) setErr(fl, null); update(); });
    form.addEventListener('change', update);
    [].forEach.call(form.querySelectorAll('[data-req]'), function (el) {
      el.addEventListener('blur', function () { if (!el.value.trim()) setErr(el.closest('.field'), el.getAttribute('data-req')); update(); });
    });
    [].forEach.call(form.querySelectorAll('[data-cve]'), function (el) {
      el.addEventListener('blur', function () { var v = el.value.trim(); if (v && !CVE.test(v)) setErr(el.closest('.field'), el.getAttribute('data-cve')); update(); });
    });
    [].forEach.call(form.querySelectorAll('[data-time]'), function (el) {
      el.addEventListener('blur', function () {
        var v = el.value.trim(), t = parseUtc(v), fl = el.closest('.field'), aware = el.getAttribute('data-time') === 'aware';
        if (!v) { if (aware) setErr(fl, 'Enter when your team became aware.'); }
        else if (isNaN(t)) setErr(fl, TIME_FORMAT);
        else if (aware && t > nowMs()) setErr(fl, laterMsg());
        update();
      });
    });
    /* Report details: opening it lets its fields arrive one after another */
    if (more) {
      var body = more.querySelector('.sh-more-body');
      [].forEach.call(body.children, function (c, i) { c.style.setProperty('--i', i); });
      more.addEventListener('toggle', function () {
        if (!more.open || reduceMotion.matches) return;
        body.classList.remove('opening'); body.offsetWidth; body.classList.add('opening');
        setTimeout(function () { body.classList.remove('opening'); }, 700);
      });
    }
    /* Asked to bring a field into view (?focus=, e.g. from a report's "Add in Edit Ticket") */
    card.addEventListener('sheet:open', function (e) { want(e.detail && e.detail.focus); update(); });
    function want(key) {
      [].forEach.call(form.querySelectorAll('.field.wanted'), function (f) { f.classList.remove('wanted'); });
      var fl = key && form.querySelector('[data-field="' + key + '"]');
      if (!fl) return;
      if (more && more.contains(fl)) more.open = true;
      fl.classList.add('wanted');
    }
    form.addEventListener('submit', function (e) {
      [].forEach.call(form.querySelectorAll('[data-chips]'), function (b) { b._commit(); });
      update();
      if (go.disabled) { e.preventDefault(); return; }
      go.classList.add('busy'); go.setAttribute('aria-busy', 'true');
    });
    update();
  }

  /* ---------- Triage ---------- */
  var TR_LABEL = { actively_exploited: 'Mark Reportable', not_actively_exploited: 'Close Ticket', invalid: 'Close as Invalid' };
  function relStr(ms) { return L.relStr ? L.relStr(ms) : ''; }
  function initTriage(form) {
    var card = form.closest('.sheet-card'), go = card.querySelector('[data-go]');
    var wrap = form.querySelector('#tr-aware-wrap'), aware = form.querySelector('#tr-aware'), reason = form.querySelector('#tr-reason');
    var pv = form.querySelector('#tr-preview'), offsets = {};
    try { offsets = JSON.parse(form.getAttribute('data-offsets')); } catch (err) { offsets = {}; }
    var ROWS = [['early_warning', 'Early warning due'], ['notification', 'Notification due']];
    function decision() { var r = form.querySelector('input[name="decision"]:checked'); return r ? r.value : ''; }
    function preview(t) {
      if (isNaN(t)) { pv.innerHTML = ''; return; }
      var html = '<div class="pv-h"><span>Preview</span><span>The service sets the deadlines when you save</span></div>';
      ROWS.forEach(function (r) {
        if (offsets[r[0]] == null) return;
        var due = t + offsets[r[0]] * 1000, left = due - nowMs();
        html += '<div class="pv"><span>' + r[1] + '</span><span class="mono">' + fmtUtc(due) + ' UTC</span><span class="rl' + (left < 0 ? ' late' : left < 12 * 3600000 ? ' soon' : '') + '">' + relStr(left) + '</span></div>';
      });
      pv.innerHTML = html;
    }
    function update() {
      var d = decision(), ae = d === 'actively_exploited';
      wrap.classList.toggle('open', ae);
      wrap.firstElementChild.inert = !ae;
      go.textContent = TR_LABEL[d] || 'Triage';
      var t = parseUtc(aware.value), awareOk = !ae || (!isNaN(t) && t <= nowMs());
      preview(ae && awareOk ? t : NaN);
      go.disabled = !(d && reason.value.trim() && awareOk) || hasErr(form);
    }
    [].forEach.call(form.querySelectorAll('input[name="decision"]'), function (r) {
      r.addEventListener('change', function () { setErr(form.querySelector('[data-field="decision"]'), null); update(); });
    });
    reason.addEventListener('input', function () { setErr(reason.closest('.field'), null); update(); });
    aware.addEventListener('input', function () { setErr(aware.closest('.field'), null); update(); });
    aware.addEventListener('blur', function () {
      var v = aware.value.trim(), t = parseUtc(v), fl = aware.closest('.field');
      if (!v) setErr(fl, 'Enter when your team became aware. Deadlines count from it.');
      else if (isNaN(t)) setErr(fl, TIME_FORMAT);
      else if (t > nowMs()) setErr(fl, laterMsg());
      update();
    });
    form.querySelector('#tr-now').addEventListener('click', function () { aware.value = fmtUtc(nowMs()); setErr(aware.closest('.field'), null); update(); aware.focus(); });
    /* The option cards press like every other control */
    [].forEach.call(form.querySelectorAll('.opt'), function (o) {
      o.addEventListener('pointerdown', function (e) { if (e.button === 0) o.classList.add('is-pressed'); });
      ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (ev) { o.addEventListener(ev, function () { o.classList.remove('is-pressed'); }); });
    });
    form.addEventListener('submit', function (e) { update(); if (go.disabled) { e.preventDefault(); return; } go.classList.add('busy'); go.setAttribute('aria-busy', 'true'); });
    card.addEventListener('sheet:open', update);
    update();
  }

  [].forEach.call(document.querySelectorAll('form.tf-form'), initTicketForm);
  [].forEach.call(document.querySelectorAll('form.tr-form'), initTriage);
  /* Coming back to a page from the browser's cache: the action button is ready again */
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) [].forEach.call(document.querySelectorAll('[data-go].busy'), function (b) { b.classList.remove('busy'); b.removeAttribute('aria-busy'); });
  });
})();
