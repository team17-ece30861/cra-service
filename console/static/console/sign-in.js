/* Sign-in (docs/design.md, "The mark and sign-in"). Without JavaScript the form shows both fields and posts normally.
   With it, the group starts at username and grows to reveal password; the arrow travels down with it. */
(function () {
  'use strict';
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  function $(id) { return document.getElementById(id); }
  var screen = $('signin'), form = $('si-form'), group = $('si-group'), user = $('si-user'), pass = $('si-pass'), go = $('si-go'), msg = $('si-msg');
  var failed = form.hasAttribute('data-error');

  function step() { return group.getAttribute('data-step'); }
  function setStep(n) {
    group.setAttribute('data-step', String(n)); pass.tabIndex = n === 2 ? 0 : -1;
    go.setAttribute('aria-label', n === 2 ? 'Sign In' : 'Continue'); update();
  }
  function update() { go.disabled = go.classList.contains('busy') || (step() === '2' ? !pass.value : !user.value.trim()); }
  function say(text) { msg.textContent = text || ''; msg.classList.toggle('show', !!text); group.classList.toggle('bad', !!text); }
  function shake() { group.classList.remove('shake'); void group.offsetWidth; group.classList.add('shake'); }

  user.addEventListener('input', function () { say(''); if (!user.value.trim() && step() === '2') setStep(1); update(); });
  pass.addEventListener('input', function () { say(''); update(); });
  group.addEventListener('animationend', function () { group.classList.remove('shake'); });
  form.addEventListener('submit', function (e) {
    if (go.disabled) { e.preventDefault(); return; }
    /* Username first; a password manager that filled both can go straight through */
    if (step() === '1' && !pass.value) { e.preventDefault(); setStep(2); setTimeout(function () { pass.focus({ preventScroll: true }); }, 120); return; }
    say(''); go.classList.add('busy'); user.readOnly = pass.readOnly = true; group.classList.add('si-busy-dim'); screen.classList.add('busy'); go.disabled = true;
  });

  if (failed) {
    /* The server said no: keep the username, open the password row, shake once, one line under the group */
    setStep(2); pass.value = '';
    var text = msg.textContent; say(text);
    if (!reduceMotion.matches) shake();
    pass.focus({ preventScroll: true });
  } else {
    setStep(user.value.trim() ? 2 : 1);
    setTimeout(function () { (step() === '2' ? pass : user).focus({ preventScroll: true }); }, 60);
  }

  /* ---------- The mark. Everything reads the one shape (#mk-shape) and the SVG viewBox. ---------- */
  var svg = document.querySelector('svg.si-mark'), vb = svg.viewBox.baseVal, SVGNS = 'http://www.w3.org/2000/svg';
  function rnd(n) { return Math.floor(Math.random() * n); }
  function markOn(name) { return screen.classList.contains('mark-' + name) && !document.hidden; }
  document.querySelector('#mk-clip-box use').setAttribute('transform', 'scale(' + (1 / vb.width) + ' ' + (1 / vb.height) + ') translate(' + (-vb.x) + ' ' + (-vb.y) + ')');

  /* The mark palette: each new line or dot pattern takes one at random, never the same as the one before */
  var COLORS = ['#0A84FF', '#409CFF', '#64D2FF', '#7D7AFF', '#5E5CE6'], lastColor = '';
  function color() { var c; do { c = COLORS[rnd(COLORS.length)]; } while (c === lastColor); lastColor = c; return c; }

  /* Lines: ledger rules; every 4 s a random rule lights and the last one goes back to gray */
  var lines = [];
  (function () {
    var g = document.querySelector('.mk-lines'), n = 0;
    for (var y = vb.y + 3; y < vb.y + vb.height; y += 4.4) {
      var r = document.createElementNS(SVGNS, 'rect');
      r.setAttribute('x', vb.x); r.setAttribute('y', y.toFixed(1)); r.setAttribute('width', vb.width); r.setAttribute('height', '0.42');
      r.style.setProperty('--i', n++); g.appendChild(r); lines.push(r);
    }
  })();
  var lineOn = -1;
  function lineStep() {
    if (!markOn('lines')) return;
    var usable = Math.floor(lines.length * 0.7), next;
    do { next = rnd(usable); } while (next === lineOn);
    if (lineOn >= 0) lines[lineOn].classList.remove('on');
    lines[next].style.setProperty('--mk-c', color()); lines[next].classList.add('on'); lineOn = next;
  }

  /* Blueprint: a dot grid around the mark; after the outline draws, a dot pattern lights every 3.8 s, held 3.4 s */
  var GRID = 5, grid = {}, gx0 = Math.floor((vb.x - 40) / GRID), gx1 = Math.ceil((vb.x + vb.width + 40) / GRID), gy0 = Math.floor((vb.y - 25) / GRID), gy1 = Math.ceil((vb.y + vb.height + 25) / GRID);
  (function () {
    var g = document.querySelector('.mk-grid');
    for (var i = gx0; i <= gx1; i++) for (var j = gy0; j <= gy1; j++) {
      var c = document.createElementNS(SVGNS, 'circle');
      c.setAttribute('cx', (i * GRID + 0.5)); c.setAttribute('cy', (j * GRID + 0.5)); c.setAttribute('r', '0.32');
      g.appendChild(c); grid[i + ',' + j] = c;
    }
    var t = document.querySelector('.mk-ticks'), x0 = vb.x, y0 = vb.y, x1 = vb.x + vb.width, y1 = vb.y + vb.height;
    t.setAttribute('d', ['M', x0 - 6, y0, 'H', x0 - 2, 'M', x0, y0 - 6, 'V', y0 - 2, 'M', x1 + 2, y0, 'H', x1 + 6, 'M', x1, y0 - 6, 'V', y0 - 2, 'M', x0 - 6, y1, 'H', x0 - 2, 'M', x0, y1 + 2, 'V', y1 + 6, 'M', x1 + 2, y1, 'H', x1 + 6, 'M', x1, y1 + 2, 'V', y1 + 6].join(' '));
  })();
  function dot(i, j) { return grid[i + ',' + j]; }
  function gridStep() {
    if (!markOn('blueprint')) return;
    var col = color(), ci = Math.floor(vb.x / GRID) + 1 + rnd(Math.floor(vb.width / GRID) - 6), cj = Math.floor(vb.y / GRID) + 1 + rnd(Math.floor(vb.height * 0.68 / GRID) - 3), kind = rnd(3), lit = [];
    if (kind === 0) { var horiz = Math.random() < 0.5; for (var k = 0; k < 6; k++) lit.push(horiz ? dot(ci + k, cj) : dot(ci, cj + k)); }
    else if (kind === 1) { lit = [dot(ci, cj), dot(ci + 1, cj), dot(ci, cj + 1), dot(ci + 1, cj + 1)]; }
    else {
      var base = dot(ci, cj), cx = +base.getAttribute('cx'), cy = +base.getAttribute('cy'), g = document.querySelector('.mk-grid'), parts = [];
      [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(function (o, n) {
        var c = document.createElementNS(SVGNS, 'circle'); c.setAttribute('cx', cx); c.setAttribute('cy', cy); c.setAttribute('class', 'split'); c.style.setProperty('--mk-c', col); c.style.transitionDelay = (n * 40) + 'ms'; g.appendChild(c); parts.push([c, o]);
      });
      base.style.opacity = '0';
      requestAnimationFrame(function () { requestAnimationFrame(function () { parts.forEach(function (p) { p[0].style.transform = 'translate(' + (p[1][0] * 1.3) + 'px,' + (p[1][1] * 1.3) + 'px)'; }); }); });
      setTimeout(function () { parts.forEach(function (p) { p[0].style.transform = 'none'; p[0].style.opacity = '0'; }); base.style.opacity = ''; }, 3400);
      setTimeout(function () { parts.forEach(function (p) { p[0].remove(); }); }, 4500);
      return;
    }
    lit = lit.filter(Boolean);
    lit.forEach(function (c, n) { setTimeout(function () { c.style.setProperty('--mk-c', col); c.classList.add('on'); }, n * 90); });
    setTimeout(function () { lit.forEach(function (c, n) { setTimeout(function () { c.classList.remove('on'); }, n * 90); }); }, 3400);
  }

  /* Window: each field steers toward random points near its own home at a steady speed, turning smoothly */
  var win = document.querySelector('.si-window'), winFx = win.querySelector('.si-window-fx'), winW = 0, winH = 0, winLast = performance.now();
  var FIELDS = [
    ['10, 132, 255', 97, 0.9], ['10, 132, 255', 82, 0.85], ['10, 132, 255', 72, 0.8], ['10, 132, 255', 67, 0.75],
    ['64, 156, 255', 87, 0.75], ['64, 156, 255', 72, 0.7], ['64, 156, 255', 62, 0.7],
    ['100, 210, 255', 67, 0.65], ['100, 210, 255', 57, 0.65], ['100, 210, 255', 52, 0.6],
    ['125, 122, 255', 82, 0.7], ['125, 122, 255', 62, 0.65],
    ['94, 92, 230', 77, 0.65], ['94, 92, 230', 57, 0.6],
    /* the bookmark's two tails: fixed homes and a short leash */
    ['125, 122, 255', 50, 0.7, [0.1, 0.92]], ['10, 132, 255', 45, 0.7, [0.25, 0.84]],
    ['100, 210, 255', 50, 0.65, [0.9, 0.92]], ['64, 156, 255', 45, 0.7, [0.75, 0.84]]
  ];
  var fields = FIELDS.map(function (d, n) {
    var el = document.createElement('i'); el.style.cssText = '--c:' + d[0] + ';--sz:' + d[1] + '%;--op:' + d[2]; winFx.appendChild(el);
    var f = { el: el, x: 0.08 + (n % 4) * 0.28 + (Math.floor(n / 4) % 2) * 0.12, y: 0.06 + Math.floor(n / 4) * 0.23, speed: 0.05 + Math.random() * 0.04, vx: 0, vy: 0 };
    var reach = d[3] ? 0.35 : 1; if (d[3]) { f.x = d[3][0]; f.y = d[3][1]; }
    f.hx = f.x; f.hy = f.y;
    f.pick = function () { f.tx = f.hx + (Math.random() - 0.5) * 0.5 * reach; f.ty = f.hy + (Math.random() - 0.5) * 0.36 * reach; }; f.pick(); return f;
  });
  new ResizeObserver(function () { winW = win.offsetWidth; winH = win.offsetHeight; winFx.style.setProperty('--win-blur', Math.round(winW * 0.09) + 'px'); }).observe(win);
  (function frame(now) {
    var dt = Math.min(0.05, (now - winLast) / 1000); winLast = now;
    if (markOn('window') && winW) fields.forEach(function (f) {
      if (!reduceMotion.matches) {
        var dx = f.tx - f.x, dy = (f.ty - f.y) * winH / winW, d = Math.hypot(dx, dy);
        if (d < 0.08) f.pick();
        var k = 1 - Math.exp(-0.9 * dt);
        f.vx += ((dx / (d || 1)) * f.speed - f.vx) * k; f.vy += ((dy / (d || 1)) * f.speed - f.vy) * k;
        f.x += f.vx * dt; f.y += f.vy * dt * winW / winH;
      }
      var sz = f.el.offsetWidth;
      f.el.style.transform = 'translate(' + (f.x * winW + 0.15 * winW - sz / 2).toFixed(1) + 'px,' + (f.y * winH + 0.15 * winH - sz / 2).toFixed(1) + 'px)';
    });
    requestAnimationFrame(frame);
  })(performance.now());

  /* Each load picks one of the three treatments at random */
  var marks = ['lines', 'blueprint', 'window'], pick = marks[rnd(marks.length)];
  screen.classList.add('mark-' + pick);
  if (!reduceMotion.matches) {
    setTimeout(lineStep, 1400); setInterval(lineStep, 4000);
    setTimeout(function () { gridStep(); setInterval(gridStep, 3800); }, 2300);
  }
})();
