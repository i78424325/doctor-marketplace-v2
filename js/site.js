/* Доктор Маркетплейс — общий скрипт всех страниц. Лёгкий: никаких обработчиков прокрутки и анимаций на каждый кадр —
   только IntersectionObserver и клики. Здесь же окно заявки (QR в Telegram/MAX или форма), чат и видео-визитка.
   Куда уходят заявки: атрибут data-endpoint у #dock (поле «Адрес приёма заявок» в админке). Пусто — демо-режим. */
(function () {
  'use strict';
  var d = document, w = window, root = d.documentElement;
  var qa = /[?&]qa=1/.test(location.search);
  if (qa) root.classList.add('qa');
  var $ = function (s, c) { return (c || d).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || d).querySelectorAll(s)); };
  var IO = 'IntersectionObserver' in w;
  var BASE = '/doctor-marketplace-v2/';
  var mem = {
    get: function (k) { try { return w.sessionStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { w.sessionStorage.setItem(k, v); } catch (e) { /* приватный режим */ } }
  };
  var mqDesk = w.matchMedia('(min-width:641px)');
  var desktop = function () { return mqDesk.matches; };
  var focus = function (el) { if (el && el.focus) try { el.focus({ preventScroll: true }); } catch (e) { el.focus(); } };

  /* появление блоков при прокрутке — один раз. То, что уже на экране, видно сразу,
     а прятать остальное (класс .ready) начинаем только когда скрипт точно запустился */
  try {
    var shown = $$('[data-reveal], .tagline, .steps');
    if (IO && !qa) {
      var vh = w.innerHeight || 800;
      shown.forEach(function (el) { if (el.getBoundingClientRect().top < vh) el.classList.add('in'); });
      root.classList.add('ready');
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
      }, { rootMargin: '0px 0px -10% 0px' });
      shown.forEach(function (el) { if (!el.classList.contains('in')) io.observe(el); });
    } else shown.forEach(function (el) { el.classList.add('in'); });
  } catch (err) { root.classList.remove('ready'); }

  /* иллюстрации первого экрана страниц услуг: проигрываем один раз сразу после загрузки */
  var plays = $$('[data-play]');
  if (plays.length) requestAnimationFrame(function () { requestAnimationFrame(function () { plays.forEach(function (el) { el.classList.add('in'); }); }); });

  /* всё живое (бегущая строка, блики, графики) работает только на экране: секция ушла — анимации на паузе */
  if (IO && !qa) {
    var live = new IntersectionObserver(function (es) {
      es.forEach(function (e) { e.target.classList.toggle('off', !e.isIntersecting); });
    }, { rootMargin: '120px 0px 120px 0px' });
    $$('main > section').forEach(function (el) { live.observe(el); });
  }

  /* шапка: тень после начала прокрутки — по «датчику» вверху страницы, без события scroll */
  var nav = $('.nav'), sensor = $('#top-sensor');
  if (nav && sensor && IO) new IntersectionObserver(function (e) { nav.classList.toggle('scrolled', !e[0].isIntersecting); }).observe(sensor);

  /* мобильное меню */
  var menuBtn = $('.menu-btn'), mmenu = $('#mmenu');
  var behindMenu = [$('#main'), $('.footer'), $('#dock'), $('.sticky-cta')].filter(Boolean);
  function setMenu(open) {
    if (!menuBtn) return;
    root.classList.toggle('menu-open', open);
    menuBtn.setAttribute('aria-expanded', String(open));
    menuBtn.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    d.body.style.overflow = open ? 'hidden' : '';
    if (mmenu) mmenu.inert = !open;
    behindMenu.forEach(function (el) { el.inert = open; });
    if (open && mmenu) { var first = $('a', mmenu); if (first) setTimeout(function () { focus(first); }, 60); }
  }
  if (menuBtn) {
    if (mmenu) mmenu.inert = true;
    menuBtn.addEventListener('click', function () { setMenu(!root.classList.contains('menu-open')); });
    $$('#mmenu a').forEach(function (a) { a.addEventListener('click', function () { setMenu(false); }); });
    var wide = w.matchMedia('(min-width:1024px)'), onWide = function (e) { if (e.matches) setMenu(false); };
    if (wide.addEventListener) wide.addEventListener('change', onWide); else if (wide.addListener) wide.addListener(onWide);
  }

  /* липкая кнопка на телефоне: появляется, когда первый экран ушёл вверх; кнопки связи поднимаются над ней */
  var sticky = $('.sticky-cta'), heroEl = $('.hero, .phero');
  if (sticky && heroEl && IO) new IntersectionObserver(function (e) {
    var on = !e[0].isIntersecting;
    sticky.classList.toggle('show', on);
    root.classList.toggle('sticky-on', on);
  }).observe(heroEl);

  /* заранее подгружаем страницу, на которую вот-вот перейдут (там, где нет speculationrules) */
  var spec = w.HTMLScriptElement && HTMLScriptElement.supports && HTMLScriptElement.supports('speculationrules');
  if (!spec) {
    var warmed = {};
    var warm = function (e) {
      var a = e.target.closest && e.target.closest('a[href]');
      if (!a || a.origin !== location.origin || a.target === '_blank' || a.hasAttribute('data-lead') || (a.hash && a.pathname === location.pathname)) return;
      var u = a.pathname + a.search;
      if (warmed[u]) return; warmed[u] = 1;
      var l = d.createElement('link'); l.rel = 'prefetch'; l.href = u; d.head.appendChild(l);
    };
    d.addEventListener('pointerover', warm, { passive: true });
    d.addEventListener('touchstart', warm, { passive: true });
  }

  /* голосовой ввод (voice.js подключён только там, где есть микрофон) */
  if (w.DMVoice) $$('[data-mic]').forEach(function (b) {
    var id = b.getAttribute('data-mic');
    w.DMVoice.attach(b, d.getElementById(id), d.getElementById(id + '-st'));
  });

  /* ---------- откуда пришёл человек: метка utm_source или сайт-источник (запоминаем на всю сессию) ---------- */
  var params = new URLSearchParams(location.search);
  (function () {
    var src = params.get('utm_source');
    if (!src && d.referrer) {
      try { var h = new URL(d.referrer).hostname.replace(/^www\./, ''); if (h && h !== location.hostname) src = h.split('.').slice(-2, -1)[0] || h; } catch (e) { /* нет источника */ }
    }
    if (src && !mem.get('dm-src')) mem.set('dm-src', src.toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 16));
    var camp = params.get('utm_campaign');
    if (camp && !mem.get('dm-camp')) mem.set('dm-camp', camp.slice(0, 60));
  })();
  var source = function () { return mem.get('dm-src') || 'direct'; };
  function pageCode() {
    var p = location.pathname;
    if (p.indexOf(BASE) === 0) p = p.slice(BASE.length);
    return (p.replace(/\/$/, '').replace(/[^a-z0-9-]+/gi, '-') || 'home').slice(0, 24);
  }
  /* метка для бота: услуга__источник__страница (в Telegram и MAX — параметр start, до 64 символов) */
  function payload(svc) { return [svc || 'na', source(), pageCode()].join('__').replace(/[^A-Za-z0-9_-]/g, '').slice(0, 64); }
  function serviceFromPage() {
    var m = location.pathname.match(/uslugi\/([a-z0-9-]+)/);
    return m ? m[1] : (params.get('usluga') || '').replace(/[^a-z0-9-]/g, '');
  }

  var dock = $('#dock');
  var cfg = {
    tg: dock ? dock.getAttribute('data-tg') : '',
    max: dock ? dock.getAttribute('data-max') : '',
    endpoint: dock ? dock.getAttribute('data-endpoint') : ''
  };
  var telA = $('.footer a[href^="tel:"]'), phone = telA ? telA.textContent.trim() : '';
  function botLink(ch, svc) {
    var base = cfg[ch];
    if (!base) return location.origin + BASE + 'kontakty/' + (svc ? '?usluga=' + svc : ''); // бот ещё не подключён — ведём на контакты
    try { var u = new URL(base); if (!u.searchParams.has('start')) u.searchParams.set('start', payload(svc)); return u.toString(); } catch (e) { return base; }
  }
  function goal(name) { try { if (w.ym && w.DM_YM) w.ym(w.DM_YM, 'reachGoal', name); } catch (e) { /* без аналитики */ } }

  /* отправка заявки: на «Адрес приёма заявок» (оттуда — в amoCRM и менеджеру); без адреса — демо */
  function send(data, cb) {
    if (!cfg.endpoint) { setTimeout(function () { cb(true); }, 700); return; }
    var fin = function (ok) { if (cb) { var f = cb; cb = null; f(ok); } };
    try {
      fetch(cfg.endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
        .then(function (r) { fin(r.ok); }, function () { fin(false); });
      setTimeout(function () { fin(false); }, 15000);
    } catch (e) { fin(false); }
  }
  if (cfg.endpoint) $$('[data-demo]').forEach(function (el) { el.hidden = true; });

  /* ---------- проверка полей ---------- */
  function setErr(input, msg) {
    var e = d.getElementById(input.id + '-err');
    input.setAttribute('aria-invalid', msg ? 'true' : 'false');
    if (e) e.textContent = msg || '';
  }
  function validName(i) { var v = i.value.trim(); setErr(i, v.length < 2 ? 'Напишите, как к вам обращаться.' : ''); return v.length >= 2; }
  /* телефон (10–15 цифр, любые разделители, без букв), ник Телеграма (с буквы, 5–32 символа), ссылка t.me или почта */
  function validContact(i) {
    var v = i.value.trim(), digits = v.replace(/\D/g, '').length;
    var ok = /^@?[a-zA-Z][a-zA-Z0-9_]{4,31}$/.test(v) || /t\.me\/[a-zA-Z][a-zA-Z0-9_]{4,}/.test(v) ||
      /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v) || (!/[a-zа-яё@]/i.test(v) && digits >= 10 && digits <= 15);
    setErr(i, ok ? '' : 'Укажите телефон, ник в Телеграме (например, @username) или почту.');
    return ok;
  }
  var markConsent = function (box) { if (box) box.closest('.check').classList.toggle('invalid', !box.checked); };

  /* ---------- окна: заявка и видео ---------- */
  var opened = null, lastFocus = null;
  var behind = function () { return [$('header'), $('#main'), $('.footer'), $('.sticky-cta'), dock, $('#chat')].filter(Boolean); };
  function openModal(m) {
    if (opened) closeModal(true);
    lastFocus = d.activeElement; opened = m; m.hidden = false;
    root.classList.add('modal-open');
    behind().forEach(function (el) { el.inert = true; });
    setTimeout(function () { focus($('.sheet, .vsheet', m) || m); }, 30);
  }
  function closeModal(silent) {
    if (!opened) return;
    var m = opened; opened = null; m.hidden = true;
    root.classList.remove('modal-open');
    behind().forEach(function (el) { el.inert = false; });
    if (m.id === 'vmodal') { var f = $('#vframe'); if (f) f.innerHTML = ''; }
    if (!silent) focus(lastFocus);
  }
  d.addEventListener('click', function (e) {
    var x = e.target.closest && e.target.closest('[data-close]');
    if (opened && x && opened.contains(x)) { e.preventDefault(); closeModal(); }
  });
  d.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      if (opened) closeModal();
      else if (chatOpen()) setChat(false);
      else if (root.classList.contains('menu-open')) { setMenu(false); focus(menuBtn); }
    }
    if (e.key === 'Tab' && opened) { // фокус не уходит из окна
      var f = $$('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])', opened).filter(function (el) { return !el.disabled && el.offsetParent !== null; });
      if (!f.length) return;
      if (e.shiftKey && (d.activeElement === f[0] || !opened.contains(d.activeElement))) { e.preventDefault(); focus(f[f.length - 1]); }
      else if (!e.shiftKey && d.activeElement === f[f.length - 1]) { e.preventDefault(); focus(f[0]); }
    }
  });

  /* заявка: вкладки Telegram / MAX / Телефон, две галочки, QR-код на компьютере, кнопка — на телефоне */
  var lead = $('#lead');
  var cur = { channel: 'tg', service: '' };
  var pd = $('#l-pd'), ads = $('#l-ads');
  var tabs = lead ? $$('[role="tab"]', lead) : [];
  var qrQueue = null;
  function loadQR(cb) {
    if (w.qrcode) return cb();
    if (qrQueue) return qrQueue.push(cb);
    qrQueue = [cb];
    var s = d.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/qrcode-generator/1.4.4/qrcode.min.js';
    s.async = true;
    s.onload = s.onerror = function () { var q = qrQueue; qrQueue = null; q.forEach(function (f) { f(); }); };
    d.head.appendChild(s);
  }
  function drawQR(box, url) {
    if (box.getAttribute('data-url') === url) return;
    box.setAttribute('data-url', url);
    loadQR(function () {
      if (!w.qrcode || box.getAttribute('data-url') !== url) return;
      try {
        var q = w.qrcode(0, 'M'); q.addData(url); q.make();
        var old = $('svg', box); if (old) old.parentNode.removeChild(old);
        box.insertAdjacentHTML('afterbegin', q.createSvgTag({ cellSize: 4, margin: 0, scalable: true }));
      } catch (e) { box.removeAttribute('data-url'); }
    });
  }
  function refreshLead() {
    if (!lead) return;
    var ok = !!(pd && pd.checked);
    ['tg', 'max'].forEach(function (ch) {
      var url = botLink(ch, cur.service);
      var go = $('[data-go="' + ch + '"]', lead);
      if (go) { go.href = url; go.setAttribute('aria-disabled', ok ? 'false' : 'true'); }
      var box = $('[data-qr="' + ch + '"]', lead);
      if (box) { box.classList.toggle('locked', !ok); if (cur.channel === ch && desktop()) drawQR(box, url); }
    });
    var demo = $('[data-demo]', lead);
    if (demo) demo.hidden = !!(cfg.tg && cfg.max) || cur.channel === 'form';
  }
  function selectTab(ch, withFocus) {
    tabs.forEach(function (t) {
      var on = t.getAttribute('data-tab') === ch;
      t.setAttribute('aria-selected', String(on)); t.tabIndex = on ? 0 : -1;
      if (on && withFocus) focus(t);
    });
    $$('[data-pane]', lead).forEach(function (p) { p.hidden = p.getAttribute('data-pane') !== ch; });
    cur.channel = ch; refreshLead();
  }
  if (lead) {
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { selectTab(t.getAttribute('data-tab')); });
      t.addEventListener('keydown', function (e) {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
        e.preventDefault();
        var n = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
        selectTab(n.getAttribute('data-tab'), true);
      });
    });
    if (pd) pd.addEventListener('change', function () { markConsent(pd); refreshLead(); });
    $$('[data-go]', lead).forEach(function (a) {
      a.addEventListener('click', function (e) {
        if (!pd || !pd.checked) { e.preventDefault(); markConsent(pd); focus(pd); return; }
        goal('lead_' + a.getAttribute('data-go'));
      });
    });
    mqDesk.addEventListener && mqDesk.addEventListener('change', refreshLead);
  }
  d.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('[data-lead]');
    if (!t || !lead || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button > 0) return;
    e.preventDefault();
    if (root.classList.contains('menu-open')) setMenu(false);
    cur.service = t.getAttribute('data-service') || serviceFromPage();
    var hidden = $('#l-service'); if (hidden) hidden.value = cur.service;
    var f = $('#lead-form'), done = f && f.parentNode.querySelector('.done');
    if (f && done && !done.hidden) { done.hidden = true; f.hidden = false; f.reset(); } // новая заявка — чистая форма
    selectTab(t.getAttribute('data-channel') || 'tg');
    openModal(lead);
    goal('lead_open');
  });

  /* формы заявки: на странице контактов и в окне */
  $$('[data-lead-form]').forEach(function (form) {
    var inModal = form.id === 'lead-form';
    var nameI = $('[name="name"]', form), contactI = $('[name="contact"]', form), svc = $('[name="service"]', form);
    var pdBox = inModal ? pd : $('[name="consent_pd"]', form), adsBox = inModal ? ads : $('[name="consent_ads"]', form);
    if (!inModal && svc && svc.tagName === 'SELECT') {
      var want = serviceFromPage();
      if (want) { var opt = $('option[value="' + want + '"]', svc); if (opt) svc.value = want; }
    }
    [nameI, contactI].forEach(function (i) {
      i.addEventListener('input', function () { if (i.getAttribute('aria-invalid') === 'true') (i === nameI ? validName : validContact)(i); });
    });
    if (pdBox && !inModal) pdBox.addEventListener('change', function () { markConsent(pdBox); });
    var val = function (n) { var el = $('[name="' + n + '"]', form); return el ? el.value.trim() : ''; };
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var a = validName(nameI), b = validContact(contactI), c = !!(pdBox && pdBox.checked);
      markConsent(pdBox);
      if (!a) { focus(nameI); return; }
      if (!b) { focus(contactI); return; }
      if (!c) { focus(pdBox); return; }
      var btn = $('button[type="submit"]', form), errP = $('.form-err', form);
      btn.classList.add('loading'); btn.setAttribute('aria-busy', 'true');
      if (errP) errP.textContent = '';
      send({
        type: 'lead', channel: 'form', name: val('name'), contact: val('contact'), store: val('store'),
        service: (svc && svc.value) || cur.service, comment: val('comment'), page: location.pathname,
        source: source(), campaign: mem.get('dm-camp') || '', consent_pd: true, consent_ads: !!(adsBox && adsBox.checked)
      }, function (ok) {
        btn.classList.remove('loading'); btn.removeAttribute('aria-busy');
        if (!ok) { if (errP) errP.textContent = 'Не получилось отправить заявку. Позвоните нам' + (phone ? ': ' + phone : '') + ' — или напишите в Telegram.'; return; }
        goal('lead_form');
        form.hidden = true;
        var box = form.parentNode.querySelector('.done');
        if (box) {
          if (cfg.endpoint) { var t = $('[data-done-text]', box); if (t) t.textContent = 'Спасибо! Менеджер свяжется с вами в ближайшее время.'; }
          box.hidden = false; focus(box);
          if (!inModal) box.scrollIntoView({ block: 'center', behavior: 'smooth' });
        }
      });
    });
  });

  /* ---------- чат «Напишите нам, мы онлайн» ---------- */
  var chat = $('#chat'), chatBtn = $('#chat-open'), log = $('#chat-log'), cform = $('#chat-form'), cin = $('#chat-in');
  var ccontact = $('#chat-contact'), quick = $('#chat-quick'), cn = $('#chat-cn'), tip = $('#dock-tip');
  var talk = { sent: [], step: 0, contact: '' };
  function chatOpen() { return !!(chat && !chat.hidden); }
  function hideTip() { if (tip) tip.classList.remove('show'); }
  function setChat(open) {
    if (!chat) return;
    chat.hidden = !open;
    root.classList.toggle('chat-on', open);
    chatBtn.setAttribute('aria-expanded', String(open));
    if (open) { hideTip(); if (desktop()) setTimeout(function () { focus(ccontact.hidden ? cin : cn); }, 60); goal('chat_open'); }
    else focus(chatBtn);
  }
  function addMsg(text, cls) {
    var m = d.createElement('div'); m.className = 'msg ' + cls; m.textContent = text;
    log.appendChild(m); log.scrollTop = log.scrollHeight; return m;
  }
  function botSay(text, delay) {
    var m = addMsg('', 'msg-in');
    m.innerHTML = '<span class="typing" aria-label="Печатает"><i></i><i></i><i></i></span>';
    setTimeout(function () { m.textContent = text; log.scrollTop = log.scrollHeight; }, delay || 900);
  }
  function userSend(text) {
    text = String(text || '').trim();
    if (!text) return;
    addMsg(text, 'msg-out'); cin.value = ''; quick.hidden = true;
    if (talk.step < 2) {
      talk.sent.push(text);
      if (talk.step === 0) {
        talk.step = 1;
        botSay('Спасибо! Оставьте телефон или ник в Телеграме — менеджер ответит, даже если вы закроете сайт.', 1000);
        setTimeout(function () { ccontact.hidden = false; cform.hidden = true; if (desktop()) focus(cn); log.scrollTop = log.scrollHeight; }, 1150);
      }
      return;
    }
    send({ type: 'chat', messages: [text], contact: talk.contact, page: location.pathname, source: source() }, function (ok) {
      addMsg(ok ? (cfg.endpoint ? 'Доставлено менеджеру' : 'Демо: в рабочей версии сообщение придёт менеджеру в Telegram') : 'Не доставлено. Напишите нам в Telegram или позвоните.', 'msg-sys');
    });
  }
  if (chat && chatBtn) {
    chatBtn.addEventListener('click', function () { setChat(!chatOpen()); });
    $$('[data-chat-close]', chat).forEach(function (b) { b.addEventListener('click', function () { setChat(false); }); });
    cform.addEventListener('submit', function (e) { e.preventDefault(); userSend(cin.value); });
    $$('[data-q]', quick).forEach(function (b) { b.addEventListener('click', function () { userSend(b.getAttribute('data-q')); }); });
    var cpd = $('#c-pd'), cads = $('#c-ads');
    if (cpd) cpd.addEventListener('change', function () { markConsent(cpd); });
    ccontact.addEventListener('submit', function (e) {
      e.preventDefault();
      var ok = validContact(cn);
      markConsent(cpd);
      if (!ok) { focus(cn); return; }
      if (!cpd.checked) { focus(cpd); return; }
      var btn = $('button[type="submit"]', ccontact); btn.classList.add('loading');
      send({ type: 'chat', messages: talk.sent, contact: cn.value.trim(), page: location.pathname, source: source(),
             campaign: mem.get('dm-camp') || '', consent_pd: true, consent_ads: !!(cads && cads.checked) }, function (sent) {
        btn.classList.remove('loading');
        if (!sent) { var er = $('#chat-cn-err'); if (er) er.textContent = 'Не получилось отправить. Попробуйте ещё раз или напишите нам в Telegram.'; return; }
        goal('lead_chat');
        talk.contact = cn.value.trim(); talk.step = 2;
        ccontact.hidden = true; cform.hidden = false;
        addMsg(talk.contact, 'msg-out');
        botSay(cfg.endpoint ? 'Готово! Передали менеджеру — он скоро напишет вам. Можно продолжать писать здесь.'
                            : 'Готово! В рабочей версии сообщение сразу придёт менеджеру в Telegram, и он вам ответит. Сейчас это демо.', 800);
      });
    });
    /* на телефоне один раз за визит подсказываем, что можно написать */
    if (tip && !mem.get('dm-tip') && !qa) setTimeout(function () {
      if (chatOpen() || opened) return;
      tip.classList.add('show'); mem.set('dm-tip', '1');
      setTimeout(hideTip, 5000);
    }, 6000);
  }

  /* ---------- видео-визитка ---------- */
  var vm = $('#vmodal'), vtpl = $('#video-tpl');
  $$('[data-video]').forEach(function (b) {
    b.addEventListener('click', function () {
      if (!vm || !vtpl) return;
      $('#vframe').innerHTML = vtpl.innerHTML;
      openModal(vm);
      var v = $('#vframe video');
      if (v && v.play) { var p = v.play(); if (p && p.catch) p.catch(function () { /* браузер ждёт нажатия */ }); }
      goal('video_play');
    });
  });
})();
