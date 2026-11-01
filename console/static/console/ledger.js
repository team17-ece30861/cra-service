/* Ledger app shell (docs/design.md; ported from docs/design/ledger-screens.html): springs, the press system, the numeric
   text transition and the ticking clock, the deadline island, the dock with its command field, list rows, menus and toasts.
   Pages work without it: links are links, and countdowns show the time the page was made. */
(function () {
  'use strict';
  var root = document.documentElement;
  var app = document.getElementById('app');
  if (!app) return;
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  function $(id) { return document.getElementById(id); }
  function mk(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

  /* ---------- Springs: generate CSS linear() curves from damping + response ---------- */
  function springFn(damping, response) {
    var w = 2 * Math.PI / response;
    if (damping >= 1) return function (t) { return 1 - (1 + w * t) * Math.exp(-w * t); };
    var wd = w * Math.sqrt(1 - damping * damping), zw = damping * w;
    return function (t) { return 1 - Math.exp(-zw * t) * (Math.cos(wd * t) + (zw / wd) * Math.sin(wd * t)); };
  }
  function settleTime(fn) {
    var last = 0;
    for (var t = 0; t < 3; t += 0.005) { if (Math.abs(1 - fn(t)) > 0.001) last = t; }
    return Math.min(last + 0.01, 3);
  }
  function linearEasing(fn, T, n) {
    var pts = [];
    for (var i = 0; i <= n; i++) pts.push(+fn(T * i / n).toFixed(4));
    pts[n] = 1;
    return 'linear(' + pts.join(', ') + ')';
  }
  var smooth = springFn(1.0, 0.35), bounce = springFn(0.8, 0.30);
  var Ts = settleTime(smooth), Tb = settleTime(bounce);
  if (window.CSS && CSS.supports && CSS.supports('transition-timing-function', 'linear(0, 1)')) {
    root.style.setProperty('--spring-smooth', linearEasing(smooth, Ts, 40));
    root.style.setProperty('--spring-smooth-dur', Math.round(Ts * 1000) + 'ms');
    root.style.setProperty('--spring-bounce', linearEasing(bounce, Tb, 50));
    root.style.setProperty('--spring-bounce-dur', Math.round(Tb * 1000) + 'ms');
  }

  /* ---------- The service clock. The page carries the service's "now" (core.clock, which follows a fixed test clock);
     the browser's clock is never read. Time moves forward from it with performance.now(). ---------- */
  var T0 = Date.parse(app.getAttribute('data-now')), P0 = performance.now();
  if (isNaN(T0)) T0 = 0;
  function nowMs() { return T0 + (performance.now() - P0); }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  /* Time left, or the time since an overdue deadline */
  function hmsStr(ms, two) { var s = Math.floor(Math.abs(ms) / 1000), h = Math.floor(s / 3600); return (two ? pad(h) : h) + ':' + pad(Math.floor(s / 60) % 60) + ':' + pad(s % 60); }
  function relStr(ms) {
    var late = ms < 0, m = Math.floor(Math.abs(ms) / 60000), d = Math.floor(m / 1440), h = Math.floor(m / 60) % 24;
    var t = d ? d + ' d ' + h + ' h' : Math.floor(m / 60) + ' h ' + (m % 60) + ' m';
    return late ? t + ' overdue' : 'in ' + t;
  }
  function isoStr(t) { return new Date(t).toISOString().replace('T', ' ').slice(0, 19) + ' UTC'; }

  /* ---------- Toasts: glass, short, sentence case ---------- */
  function toast(title, body, ok) {
    var t = $('toast'); if (!t) return;
    $('toast-title').textContent = title; $('toast-body').textContent = body || '';
    t.querySelector('svg use').setAttribute('href', ok ? '#i-check' : '#i-hourglass');
    t.classList.toggle('ok', !!ok);
    t.classList.add('show'); clearTimeout(toast.t); toast.t = setTimeout(function () { t.classList.remove('show'); }, 3400);
  }

  /* ---------- Morph engine: separate springs for width, height, radius. Interruptible; velocity carries through retargets. ---------- */
  /* Growing may overshoot a little. Shrinking is critically damped and stops at its target, unless a shrink damping is given
     (the dock's height keeps its bounce, and its contents are timed around the dip; see planLanding). */
  function Spring(damping, response, x, shrinkDamping) { this.zg = damping; this.rg = response; this.zs = shrinkDamping == null ? 1 : shrinkDamping; this.x = x; this.v = 0; this.t = x; this.retarget(x); }
  Spring.prototype.retarget = function (t) {
    this.shrink = t < this.x;
    this.z = this.shrink ? this.zs : this.zg;
    this.w = 2 * Math.PI / (this.shrink ? this.rg * 0.8 : this.rg);
    this.t = t;
  };
  Spring.prototype.step = function (dt) {
    var a = -this.w * this.w * (this.x - this.t) - 2 * this.z * this.w * this.v; this.v += a * dt; this.x += this.v * dt;
    if (this.shrink && this.zs >= 1 && this.x < this.t) { this.x = this.t; this.v = 0; }
  };
  Spring.prototype.done = function () { return Math.abs(this.x - this.t) < 0.3 && Math.abs(this.v) < 2; };
  var KEYS = ['w', 'h', 'r'];
  function Morph(apply, onRest, opts) { this.apply = apply; this.onRest = onRest; this.opts = opts || {}; this.s = null; this.raf = 0; }
  Morph.prototype.to = function (target, instant) {
    var self = this;
    if (!this.s) { this.s = this.opts.make ? this.opts.make(target) : { w: new Spring(0.78, 0.36, target.w), h: new Spring(0.72, 0.40, target.h, this.opts.hShrinkDamping), r: new Spring(0.8, 0.36, target.r) }; instant = true; }
    instant = instant || reduceMotion.matches;
    KEYS.forEach(function (k) { self.s[k].retarget(target[k]); if (instant) { self.s[k].x = target[k]; self.s[k].v = 0; } });
    if (instant) { cancelAnimationFrame(this.raf); this.raf = 0; this.apply(target.w, target.h, target.r); if (this.onRest) this.onRest(); return; }
    if (this.raf) return;
    var last = performance.now();
    function frame(now) {
      var dt = Math.min((now - last) / 1000, 1 / 30); last = now;
      for (var i = 0; i < 4; i++) KEYS.forEach(function (k) { self.s[k].step(dt / 4); });
      if (KEYS.every(function (k) { return self.s[k].done(); })) {
        KEYS.forEach(function (k) { self.s[k].x = self.s[k].t; self.s[k].v = 0; });
        self.apply(self.s.w.x, self.s.h.x, self.s.r.x); self.raf = 0; if (self.onRest) self.onRest(); return;
      }
      self.apply(self.s.w.x, self.s.h.x, self.s.r.x);
      self.raf = requestAnimationFrame(frame);
    }
    this.raf = requestAnimationFrame(frame);
  };

  /* ---------- List rows ---------- */
  /* Row actions: the morph needs the deadline text's width (rest) and the button's own width (hover). Measure only while a row
     is at rest, so a measurement never interrupts the morph; the rest width follows the countdown every second. */
  var rowEls = [].slice.call(document.querySelectorAll('.lrow'));
  function measureRow(r, all) {
    var dlEl = r.querySelector('.dl'); if (!dlEl || dlEl.matches(':hover, :focus-within')) return;
    var m = r.querySelector('.act-main'), w = r.querySelector('.when'); if (!m || !w) return;
    if (all) { m.style.transition = 'none'; m.style.width = 'auto'; dlEl.style.setProperty('--w-act', m.offsetWidth + 'px'); m.style.width = ''; }
    dlEl.style.setProperty('--w-rest', w.offsetWidth + 'px');
    if (all) { m.offsetWidth; m.style.transition = ''; }
  }
  function measureAll(all) { rowEls.forEach(function (r) { measureRow(r, all); }); }
  measureAll(true);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { measureAll(true); });
  window.addEventListener('resize', function () { measureAll(true); });
  /* While a list scrolls, rows sliding under the pointer shouldn't light up; hover returns 150 ms after scrolling stops */
  var scroller = $('app-scroll');
  (function () {
    var t = 0;
    function onScroll() { root.classList.add('is-scrolling'); clearTimeout(t); t = setTimeout(function () { root.classList.remove('is-scrolling'); }, 150); }
    if (scroller) scroller.addEventListener('scroll', onScroll, { passive: true });
  })();

  /* ---------- The deadline island ---------- */
  var island = $('island'), heroEl = $('app-hero'), islandMorph = null, islandTarget = function () { return null; };
  function toggleIsland() {}
  if (island) {
    var islandBar = island.querySelector('.bar'), islandMore = island.querySelector('.more'), expandable = !!islandMore;
    islandMorph = new Morph(function (w, h, r) { island.style.width = w + 'px'; island.style.height = h + 'px'; island.style.borderRadius = r + 'px'; });
    islandTarget = function () { var open = island.classList.contains('open'), max = app.clientWidth - 32; return { w: Math.min(open ? 460 : 360, max), h: islandBar.offsetHeight + (open && islandMore ? islandMore.offsetHeight : 0), r: open ? 26 : 22 }; };
    islandMorph.to(islandTarget(), true);
    toggleIsland = function (force) {
      if (!expandable) return;
      var o = island.classList.toggle('open', force);
      island.setAttribute('aria-expanded', o ? 'true' : 'false'); islandMorph.to(islandTarget());
    };
    island.addEventListener('click', function (e) {
      var li = e.target.closest('li[data-href]');
      if (li && island.classList.contains('open')) { location.href = li.getAttribute('data-href'); return; }
      toggleIsland();
    });
    island.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleIsland(); } });
    [].forEach.call(island.querySelectorAll('.more li'), function (li, i) { li.style.setProperty('--i', i); });
    /* On Home the hero shows the same deadline, so the island waits until the hero scrolls away */
    if (heroEl && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          var away = e.isIntersecting; island.classList.toggle('away', away);
          if (away && island.classList.contains('open')) { island.classList.remove('open'); island.setAttribute('aria-expanded', 'false'); islandMorph.to(islandTarget(), true); }
        });
      }, { root: scroller, threshold: 0.35 }).observe(heroEl);
    } else island.classList.remove('away');
  }

  /* ---------- The dock and its command field ---------- */
  var dock = $('dock'), dockNav = dock.querySelector('.dock-nav'), cmdBox = $('cmd'), cmdIn = $('cmd-input');
  var morphSize = { w: 0, h: 0, r: 20 }, growExtra = { w: 0, h: 0 };
  function renderDock() { dock.style.width = (morphSize.w + growExtra.w).toFixed(2) + 'px'; dock.style.height = (morphSize.h + growExtra.h).toFixed(2) + 'px'; dock.style.borderRadius = morphSize.r.toFixed(2) + 'px'; }
  var dockMorph = new Morph(function (w, h, r) { morphSize.w = w; morphSize.h = h; morphSize.r = r; renderDock(); },
    function () { if (!app.classList.contains('cmd-open')) dock.classList.remove('morphing'); }, { hShrinkDamping: 0.78 });
  /* Landing choreography: the dock's top edge dips once (about 4 px) as it closes. Simulate the edge, then plan the icons'
     rise so the first icon finishes exactly when the edge is stable, starting just low enough that the gap between the edge
     and any icon never drops below 4 px (it's 6 px at rest). Icons arrive outward from the search field, which is what lands. */
  var RISE_EASE = [0.3, 0, 0.2, 1], RISE_DUR = 0.30, GAP_TOL = 2, FRAME_LAG = 0.016, LAND_STAGGER = 25;
  var LANDING_RANKS = [3, 2, 1, 0, 0, 0, 0, 0];   /* Tickets, Due, Overdue, To triage, separator, field slot, separator, New */
  function bezierY(c) {
    function bx(t) { return 3 * c[0] * t * (1 - t) * (1 - t) + 3 * c[2] * t * t * (1 - t) + t * t * t; }
    function by(t) { return 3 * c[1] * t * (1 - t) * (1 - t) + 3 * c[3] * t * t * (1 - t) + t * t * t; }
    return function (x) { if (x <= 0) return 0; if (x >= 1) return 1; var lo = 0, hi = 1; for (var i = 0; i < 30; i++) { var m = (lo + hi) / 2; if (bx(m) < x) lo = m; else hi = m; } return by((lo + hi) / 2); };
  }
  var riseEase = bezierY(RISE_EASE);
  function planLanding() {
    var items = dockNav.children, hs = dockMorph.s && dockMorph.s.h, i;
    function plain() { dockNav.style.setProperty('--rise', '0px'); for (i = 0; i < items.length; i++) items[i].style.removeProperty('--d'); }
    if (!hs || reduceMotion.matches) return plain();
    var target = dockNav.offsetHeight, sim = new Spring(hs.zg, hs.rg, hs.x, hs.zs), dt = 1 / 480, traj = [], stable = 0;
    sim.v = hs.v; sim.retarget(target);
    for (i = 1; i <= 720; i++) {
      sim.step(dt);
      var t = i * dt + FRAME_LAG;
      traj.push([t, Math.max(0, target - sim.x)]);
      if (Math.abs(sim.x - target) >= 0.5) stable = t;
    }
    var start = Math.max(0, stable - RISE_DUR), rise = 0;
    traj.forEach(function (p) {
      if (p[0] < start || p[1] <= GAP_TOL) return;
      rise = Math.max(rise, (p[1] - GAP_TOL) / Math.max(1 - riseEase((p[0] - start) / RISE_DUR), 1e-3));
    });
    rise = Math.min(Math.max(rise + 1, 8), 40);
    dockNav.style.setProperty('--rise', rise.toFixed(1) + 'px');
    dockNav.style.setProperty('--rise-dur', Math.round(RISE_DUR * 1000) + 'ms');
    dockNav.style.setProperty('--rise-ease', 'cubic-bezier(' + RISE_EASE.join(', ') + ')');
    for (i = 0; i < items.length; i++) items[i].style.setProperty('--d', Math.round(start * 1000 + (LANDING_RANKS[i] || 0) * LAND_STAGGER) + 'ms');
    dockNav.offsetWidth;
  }
  function dockTarget() {
    if (app.classList.contains('cmd-open')) { var w = Math.min(560, app.clientWidth - 32); cmdBox.style.width = w + 'px'; return { w: w, h: cmdBox.offsetHeight, r: 24 }; }
    return { w: dockNav.offsetWidth, h: dockNav.offsetHeight, r: 20 };
  }
  /* The traveling field rides the same springs as the dock's width. Its "h" spring carries the field's horizontal offset from the dock's center. */
  var fieldEl = $('dock-input'), slotBtn = $('dock-find');
  var fieldMorph = new Morph(function (w, cx, r) {
    fieldEl.style.width = w.toFixed(2) + 'px';
    fieldEl.style.left = 'calc(50% + ' + (cx - w / 2).toFixed(2) + 'px)';
    fieldEl.style.borderRadius = r.toFixed(2) + 'px';
    fieldEl.classList.toggle('compact', w < 120);
  }, null, { make: function (t) { return { w: new Spring(0.78, 0.36, t.w), h: new Spring(0.78, 0.36, t.h), r: new Spring(0.8, 0.36, t.r) }; } });
  function fieldTarget() {
    if (app.classList.contains('cmd-open')) { var W = Math.min(560, app.clientWidth - 32); return { w: W - 12, h: 0, r: 18 }; }
    return { w: slotBtn.offsetWidth, h: slotBtn.offsetLeft + slotBtn.offsetWidth / 2 - dockNav.offsetWidth / 2, r: 14 };
  }
  function morph() { dock.classList.add('morphing'); dockMorph.to(dockTarget()); fieldMorph.to(fieldTarget()); }
  /* Hover grows an item 8% and a press 14%, from its bottom edge. Each item has its own spring, and on every frame the dock's
     extra height is exactly the largest growth among items that show a background (extra width too, for the end items), so glass
     and item move as one. A press blooms a highlight outward from the icon (q: 0 to 1 drives its scale 0.6 to 1 and its opacity),
     and a bare icon only makes the glass grow once that bloom passes its own edge, so the glass eases in instead of jumping. */
  var HOVER_SCALE = 1.08, PRESS_SCALE = 1.14, growRaf = 0, hoveredBtn = null;
  var growItems = [].filter.call(dockNav.children, function (el) { return (el.tagName === 'BUTTON' || el.tagName === 'A') && !el.classList.contains('dock-field'); })
    .map(function (b) { return { b: b, x: 1, v: 0, t: 1, z: 0.8, w: 2 * Math.PI / 0.25, q: 0, qv: 0, bl: 0.6 }; });
  var BLOOM_RESPONSE = 0.32;
  function growFrame(now) {
    var dt = Math.min((now - growFrame.last) / 1000, 1 / 30), busy = false, eh = 0, ew = 0;
    growFrame.last = now;
    growItems.forEach(function (g, i) {
      for (var k = 0; k < 4; k++) { var a = -g.w * g.w * (g.x - g.t) - 2 * g.z * g.w * g.v; g.v += a * dt / 4; g.x += g.v * dt / 4; }
      if (Math.abs(g.x - g.t) < 0.0005 && Math.abs(g.v) < 0.005) { g.x = g.t; g.v = 0; } else busy = true;
      var pressed = g.b.classList.contains('is-pressed'), qt = pressed ? 1 : 0;
      if (reduceMotion.matches) { g.q = qt; g.qv = 0; }
      else {
        var qw = 2 * Math.PI / BLOOM_RESPONSE, qz = pressed ? 0.8 : 1;
        for (var k2 = 0; k2 < 4; k2++) { var qa = -qw * qw * (g.q - qt) - 2 * qz * qw * g.qv; g.qv += qa * dt / 4; g.q += g.qv * dt / 4; }
        if (Math.abs(g.q - qt) < 0.002 && Math.abs(g.qv) < 0.02) { g.q = qt; g.qv = 0; } else busy = true;
      }
      /* pressing: the bloom grows outward and fades in; releasing: it keeps its size and fades out, so the glass eases back */
      if (pressed) g.bl = 0.6 + 0.4 * Math.max(0, g.q); else if (g.q <= 0) g.bl = 0.6;
      var bloom = g.bl, bo = pressed ? Math.min(1, Math.max(0, g.q) * 1.3) : Math.max(0, Math.min(1, g.q));
      g.b.style.setProperty('--bloom', bloom.toFixed(4)); g.b.style.setProperty('--bloom-o', bo.toFixed(3));
      g.b.style.transform = g.x === 1 ? '' : 'scale(' + g.x.toFixed(4) + ')';
      var size = g.b.offsetHeight, solidBg = g.b.matches('[aria-current="page"], .new');
      /* the item scales from its bottom edge; the bloom scales from the item's center */
      var growH = solidBg ? Math.max(0, size * (g.x - 1)) : bo * Math.max(0, size * g.x * (1 + bloom) / 2 - size);
      var growW = solidBg ? Math.max(0, size * (g.x - 1)) : bo * Math.max(0, size * (g.x * bloom - 1));
      eh = Math.max(eh, growH);
      if (i === 0 || i === growItems.length - 1) ew = Math.max(ew, growW);
    });
    growExtra.h = eh; growExtra.w = ew; renderDock();
    growRaf = busy ? requestAnimationFrame(growFrame) : 0;
  }
  function syncGrow() {
    var open = app.classList.contains('cmd-open');
    growItems.forEach(function (g) {
      var pressed = g.b.classList.contains('is-pressed');
      g.t = open || reduceMotion.matches ? 1 : pressed ? PRESS_SCALE : g.b === hoveredBtn ? HOVER_SCALE : 1;
      g.z = pressed ? 0.6 : 0.8;   /* a press swells with a little bounce, like glass under a finger */
    });
    if (!growRaf) { growFrame.last = performance.now(); growRaf = requestAnimationFrame(growFrame); }
  }
  growItems.forEach(function (g) {
    var b = g.b;
    b.addEventListener('pointerenter', function (e) { if (e.pointerType === 'mouse') { hoveredBtn = b; syncGrow(); } });
    b.addEventListener('pointerleave', function () { if (hoveredBtn === b) hoveredBtn = null; syncGrow(); });
    b.addEventListener('presschange', syncGrow);
  });
  /* Stagger indices: dock items left to right; command rows from the input upward */
  [].forEach.call(dockNav.children, function (el, i) { el.style.setProperty('--i', i); });

  /* The command list shows a few suggestions; typing searches every ticket and action on the page */
  var IDLE_ROWS = 4, MATCH_ROWS = 7;
  var cmdItems = [].slice.call(document.querySelectorAll('#cmd-list li[role="option"]')), cmdNone = document.querySelector('#cmd-list .none');
  function visibleCmd() { return cmdItems.filter(function (x) { return !x.hidden; }); }
  function filterCmd() {
    var q = cmdIn.value.trim().toLowerCase(), shown = 0, first = -1, cap = q ? MATCH_ROWS : IDLE_ROWS;
    cmdItems.forEach(function (li, i) {
      var hit = (!q || li.textContent.toLowerCase().indexOf(q) >= 0) && shown < cap;
      li.hidden = !hit; if (hit) { shown++; if (first < 0) first = i; }
    });
    cmdNone.hidden = shown > 0;
    var vis = visibleCmd(); vis.forEach(function (li, i) { li.style.setProperty('--i', vis.length - i); });
    selectCmd(first);
  }
  function selectCmd(i) {
    cmdItems.forEach(function (x, j) { x.setAttribute('aria-selected', j === i ? 'true' : 'false'); });
    if (cmdItems[i]) { if (!cmdItems[i].id) cmdItems[i].id = 'cmd-o' + i; cmdIn.setAttribute('aria-activedescendant', cmdItems[i].id); }
    else cmdIn.removeAttribute('aria-activedescendant');
  }
  filterCmd();

  function snapAll() { dockMorph.to(dockTarget(), true); fieldMorph.to(fieldTarget(), true); if (islandMorph) islandMorph.to(islandTarget(), true); }
  snapAll();
  window.addEventListener('resize', snapAll);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(snapAll);
  function openCmd() {
    if (app.classList.contains('cmd-open')) return;
    hoveredBtn = null; app.classList.add('cmd-open'); cmdIn.setAttribute('aria-expanded', 'true'); syncGrow(); morph();
    setTimeout(function () { cmdIn.focus({ preventScroll: true }); }, 60);
  }
  function closeCmd() {
    if (!app.classList.contains('cmd-open')) return;
    planLanding(); app.classList.remove('cmd-open'); cmdIn.setAttribute('aria-expanded', 'false'); cmdIn.blur(); morph();
    setTimeout(function () { cmdIn.value = ''; fieldEl.classList.remove('has-value'); filterCmd(); }, 200);
  }
  function runCmd(li) {
    var href = li.getAttribute('data-href'), soon = li.getAttribute('data-soon'), sheet = li.getAttribute('data-sheet-href');
    closeCmd();
    setTimeout(function () { if (sheet) openSheetHref(sheet, null); else if (href) location.href = href; else if (soon) notYet(soon); }, 140);
  }
  cmdIn.addEventListener('focus', openCmd);
  slotBtn.addEventListener('click', openCmd);
  $('cmd-scrim').addEventListener('click', closeCmd);
  cmdIn.addEventListener('input', function () { fieldEl.classList.toggle('has-value', cmdIn.value.length > 0); filterCmd(); morph(); });
  cmdItems.forEach(function (li, i) { li.addEventListener('mouseenter', function () { selectCmd(i); }); li.addEventListener('click', function () { runCmd(li); }); });
  document.addEventListener('keydown', function (e) {
    var tag = (document.activeElement && document.activeElement.tagName) || '';
    if (e.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test(tag) && !e.metaKey && !e.ctrlKey && !e.altKey) { e.preventDefault(); openCmd(); }
    if (!app.classList.contains('cmd-open')) return;
    if (e.key === 'Escape') closeCmd();
    if (e.key === 'Enter' && document.activeElement === cmdIn) {
      e.preventDefault();
      var sel = cmdItems.filter(function (x) { return !x.hidden && x.getAttribute('aria-selected') === 'true'; })[0];
      if (sel) runCmd(sel); else closeCmd();
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      var vis = visibleCmd(); if (!vis.length) return;
      var k = vis.findIndex(function (x) { return x.getAttribute('aria-selected') === 'true'; });
      k = (k + (e.key === 'ArrowDown' ? 1 : vis.length - 1)) % vis.length;
      selectCmd(cmdItems.indexOf(vis[k]));
    }
  });

  /* ---------- Press system: one pressed state for every control ---------- */
  (function () {
    var PRESSABLE = 'button, .btn, [role="button"], [role="option"], .dock-input, .lrow, .island, .dock-nav > a';
    var SLOP = 10, el = null, rect = null;
    function set(on) {
      if (!el || el.classList.contains('is-pressed') === on) return;
      el.classList.toggle('is-pressed', on);
      el.dispatchEvent(new CustomEvent('presschange', { detail: on }));
    }
    function release() { set(false); el = null; }
    document.addEventListener('pointerdown', function (e) {
      if (e.button !== 0) return;
      release();
      var t = e.target.closest(PRESSABLE);
      if (!t || t.disabled || t.getAttribute('aria-disabled') === 'true') return;
      el = t; rect = t.getBoundingClientRect(); set(true);
    }, true);
    document.addEventListener('pointermove', function (e) {
      if (!el) return;
      set(e.clientX >= rect.left - SLOP && e.clientX <= rect.right + SLOP && e.clientY >= rect.top - SLOP && e.clientY <= rect.bottom + SLOP);
    }, true);
    document.addEventListener('pointerup', release, true);
    document.addEventListener('pointercancel', release, true);
    window.addEventListener('blur', release);
    document.addEventListener('keydown', function (e) {
      if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) { var t = document.activeElement && document.activeElement.closest && document.activeElement.closest('button, .btn, [role="button"], .dock-nav > a'); if (t) { release(); el = t; set(true); } }
    }, true);
    document.addEventListener('keyup', function (e) { if (e.key === ' ' || e.key === 'Enter') release(); }, true);
  })();

  /* ---------- Numeric text transition, the web version of SwiftUI's .contentTransition(.numericText(countsDown:)) ----------
     Only changed characters move: the old one travels 0.42 em, shrinking to 70% and blurring out; the new one arrives from the
     opposite side at 70% and grows to full size. Counting down, digits travel downward. A critically damped spring (response
     0.42 s) drives both, and a slot whose glyph changes width springs to the new width. When several characters change, they go
     one after another from the left, each starting 70 ms after the last. Reduced motion: a short cross-fade. */
  var NT_STEP = 70, NT_SCALE = 0.7, NT_DUR = 620, NT_EASE = (function () { var w = 2 * Math.PI / 0.42, p = []; for (var i = 0; i <= 32; i++) { var t = i / 32 * NT_DUR / 1000; p.push((1 - (1 + w * t) * Math.exp(-w * t)).toFixed(4)); } p[32] = '1'; return 'linear(' + p.join(', ') + ')'; })();
  function ntGlyph(c) { return mk('span', 'nt-g', c); }
  function ntSlot(c) { var sl = mk('span', 'nt-s'); sl.appendChild(ntGlyph(c)); return sl; }
  function ntCurrent(sl) { var k = sl.lastElementChild; while (k && k.classList.contains('nt-out')) k = k.previousElementSibling; return k; }
  function ntSet(el, text, down) {
    if (el._nt === text) return;
    var prev = el._nt, v = el.querySelector(':scope > .nt-v');
    el._nt = text;
    if (prev == null || !v) {
      el.textContent = ''; el.classList.add('nt');
      var sr = mk('span', 'sr-only', text); el.appendChild(sr);
      v = mk('span', 'nt-v'); v.setAttribute('aria-hidden', 'true');
      for (var i = 0; i < text.length; i++) v.appendChild(ntSlot(text[i]));
      el.appendChild(v); return;
    }
    el.firstChild.textContent = text;
    var live = !!el.offsetParent, calm = reduceMotion.matches, dir = down ? 1 : -1;
    var slots = [].filter.call(v.children, function (x) { return !x._leaving; });
    var blur = live ? parseFloat(getComputedStyle(el).fontSize) * 0.08 : 0;
    function out(g, d) {
      g.classList.add('nt-out');
      if (!live) { g.remove(); return; }
      var a = calm ? g.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 150, fill: 'forwards' })
        : g.animate([{ transform: 'translateY(0)', opacity: 1, filter: 'blur(0)' }, { transform: 'translateY(' + 0.42 * dir + 'em) scale(' + NT_SCALE + ')', opacity: 0, filter: 'blur(' + blur + 'px)' }], { duration: NT_DUR * 0.7, delay: d, easing: NT_EASE, fill: 'both' });
      a.onfinish = function () { g.remove(); };
    }
    function inn(g, d) {
      if (!live) return;
      if (calm) g.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150 });
      else g.animate([{ transform: 'translateY(' + -0.42 * dir + 'em) scale(' + NT_SCALE + ')', opacity: 0, filter: 'blur(' + blur + 'px)' }, { transform: 'none', opacity: 1, filter: 'blur(0)' }], { duration: NT_DUR, delay: d, easing: NT_EASE, fill: 'backwards' });
    }
    function resize(sl, w0, d) {
      if (!live || calm) return; var w1 = sl.getBoundingClientRect().width;
      if (Math.abs(w1 - w0) > 0.5) sl.animate([{ width: w0 + 'px' }, { width: w1 + 'px' }], { duration: NT_DUR, delay: d, easing: NT_EASE, fill: 'backwards' });
    }
    var pairs = ntAlign(prev, text), p = 0, order = 0;
    pairs.forEach(function (pr) {
      var oc = pr[0], nc = pr[1], sl = oc != null ? slots[p++] : null;
      if (oc === nc) return;
      var d = calm ? 0 : order++ * NT_STEP;   /* leftmost change first */
      if (sl && nc != null) {
        var w0 = live ? sl.getBoundingClientRect().width : 0, g = ntGlyph(nc), cur = ntCurrent(sl);
        sl.appendChild(g); if (cur) out(cur, d); inn(g, d); resize(sl, w0, d);
      } else if (nc != null) {
        var ns = ntSlot(nc); v.insertBefore(ns, slots[p] || null); inn(ns.firstChild, d); resize(ns, 0, d);
      } else if (sl) {
        sl._leaving = true; var c2 = ntCurrent(sl);
        if (!live) { sl.remove(); return; }
        var w2 = sl.getBoundingClientRect().width; if (c2) out(c2, d);
        sl.animate([{ width: w2 + 'px' }, { width: '0px' }], { duration: calm ? 150 : NT_DUR, delay: d, easing: NT_EASE, fill: 'both' }).onfinish = function () { sl.remove(); };
      }
    });
  }
  /* Pairs old and new characters. When the words match ("in 6 h 10 m" / "in 6 h 9 m"), each number is aligned on its own from the
     right, so only digits move; otherwise the whole strings are aligned from the right. */
  function ntAlign(a, b) {
    var ta = a.match(/\d+|\D+/g) || [], tb = b.match(/\d+|\D+/g) || [], out = [], same = ta.length === tb.length;
    for (var i = 0; same && i < ta.length; i++) if (/\D/.test(ta[i]) !== /\D/.test(tb[i]) || (/\D/.test(ta[i]) && ta[i] !== tb[i])) same = false;
    function right(x, y) { var n = Math.max(x.length, y.length); for (var k = n; k >= 1; k--) out.push([x.length - k >= 0 ? x[x.length - k] : null, y.length - k >= 0 ? y[y.length - k] : null]); }
    if (same) for (var t = 0; t < ta.length; t++) right(ta[t], tb[t]); else right(a, b);
    return out;
  }

  /* ---------- The ticking clock ---------- */
  function countdown(e, two) {
    var ms = Date.parse(e.getAttribute(two ? 'data-hms2' : 'data-hms')) - nowMs(), late = ms < 0;
    ntSet(e, hmsStr(ms, two), !late);
    e.classList.toggle('late', late);
    var left = e.parentNode && e.parentNode.querySelector('[data-left]'); if (left) left.textContent = late ? 'overdue' : 'left';
    if (island && island.contains(e)) island.classList.toggle('late', late);
  }
  function tickClock() {
    var n = nowMs();
    document.querySelectorAll('[data-clock]').forEach(function (e) { e.textContent = isoStr(n); });
    document.querySelectorAll('[data-hms]').forEach(function (e) { countdown(e, false); });
    document.querySelectorAll('[data-hms2]').forEach(function (e) { countdown(e, true); });
    document.querySelectorAll('[data-rl]').forEach(function (e) {
      var ms = Date.parse(e.getAttribute('data-rl')) - n;
      ntSet(e, relStr(ms), ms >= 0); e.classList.toggle('late', ms < 0); e.classList.toggle('soon', ms >= 0 && ms < 12 * 3600000);
    });
    document.querySelectorAll('[data-meter]').forEach(function (e) {
      var due = Date.parse(e.getAttribute('data-due')), start = Date.parse(e.getAttribute('data-start')), ms = due - n;
      var pct = Math.max(0, Math.min(100, Math.round(100 * ms / (due - start))));
      e.firstElementChild.style.width = pct + '%';
      e.classList.toggle('late', ms < 0); e.classList.toggle('soon', ms >= 0 && ms < 12 * 3600000);
      var text = ms < 0 ? relStr(ms) : relStr(ms).slice(3) + ' left of ' + e.getAttribute('data-total');
      e.setAttribute('aria-label', text);
      var label = e.parentNode.querySelector('[data-meter-text]'); if (label) label.textContent = text;
    });
    measureAll(false);
  }
  /* Tick just after each second boundary of the clock. A plain 1 s interval started at load fires right on the boundary, so
     timer jitter lands some ticks just before it and some just after: a second shown twice, then one skipped. */
  (function tick() { tickClock(); setTimeout(tick, 1000 - nowMs() % 1000 + 40); })();

  /* ---------- Menus (account, the ticket's ⋯) ---------- */
  function setMenu(btn, menu, open) { menu.hidden = !open; btn.setAttribute('aria-expanded', open ? 'true' : 'false'); if (open) { var f = menu.querySelector('button'); if (f) f.focus({ preventScroll: true }); } }
  var menus = [].map.call(document.querySelectorAll('[aria-haspopup="menu"]'), function (btn) { return { btn: btn, menu: $(btn.getAttribute('aria-controls')) }; })
    .filter(function (m) { return m.menu; });
  menus.forEach(function (m) {
    m.btn.addEventListener('click', function () { setMenu(m.btn, m.menu, m.menu.hidden); });
    m.menu.addEventListener('keydown', function (e) {
      var items = [].slice.call(m.menu.querySelectorAll('button')), k = items.indexOf(document.activeElement);
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); items[(k + (e.key === 'ArrowDown' ? 1 : items.length - 1)) % items.length].focus(); }
      if (e.key === 'Escape') { setMenu(m.btn, m.menu, false); m.btn.focus(); }
    });
  });
  document.addEventListener('pointerdown', function (e) {
    menus.forEach(function (m) { if (!m.menu.hidden && !e.target.closest('.menu-wrap')) setMenu(m.btn, m.menu, false); });
  });

  /* ---------- Copy the ticket ID ---------- */
  function copyId(btn) {
    var label = btn.id === 'tk-copy' ? btn.querySelector('span') : null;
    function done(ok) {
      if (label) { label.textContent = ok ? 'Copied' : 'Select to copy'; setTimeout(function () { label.textContent = 'Copy'; }, 1600); }
      else toast(ok ? 'Ticket ID copied' : 'Copy blocked', ok ? '' : 'Select the ID and copy it instead.', ok);
    }
    try { navigator.clipboard.writeText(btn.getAttribute('data-copy')).then(function () { done(true); }, function () { done(false); }); } catch (err) { done(false); }
  }

  /* ---------- Actions for screens that aren't built yet: the control stays in place and says so ---------- */
  function notYet(what) { toast('Not available yet', what + ' arrives in the next update.'); }

  document.addEventListener('click', function (e) {
    var t = e.target;
    var copy = t.closest('[data-copy]');
    if (copy) { menus.forEach(function (m) { if (m.menu.contains(copy)) setMenu(m.btn, m.menu, false); }); copyId(copy); return; }
    var soon = t.closest('[data-soon]');
    if (soon && !t.closest('#cmd-list')) { menus.forEach(function (m) { if (m.menu.contains(soon)) setMenu(m.btn, m.menu, false); }); notYet(soon.getAttribute('data-soon')); return; }
    /* A row opens its ticket, except from the deadline chip, whose actions are its own */
    var row = t.closest('.lrow[data-href]');
    if (row && !t.closest('.dl') && !t.closest('a')) location.href = row.getAttribute('data-href');
  });

  /* Arriving on a page: the screen rises in, as the prototype's route change does */
  var screen = document.querySelector('.screen');
  if (screen && !reduceMotion.matches) screen.classList.add('entering');

  /* ================= Sheets (PR 2) =================
     A sheet slides up over the page it belongs to, with the scrim behind and the page inert; it leaves the same way.
     Each sheet has its own URL (data-url): opened from the page, it's pushed onto history, so Back closes it and the URL
     can be shared; opened by that URL, the server renders the page with the sheet already open. Esc, Cancel and the scrim
     close it; focus stays inside while it's open and goes back to what opened it. Pages put their sheets in #sheet-layer
     (console/templates/console/_sheets.html); a page without the sheet follows the link instead. Sheets announce
     'sheet:open' (detail.focus: a field to bring into view) for their own scripts (forms.js). */
  var layer = $('sheet-layer'), sheetCard = null, sheetOpener = null, sheetPushed = false;
  var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';
  function sheetFor(href) {
    if (!layer || !href) return null;
    var path = new URL(href, location.href).pathname;
    return layer.querySelector('.sheet-card[data-url="' + path.replace(/"/g, '') + '"]');
  }
  function focusables(card) { return [].filter.call(card.querySelectorAll(FOCUSABLE), function (el) { return el.offsetParent !== null || el === document.activeElement; }); }
  function sheetFocus(card, focus) {
    var wanted = focus && card.querySelector('[data-field="' + focus + '"]');
    var target = (wanted && wanted.querySelector('input:not([type="hidden"]), textarea, select'))
      || card.querySelector('.invalid, [aria-invalid="true"]')
      || card.querySelector('.sh-body input[type="radio"]:checked, .sh-body .input, .sh-body .textarea, .sh-body .select, .sh-body input[type="radio"], .dlg-actions .btn');
    if (target && target.classList.contains('chips-input')) target = target.querySelector('input');
    if (target) target.focus({ preventScroll: true });
    var into = wanted || (target && target.closest('.field'));
    if (into && (wanted || card.querySelector('.invalid'))) into.scrollIntoView({ block: 'center', behavior: reduceMotion.matches ? 'auto' : 'smooth' });
  }
  function openSheet(card, opts) {
    opts = opts || {};
    if (app.classList.contains('cmd-open')) closeCmd();
    [].forEach.call(layer.querySelectorAll('.sheet-card'), function (c) { c.hidden = c !== card; });
    sheetCard = card; sheetOpener = opts.opener || document.activeElement;
    clearTimeout(layer.t); layer.hidden = false; layer.classList.remove('entering');
    layer.offsetWidth; // start the transition from the closed state
    layer.classList.add('open'); app.inert = true;
    card.dispatchEvent(new CustomEvent('sheet:open', { bubbles: true, detail: { focus: opts.focus || '' } }));
    setTimeout(function () { if (sheetCard === card) sheetFocus(card, opts.focus); }, 80);
  }
  function closeSheet(fromHistory) {
    if (!sheetCard) return;
    var card = sheetCard; sheetCard = null;
    layer.classList.remove('open', 'entering'); app.inert = false;
    layer.t = setTimeout(function () { if (!sheetCard) { layer.hidden = true; card.dispatchEvent(new CustomEvent('sheet:closed', { bubbles: true })); } }, 260);
    var back = sheetOpener && document.contains(sheetOpener) && sheetOpener !== document.body ? sheetOpener
      : document.querySelector('#app [data-sheet-href^="' + card.getAttribute('data-url') + '"]');
    if (back && back.focus) back.focus({ preventScroll: true });
    if (fromHistory) return;
    if (sheetPushed) { sheetPushed = false; history.back(); }
    else history.replaceState(null, '', card.getAttribute('data-base') || location.pathname);
  }
  function openSheetHref(href, opener) {
    var card = sheetFor(href);
    if (!card) { location.href = href; return; }
    var url = new URL(href, location.href);
    if (!sheetCard) { history.pushState({ sheet: url.pathname + url.search }, '', url.pathname + url.search); sheetPushed = true; }
    openSheet(card, { opener: opener, focus: url.searchParams.get('focus') || '' });
  }
  if (layer) {
    /* Opened by its URL: the server rendered it open (rising in once, by CSS, on a fresh visit) */
    var already = layer.classList.contains('open') && layer.querySelector('.sheet-card:not([hidden])');
    if (already) {
      sheetCard = already; app.inert = true;
      history.replaceState({ sheet: location.pathname + location.search }, '', location.href);
      setTimeout(function () { sheetFocus(already, new URLSearchParams(location.search).get('focus')); }, layer.classList.contains('entering') ? 120 : 0);
    }
    layer.addEventListener('click', function (e) { if (e.target.closest('[data-close]')) { e.preventDefault(); closeSheet(); } });
    document.addEventListener('keydown', function (e) {
      if (!sheetCard) return;
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeSheet(); return; }
      if (e.key !== 'Tab') return;
      var f = focusables(sheetCard); if (!f.length) return;
      var first = f[0], last = f[f.length - 1], at = document.activeElement;
      if (!sheetCard.contains(at)) { e.preventDefault(); first.focus(); }
      else if (e.shiftKey && at === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && at === last) { e.preventDefault(); first.focus(); }
    }, true);
    window.addEventListener('popstate', function (e) {
      var want = e.state && e.state.sheet, card = want && sheetFor(want);
      if (card && card !== sheetCard) { sheetPushed = true; openSheet(card, { focus: new URL(want, location.href).searchParams.get('focus') || '' }); }
      else if (!card && sheetCard) { sheetPushed = false; closeSheet(true); }
    });
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-sheet-href]');
    if (!t || t.closest('#cmd-list') || e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    e.preventDefault(); openSheetHref(t.getAttribute('data-sheet-href'), t);
  });

  /* A toast the server left for this page (a change that just went through) */
  var flash = document.querySelector('[data-flash]');
  if (flash) {
    try { var f = JSON.parse(flash.getAttribute('data-flash')); setTimeout(function () { toast(f.title, f.body, true); }, reduceMotion.matches ? 0 : 280); } catch (err) { /* not a toast */ }
  }

  window.Ledger = { toast: toast, nowMs: nowMs, relStr: relStr, reduceMotion: reduceMotion, openSheetHref: openSheetHref, closeSheet: closeSheet };
})();
