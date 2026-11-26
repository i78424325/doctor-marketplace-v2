/* Конструктор сайта «Доктор Маркетплейс»: правка страницы прямо на ней.
   Во фрейме — версия страницы для редактора (admin/edit/, собирается вместе с сайтом): поля помечены data-e,
   блоки — data-blk, списки — data-list / data-item, общие файлы (цифры, основатель, услуги…) — data-src.
   Правки копятся в черновике этого браузера; «Опубликовать» — одна правка в репозиторий (GitHub GraphQL createCommitOnBranch)
   со строкой журнала правок (journal.js). После неё сайт пересобирается сам, примерно за минуту. */
(() => {
  'use strict';
  const J = window.DMJournal || null;
  const BASE = location.pathname.replace(/admin\/[^/]*$/, '');
  const API = 'https://api.github.com';
  const PAGE = (new URLSearchParams(location.search).get('page') || 'home').replace(/[^a-z0-9-]/g, '') || 'home'; // какую страницу правим
  const DRAFT = 'dm-builder-draft:' + PAGE; // у каждой страницы свой черновик
  const EDIT = BASE + 'admin/edit/' + PAGE + '/';
  const $ = (s, c) => (c || document).querySelector(s);
  const $$ = (s, c) => Array.from((c || document).querySelectorAll(s));
  const LS = {
    get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } },
    del: k => { try { localStorage.removeItem(k); } catch (e) { /* приватный режим */ } }
  };
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const clone = o => (o === undefined ? undefined : JSON.parse(JSON.stringify(o)));
  const clean = s => String(s == null ? '' : s).replace(/ /g, ' ').replace(/[\r\n\t]+/g, ' ').replace(/ {2,}/g, ' ').trim();
  const decoder = document.createElement('textarea');
  const decode = s => { decoder.innerHTML = String(s); return decoder.value; }; // «6&nbsp;000+» в файле → «6 000+» на экране, как у сборщика
  const b64 = text => {
    const b = new TextEncoder().encode(text);
    let s = '';
    for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
    return btoa(s);
  };
  const PLAIN = (() => { // «только текст»: при вставке и наборе не появляется жирный, ссылки и чужие стили
    const t = document.createElement('div');
    try { t.contentEditable = 'plaintext-only'; } catch (e) { return 'true'; }
    return t.contentEditable === 'plaintext-only' ? 'plaintext-only' : 'true';
  })();
  const RU = (() => {
    const a = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя', b = 'a b v g d e e zh z i i k l m n o p r s t u f h ts ch sh sch - y - e yu ya'.split(' '), m = {};
    for (let i = 0; i < a.length; i++) m[a[i]] = b[i] === '-' ? '' : b[i];
    return m;
  })();
  const slug = s => String(s || '').toLowerCase().split('').map(c => (RU[c] !== undefined ? RU[c] : c)).join('')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'foto';

  const I = {
    up: '<path d="M12 19V5M5.5 11.5 12 5l6.5 6.5"/>',
    down: '<path d="M12 5v14M5.5 12.5 12 19l6.5-6.5"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2.5"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
    eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/>',
    eyeOff: '<path d="M3 3l18 18M10.6 5.6A9.6 9.6 0 0 1 12 5.5C18 5.5 21.5 12 21.5 12a17 17 0 0 1-3.2 4.1M6.6 6.6A17 17 0 0 0 2.5 12S6 18.5 12 18.5a9 9 0 0 0 4.4-1.1"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
    gear: '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
    trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>'
  };
  const svg = (n, s) => '<svg viewBox="0 0 24 24" width="' + (s || 18) + '" height="' + (s || 18) + '" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + I[n] + '</svg>';

  /* как поле с разметкой выглядит на сайте — так же, как в сборщике build.py (hero_title, accent, tagline_words) */
  const FMT = {
    hero: raw => esc(raw).replace(/(^|\s)(\S{1,2}) (?=\[)/g, (m, a, b) => a + b + '&nbsp;')
      .replace(/\[WB\]/g, '<span class="mk mk-wb">Wildberries</span>').replace(/\[OZON\]/g, '<span class="mk mk-ozon">Ozon</span>')
      .replace(/\[([^\]]+)\]/g, '<span class="lead-word">$1</span>'),
    accent: raw => esc(raw).replace(/\*([^*]+)\*/g, '<em>$1</em>'),
    tagline: raw => {
      const out = [];
      let i = 0;
      String(raw).split(/(\*[^*]+\*)/).forEach(seg => {
        const acc = seg.charAt(0) === '*';
        seg.replace(/^\*+|\*+$/g, '').split(/\s+/).filter(Boolean).forEach(w => {
          out.push('<span class="w' + (acc ? ' acc' : '') + '" style="--i:' + (i++) + '">' + esc(w) + '</span>');
        });
      });
      return out.join(' ');
    }
  };
  const TIPS = {
    hero: '[WB] — Wildberries, [OZON] — Ozon, [слова] — зелёным. Enter — готово, Esc — отменить',
    accent: '*слова* в звёздочках — цветом. Enter — готово, Esc — отменить',
    tagline: '*слова* в звёздочках — цветом. Enter — готово, Esc — отменить'
  };
  const HELP = {
    _: 'Нажмите на текст в блоке и пишите. Наведите на блок — появятся кнопки.',
    hero: 'Заголовок: [WB] — Wildberries, [OZON] — Ozon, [слова] — зелёным. Цифры под кнопкой — те же, что в блоке «Цифры». Видео-визитка — в «Разделах»: «Видео-визитка».',
    clients: 'Логотипы клиентов добавляются в «Разделах»: «Наши клиенты — логотипы». Здесь — заголовок строки.',
    who: 'Наведите на карточку или пункт списка — появятся кнопки: выше, ниже, копия, удалить. *Слова в звёздочках* в заголовке карточки — цветом.',
    services: 'Названия и подписи плиток правятся здесь. Цены, кейсы, порядок и новые услуги — в «Разделах»: «Услуги, цены и кейсы».',
    stats: 'Цифры правятся на месте. Добавить или убрать цифру — в «Разделах»: «Цифры».',
    tagline: '*Слова в звёздочках* выделяются цветом.',
    founder: 'Фото — нажмите на него. Пункты списка: наведите — появятся кнопки. Основатель один на весь сайт: правка видна и на странице «О компании».',
    news: 'Список последних новостей и статей. Сколько показывать — выше, от 3 до 6. Новую новость или статью добавляют в «Разделах»: «Новости и статьи».',
    'cases-feed': 'Последние кейсы с графиками продаж. Сколько показывать — выше: 3, 6 или 9. Сами кейсы добавляют в «Разделах»: «Кейсы». Пока кейсов нет, на сайте этого блока не видно.',
    'cases-list': 'Все кейсы с фильтром по площадкам и услугам. Новый кейс — в «Разделах»: «Кейсы» → «Создать».',
    cases: 'Кейсы этой услуги: из раздела «Кейсы» (где отмечена услуга) и простые — из «Услуги, цены и кейсы».',
    steps: 'Шаги правятся на месте. Добавить шаг — в «Разделах»: «Шаги „Как мы работаем“».',
    faq: 'Вопросы и ответы — в «Разделах»: «Вопросы и ответы». Здесь — заголовок блока.',
    cta: 'Кнопка открывает окно записи на консультацию.'
  };
  const BGS = [['', 'Как в дизайне'], ['page', 'Светлый'], ['alt', 'Серый'], ['white', 'Белый'], ['mint', 'Мятный'], ['sand', 'Песочный']];
  const SWATCH = { page: '#F4F3EF', alt: '#ECEBE5', white: '#FFFFFF', mint: '#E7F2EB', sand: '#F5EFE3' };

  const S = {
    data: null, doc: null, src: {}, sha: {}, rev: 'local', dirty: new Set(), kinds: new Set(), uploads: {},
    sel: null, hover: null, hoverItem: null, editing: null, editStart: undefined, editHTML: '', editDirty: null, editKinds: null,
    undo: [], redo: [], fw: null, fd: null, busy: false, watch: 0, note: '', noteCls: '', panelMode: null, libAfter: null, pickFor: null,
    raf: 0, dt: 0, tt: 0, tbFor: null, itFor: null
  };
  const ui = {};

  /* ---------- запуск ---------- */
  async function boot() {
    bindShell();
    try {
      const r = await fetch(EDIT + 'data.json?nc=' + Date.now(), { cache: 'no-store' });
      if (r.status === 404 && PAGE !== 'home') { location.replace('konstruktor.html'); return; } // такой страницы в конструкторе нет — на главную
      if (!r.ok) throw new Error('HTTP ' + r.status);
      S.data = await r.json();
    } catch (e) {
      ui.panel.innerHTML = '<p class="pwarn">Не получилось загрузить конструктор. Проверьте интернет и обновите страницу.</p>';
      setNote('Ошибка загрузки', 'warn');
      return;
    }
    ui.page.innerHTML = (S.data.pages || [S.data.page]).map(p => '<option value="' + esc(p.key) + '"' + (p.key === PAGE ? ' selected' : '') + '>' + esc(p.title) + '</option>').join('');
    S.rev = S.data.rev || 'local';
    S.doc = clone(S.data.doc);
    S.sha[S.data.page.file] = S.data.page.sha || null;
    NICE[S.data.page.file] = 'страница «' + (S.data.page.title || PAGE) + '»';
    Object.keys(S.data.sources || {}).forEach(n => {
      const s = S.data.sources[n];
      S.src[n] = { file: s.file, doc: clone(s.doc) || {} };
      S.sha[s.file] = s.sha || null;
    });
    document.title = 'Конструктор: ' + (S.data.page.title || 'Главная') + ' — Доктор Маркетплейс';
    ui.frame.addEventListener('load', initFrame, { once: true });
    ui.frame.src = EDIT + '?edit=1&r=' + encodeURIComponent(String(S.rev).slice(0, 12)) + '&t=' + Date.now();
    authCheck();
    updateStatus();
  }

  function bindShell() {
    ui.frame = $('#k-frame'); ui.stage = $('#k-stage'); ui.panel = $('#k-panel'); ui.status = $('#k-status'); ui.pub = $('#k-pub');
    ui.undo = $('#k-undo'); ui.redo = $('#k-redo'); ui.toast = $('#k-toast'); ui.modal = $('#k-modal'); ui.login = $('#k-login');
    ui.page = $('#k-page'); ui.close = $('#k-close');
    ui.pub.addEventListener('click', publish);
    ui.page.addEventListener('change', () => leave('konstruktor.html' + (ui.page.value === 'home' ? '' : '?page=' + encodeURIComponent(ui.page.value)), 'page'));
    ui.close.addEventListener('click', () => leave('./', 'close'));
    ui.undo.addEventListener('click', undo);
    ui.redo.addEventListener('click', redo);
    ui.canvas = $('.kcanvas');
    $$('[data-dev]').forEach(b => b.addEventListener('click', () => {
      ui.stage.dataset.dev = b.dataset.dev;
      $$('[data-dev]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
      fitStage();
    }));
    if (window.ResizeObserver) new ResizeObserver(fitStage).observe(ui.canvas); else window.addEventListener('resize', fitStage);
    fitStage();
    document.addEventListener('keydown', e => {
      const t = e.target;
      if (t && t.closest && t.closest('input, textarea')) return;
      onShortcut(e);
    });
    window.addEventListener('beforeunload', e => {
      if (!S.dirty.size) return;
      saveDraftNow();
      if (S.leaving) return; // уходим сами (другая страница, «Закрыть») — черновик уже сохранён, лишний вопрос браузера не нужен
      e.preventDefault();
      e.returnValue = '';
    });
    window.addEventListener('storage', e => { if (e.key === 'sveltia-cms.user') authCheck(); });
    bindPanel();
  }

  /* уйти из конструктора: на другую страницу сайта или «Закрыть». Неопубликованные правки — сначала вопрос */
  function leave(url, why) {
    const close = why === 'close';
    ui.page.value = PAGE; // пока решаем — в списке остаётся текущая страница
    const go = () => {
      S.leaving = true;
      saveDraftNow();
      if (close) { // вкладку открыли кнопкой из админки — закрываем её; если браузер не дал — переходим в админку
        try { window.close(); } catch (e) { /* не закрывается */ }
        setTimeout(() => { location.href = url; }, 300);
      } else location.href = url;
    };
    if (S.editing) S.editing.blur();
    if (!S.dirty.size) { go(); return; }
    modal('<h2>Есть неопубликованные правки</h2><p>' + (close ? 'Если закрыть сейчас' : 'Если перейти на другую страницу') +
      ', правки останутся черновиком в этом браузере: конструктор предложит вернуть их, когда вы снова откроете эту страницу.</p>',
      [['Опубликовать и ' + (close ? 'закрыть' : 'перейти'), async () => { if (await publish()) go(); }, 'primary'],
       [close ? 'Закрыть, оставить черновик' : 'Перейти, оставить черновик', go], ['Отмена']]);
  }

  /* «Компьютер» — всегда настоящая ширина сайта (1280 px), планшет — 820, телефон — 390. Не влезает в окно — страница уменьшается целиком */
  const DEV_W = { desktop: 1280, tablet: 820, phone: 390 };
  function fitStage() {
    const dev = ui.stage.dataset.dev || 'desktop', want = DEV_W[dev] || 1280;
    const cw = ui.canvas.clientWidth - 32, ch = ui.canvas.clientHeight - 32;
    if (cw <= 0 || ch <= 0) return;
    if (dev === 'desktop' && cw >= want) {
      ui.stage.style.width = '100%'; ui.stage.style.height = '100%';
      ui.frame.style.width = '100%'; ui.frame.style.height = '100%'; ui.frame.style.transform = '';
    } else {
      const k = Math.min(1, cw / want);
      ui.stage.style.width = Math.floor(want * k) + 'px'; ui.stage.style.height = ch + 'px';
      ui.frame.style.width = want + 'px'; ui.frame.style.height = Math.ceil(ch / k) + 'px';
      ui.frame.style.transform = k < 1 ? 'scale(' + k + ')' : '';
    }
    schedule();
  }

  function initFrame() {
    let d = null;
    try { d = ui.frame.contentDocument; } catch (e) { d = null; }
    if (!d || !$('main [data-blk]', d)) {
      ui.panel.innerHTML = '<p class="pwarn">Страница для правки не открылась. Обновите страницу.</p>';
      return;
    }
    S.fw = ui.frame.contentWindow;
    S.fd = d;
    const mrev = $('meta[name="dm-rev"]', d); // страница и данные должны быть из одной выкладки сайта
    if (mrev && mrev.content !== S.rev) {
      let last = 0;
      try { last = +sessionStorage.getItem('dm-k-reload') || 0; } catch (e) { /* без памяти вкладки */ }
      if (Date.now() - last > 60000) {
        try { sessionStorage.setItem('dm-k-reload', String(Date.now())); } catch (e) { /* без памяти вкладки */ }
        location.reload();
        return;
      }
      setNote('Сайт сейчас обновляется — через минуту обновите эту страницу', 'warn');
    }
    d.documentElement.classList.add('dm-edit');
    const css = d.createElement('link');
    css.rel = 'stylesheet';
    css.href = BASE + 'admin/konstruktor-frame.css?v=' + encodeURIComponent(S.data.ver || '');
    d.head.appendChild(css);
    overlay(d);
    prepare(d);
    d.addEventListener('click', onClick, true);
    d.addEventListener('auxclick', stopAll, true);
    d.addEventListener('submit', stopAll, true);
    d.addEventListener('focusin', onFocusIn);
    d.addEventListener('focusout', onFocusOut);
    d.addEventListener('input', onInput);
    d.addEventListener('keydown', onKey, true);
    d.addEventListener('paste', onPaste, true);
    d.addEventListener('drop', e => e.preventDefault(), true);
    d.addEventListener('dragstart', e => { const t = e.target; if (!(t && t.closest && t.closest('[contenteditable]'))) e.preventDefault(); }, true);
    d.addEventListener('mousemove', onMove, { passive: true });
    d.documentElement.addEventListener('mouseleave', () => { setHover(null); setItem(null); schedule(); });
    S.fw.addEventListener('scroll', schedule, { passive: true });
    S.fw.addEventListener('resize', schedule);
    pushUndo(true);
    renderPanel();
    updateStatus();
    restoreDraftOffer();
  }
  const stopAll = e => { e.preventDefault(); e.stopPropagation(); };

  /* ---------- кнопки на самой странице ---------- */
  const tbtn = (icon, title, act) => '<button type="button" data-act="' + act + '" title="' + title + '" aria-label="' + title + '">' + svg(icon) + '</button>';
  function overlay(d) {
    const ov = d.createElement('div');
    ov.id = 'dm-ov';
    ov.innerHTML =
      '<div id="dm-bt" role="toolbar" aria-label="Блок"><span class="dm-name"></span>' +
      tbtn('up', 'Выше', 'up') + tbtn('down', 'Ниже', 'down') + tbtn('copy', 'Копия блока', 'copy') +
      tbtn('eye', 'Скрыть на сайте', 'hide') + tbtn('gear', 'Настройки блока', 'set') + tbtn('trash', 'Удалить блок', 'del') + '</div>' +
      '<div id="dm-it" role="toolbar" aria-label="Пункт списка">' + tbtn('up', 'Выше', 'iup') + tbtn('down', 'Ниже', 'idown') +
      tbtn('copy', 'Добавить такой же', 'icopy') + tbtn('x', 'Удалить пункт', 'idel') + '</div>' +
      '<button type="button" id="dm-add">' + svg('plus', 16) + '<span>Добавить блок</span></button>' +
      '<div id="dm-tip" role="note"></div><input type="file" id="dm-file" accept="image/*" hidden>';
    d.body.appendChild(ov);
    ov.addEventListener('click', onOverlay);
    $('#dm-file', d).addEventListener('change', onFile);
  }
  function prepare(root) {
    const pick = sel => (root.matches && root.matches(sel) ? [root] : []).concat($$(sel, root));
    pick('[data-e]').forEach(el => {
      if (el.hasAttribute('data-img')) { el.setAttribute('title', 'Нажмите, чтобы заменить фото'); el.setAttribute('draggable', 'false'); return; }
      el.setAttribute('contenteditable', PLAIN);
      el.setAttribute('spellcheck', 'true');
      el.setAttribute('data-ph', 'Нажмите и пишите');
    });
    pick('[data-reveal], .tagline, .steps, [data-play]').forEach(el => el.classList.add('in'));
  }

  /* ---------- где лежит поле: блок страницы или общий файл ---------- */
  function itemIndex(n) {
    if (n.hasAttribute('data-i')) return +n.getAttribute('data-i');
    let i = 0;
    for (let s = n.previousElementSibling; s; s = s.previousElementSibling) if (s.hasAttribute('data-item')) i++;
    return i;
  }
  function locate(el, field) {
    const path = [];
    for (let n = el, first = true; n && n.nodeType === 1; n = n.parentElement, first = false) {
      if (first && field !== false && n.hasAttribute('data-e') && n.getAttribute('data-e') !== '.') path.unshift(n.getAttribute('data-e'));
      if (n.hasAttribute('data-item')) path.unshift(itemIndex(n));
      if (n.hasAttribute('data-list')) path.unshift(n.getAttribute('data-list'));
      if (n.hasAttribute('data-src')) return { src: n.getAttribute('data-src'), path };
      if (n.hasAttribute('data-blk')) return { blk: n.getAttribute('data-blk'), path: ['data'].concat(path) };
    }
    return null;
  }
  const model = id => S.doc.blocks.find(b => b.id === id);
  const idx = id => S.doc.blocks.findIndex(b => b.id === id);
  const rootOf = loc => (loc.src ? (S.src[loc.src] && S.src[loc.src].doc) : model(loc.blk));
  const scopeOf = loc => (loc.src ? 'src:' + loc.src : 'page');
  const keyOf = loc => (loc ? (loc.src ? 'src:' + loc.src : 'blk:' + loc.blk) + '|' + loc.path.join('/') : '');
  function getAt(loc) {
    if (!loc) return undefined;
    let o = rootOf(loc);
    for (const k of loc.path) { if (o == null) return undefined; o = o[k]; }
    return o;
  }
  function setAt(loc, v) {
    let o = loc && rootOf(loc);
    if (!o) return false;
    const p = loc.path;
    for (let i = 0; i < p.length - 1; i++) {
      if (o[p[i]] == null || typeof o[p[i]] !== 'object') o[p[i]] = typeof p[i + 1] === 'number' ? [] : {};
      o = o[p[i]];
    }
    o[p[p.length - 1]] = v;
    touch(scopeOf(loc));
    return true;
  }
  function touch(scope, kind) {
    S.dirty.add(scope);
    if (kind) S.kinds.add(kind);
    saveDraft();
    updateStatus();
  }

  /* ---------- текст на месте ---------- */
  const fieldOf = t => (t && t.closest ? t.closest('[data-e]:not([data-img])') : null);
  function show(el, v) {
    if (el.hasAttribute('data-img')) { el.src = imgSrc(v); return; }
    const val = v == null || v === '' ? (el.getAttribute('data-fb') || '') : String(v); // пустое поле — как на сайте, текст по умолчанию
    const f = el.getAttribute('data-fmt');
    if (f && FMT[f]) el.innerHTML = FMT[f](val);
    else el.textContent = decode(val);
  }
  const REQUIRED = { services: /^services\/\d+\/title$/, stats: /^items\/\d+\/value$/ }; // без них сборщик убирает услугу или цифру с сайта
  const required = loc => !!(loc && loc.src && REQUIRED[loc.src] && REQUIRED[loc.src].test(loc.path.join('/')));
  function caretEnd(el) {
    const sel = S.fw && S.fw.getSelection();
    if (!sel) return;
    const r = S.fd.createRange();
    r.selectNodeContents(el);
    r.collapse(false);
    sel.removeAllRanges();
    sel.addRange(r);
  }
  function twins(el, loc, v) { // то же поле в другом месте страницы (цифры в первом экране и в блоке «Цифры», фото основателя)
    const k = keyOf(loc);
    $$('[data-e]', S.fd).forEach(o => { if (o !== el && keyOf(locate(o)) === k) show(o, v); });
  }
  /* место поля в данных ищется заново при каждом нажатии: пункты могли переставить или удалить, пока курсор стоял в поле */
  function onFocusIn(e) {
    const el = fieldOf(e.target);
    if (!el) return;
    S.editing = el;
    S.editStart = clone(getAt(locate(el)));
    S.editHTML = el.innerHTML;
    S.editDirty = new Set(S.dirty);
    S.editKinds = new Set(S.kinds);
    if (el.hasAttribute('data-fmt')) { // разметка видна, пока пишешь; курсор — в конец
      el.textContent = S.editStart == null ? '' : String(S.editStart);
      setTimeout(() => { if (S.editing === el) caretEnd(el); }, 0);
    }
    select(el.closest('[data-blk]'));
    tip(el);
  }
  function onInput(e) {
    const el = fieldOf(e.target);
    if (!el || el !== S.editing) return;
    const loc = locate(el);
    if (!loc) return;
    const v = clean(el.textContent);
    setAt(loc, v);
    S.kinds.add('тексты');
    twins(el, loc, v);
  }
  function onFocusOut(e) {
    const el = fieldOf(e.target);
    if (!el || el !== S.editing) return;
    S.editing = null;
    tip(null);
    const loc = locate(el);
    let v = getAt(loc);
    if (required(loc) && !clean(v)) {
      setAt(loc, clone(S.editStart));
      v = S.editStart;
      twins(el, loc, v);
      toast('Это поле не может быть пустым — без него пункт пропадёт с сайта. Вернул прежний текст', { err: true });
    }
    if (JSON.stringify(v) === JSON.stringify(S.editStart)) { // ничего не поменяли — всё как было, без лишней правки
      el.innerHTML = S.editHTML;
      S.dirty = S.editDirty;
      S.kinds = S.editKinds;
      saveDraft();
      updateStatus();
      return;
    }
    show(el, v);
    pushUndo();
  }
  function onKey(e) {
    const el = fieldOf(e.target);
    if (el) {
      if (e.key === 'Enter') { e.preventDefault(); el.blur(); return; }
      if (e.key === 'Escape') {
        e.preventDefault();
        const loc = locate(el);
        if (loc && JSON.stringify(getAt(loc)) !== JSON.stringify(S.editStart)) { setAt(loc, clone(S.editStart)); twins(el, loc, S.editStart); }
        el.blur();
        return;
      }
      if ((e.metaKey || e.ctrlKey) && /^[biu]$/i.test(e.key)) e.preventDefault(); // жирный и курсив здесь не нужны
      return;
    }
    if (e.key === 'Escape' && S.sel) { select(null); return; }
    onShortcut(e);
  }
  function onPaste(e) {
    const el = fieldOf(e.target);
    if (!el) return;
    e.preventDefault();
    const t = clean((e.clipboardData && e.clipboardData.getData('text/plain')) || '');
    if (t) S.fd.execCommand('insertText', false, t);
  }
  function onClick(e) {
    const t = e.target;
    if (!t || !t.closest || t.closest('#dm-ov')) return;
    e.stopPropagation(); // скрипты сайта (окно заявки, видео) в конструкторе не срабатывают
    const img = t.closest('[data-img]');
    if (img) { e.preventDefault(); select(img.closest('[data-blk]')); pickImage(img); return; }
    if (t.closest('a, button, label')) e.preventDefault(); // ссылки не уводят со страницы
    select(t.closest('[data-blk]'));
  }
  function tip(el) {
    const box = S.fd && $('#dm-tip', S.fd);
    if (!box) return;
    const text = el && TIPS[el.getAttribute('data-fmt')];
    if (!text) { box.style.display = 'none'; return; }
    const r = el.getBoundingClientRect();
    box.textContent = text;
    box.style.display = 'block';
    box.style.top = Math.max(r.top - 34, 4) + 'px';
    box.style.left = Math.max(Math.min(r.left, S.fd.documentElement.clientWidth - box.offsetWidth - 8), 8) + 'px';
  }

  /* ---------- наведение: рамка блока и кнопки ---------- */
  const editableList = l => !!(l && l.hasAttribute('data-list') && !l.hasAttribute('data-fixed'));
  function onMove(e) { // кнопки перерисовываются, только когда мышь перешла на другой блок или пункт
    const t = e.target;
    if (!t || !t.closest || t.closest('#dm-ov')) return; // над кнопками — оставляем, как было
    const b = t.closest('[data-blk]'), i0 = t.closest('[data-item]'), i = i0 && editableList(i0.parentElement) ? i0 : null;
    if (b === S.hover && i === S.hoverItem) return;
    setHover(b);
    setItem(i);
    place();
  }
  function setHover(b) {
    if (S.hover === b) return;
    if (S.hover) S.hover.classList.remove('dm-hover');
    S.hover = b;
    if (b) b.classList.add('dm-hover');
  }
  function setItem(i) {
    if (S.hoverItem === i) return;
    if (S.hoverItem) S.hoverItem.classList.remove('dm-ihover');
    S.hoverItem = i;
    if (i) i.classList.add('dm-ihover');
  }
  function schedule() {
    if (!S.fw) return;
    if (S.fd.hidden) { place(); return; }
    if (S.raf) return;
    S.raf = S.fw.requestAnimationFrame(() => { S.raf = 0; place(); });
  }
  function blockName(el) {
    const m = el && model(el.getAttribute('data-blk'));
    const t = m && S.data.types[m.type];
    return t ? t.name : 'Блок';
  }
  function place() {
    const d = S.fd;
    if (!d) return;
    const bt = $('#dm-bt', d), add = $('#dm-add', d), it = $('#dm-it', d);
    const vh = S.fw.innerHeight, vw = d.documentElement.clientWidth;
    const b = S.hover && S.hover.isConnected ? S.hover : (S.sel && S.sel.isConnected ? S.sel : null);
    bt.style.display = 'none';
    add.style.display = 'none';
    S.tbFor = null;
    if (b) {
      const r = b.getBoundingClientRect();
      if (r.bottom > 48 && r.top < vh - 48) {
        const m = model(b.getAttribute('data-blk'));
        const off = !!(m && m.hidden);
        S.tbFor = b; // кнопки действуют на тот блок, у которого нарисованы
        bt.style.display = 'flex';
        $('.dm-name', bt).textContent = blockName(b);
        if (bt.dataset.off !== String(off)) {
          bt.dataset.off = String(off);
          bt.classList.toggle('is-off', off);
          const h = $('[data-act="hide"]', bt);
          h.innerHTML = svg(off ? 'eyeOff' : 'eye');
          h.title = off ? 'Показать на сайте' : 'Скрыть на сайте';
          h.setAttribute('aria-label', h.title);
        }
        bt.style.top = Math.max(Math.min(r.top + 8, r.bottom - bt.offsetHeight - 8), 8) + 'px';
        bt.style.right = Math.max(vw - r.right + 8, 8) + 'px';
        if (r.bottom < vh - 8 && r.bottom > 24) {
          add.style.display = 'flex';
          add.style.top = (r.bottom - 18) + 'px';
          add.style.left = (Math.max(r.left, 0) + Math.min(r.right, vw)) / 2 + 'px';
        }
      }
    }
    const i = S.hoverItem && S.hoverItem.isConnected ? S.hoverItem : null;
    S.itFor = i;
    if (i) {
      const r = i.getBoundingClientRect();
      it.style.display = 'flex';
      it.style.top = Math.max(r.top - 14, 4) + 'px';
      it.style.left = Math.max(Math.min(r.right - it.offsetWidth, vw - it.offsetWidth - 4), 4) + 'px';
    } else it.style.display = 'none';
    if (S.editing) tip(S.editing);
  }
  function onOverlay(e) {
    const btn = e.target.closest('button');
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    if (S.editing) S.editing.blur(); // сначала закончить правку текста, потом менять блоки и пункты
    const blk = S.tbFor && S.tbFor.isConnected ? S.tbFor : (S.hover && S.hover.isConnected ? S.hover : S.sel);
    if (btn.id === 'dm-add') { openLibrary(blk); return; }
    const act = btn.getAttribute('data-act');
    if (act && act.charAt(0) === 'i') { itemOp(act.slice(1), S.itFor && S.itFor.isConnected ? S.itFor : S.hoverItem); return; }
    if (!blk) return;
    const ops = { up: () => moveBlock(blk, -1), down: () => moveBlock(blk, 1), copy: () => dupBlock(blk), hide: () => toggleHide(blk), set: () => select(blk, true), del: () => delBlock(blk) };
    if (ops[act]) ops[act]();
  }

  /* ---------- блоки ---------- */
  const blocksDom = () => (S.fd ? $$('main [data-blk]', S.fd) : []);
  const prevBlock = el => { let s = el.previousElementSibling; while (s && !s.hasAttribute('data-blk')) s = s.previousElementSibling; return s; };
  const nextBlock = el => { let s = el.nextElementSibling; while (s && !s.hasAttribute('data-blk')) s = s.nextElementSibling; return s; };
  function newId(type) {
    let id;
    do { id = String(type).replace(/[^a-z0-9-]/g, '') + '-' + Math.random().toString(36).slice(2, 6); } while (model(id));
    return id;
  }
  function changed(kind) {
    touch('page', kind);
    pushUndo();
    renderPanel();
    schedule();
  }
  function moveBlock(el, dir) {
    const sib = dir < 0 ? prevBlock(el) : nextBlock(el);
    if (!sib) { toast(dir < 0 ? 'Блок уже первый' : 'Блок уже последний'); return; }
    if (dir < 0) sib.parentNode.insertBefore(el, sib); else sib.parentNode.insertBefore(el, sib.nextSibling);
    const m = S.doc.blocks.splice(idx(el.getAttribute('data-blk')), 1)[0];
    const j = idx(sib.getAttribute('data-blk'));
    S.doc.blocks.splice(dir < 0 ? j : j + 1, 0, m);
    changed('порядок блоков');
    el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  function reid(root, oldId, nid, type) { // id заголовков в копии блока — свои, как их сделает сборщик
    const fix = v => (oldId !== type && v.slice(-oldId.length - 1) === '-' + oldId ? v.slice(0, -oldId.length - 1) : v) + '-' + nid;
    $$('[id]', root).forEach(n => { n.id = fix(n.id); });
    [root].concat($$('[aria-labelledby]', root)).forEach(n => {
      const v = n.getAttribute('aria-labelledby');
      if (v) n.setAttribute('aria-labelledby', v.split(/\s+/).map(fix).join(' '));
    });
  }
  function dupBlock(el) {
    const id = el.getAttribute('data-blk'), m = model(id);
    if (!m) return;
    const nid = newId(m.type), copy = clone(m);
    copy.id = nid;
    S.doc.blocks.splice(idx(id) + 1, 0, copy);
    const c = el.cloneNode(true);
    c.setAttribute('data-blk', nid);
    c.classList.remove('dm-hover', 'dm-sel');
    $$('.dm-ihover', c).forEach(x => x.classList.remove('dm-ihover'));
    reid(c, id, nid, m.type);
    el.parentNode.insertBefore(c, el.nextSibling);
    changed('блоки');
    select(c);
    c.scrollIntoView({ block: 'center', behavior: 'smooth' });
    toast('Копия блока — сразу под ним');
  }
  function toggleHide(el) {
    const m = model(el.getAttribute('data-blk'));
    if (!m) return;
    if (m.hidden) delete m.hidden; else m.hidden = true;
    applyStyle(el, m);
    changed('блоки');
    toast(m.hidden ? 'Блок скрыт: на сайте его не будет, здесь он полупрозрачный' : 'Блок снова виден на сайте');
  }
  function delBlock(el) {
    const id = el.getAttribute('data-blk'), i = idx(id);
    if (i < 0) return;
    if (blocksDom().length <= 1) { toast('На странице должен остаться хотя бы один блок'); return; }
    S.doc.blocks.splice(i, 1);
    if (S.sel === el) S.sel = null;
    if (S.hover === el) S.hover = null;
    el.remove();
    changed('блоки');
    toast('Блок удалён', { label: 'Отменить', act: undo });
  }
  function openLibrary(after) {
    S.libAfter = after && after.isConnected ? after : null;
    S.panelMode = 'lib';
    renderPanel();
  }
  function addBlock(type) {
    const html = S.data.library && S.data.library[type];
    if (!html || !S.fd) return;
    const id = newId(type);
    const tpl = S.fd.createElement('template');
    tpl.innerHTML = html.split('zznewzz').join(id);
    const el = tpl.content.firstElementChild;
    if (!el) return;
    const m = { id, type, data: clone((S.data.defaults || {})[type] || {}), style: {} };
    const after = S.libAfter && S.libAfter.isConnected ? S.libAfter : null;
    if (after) {
      after.parentNode.insertBefore(el, after.nextSibling);
      S.doc.blocks.splice(idx(after.getAttribute('data-blk')) + 1, 0, m);
    } else {
      $('main', S.fd).appendChild(el);
      S.doc.blocks.push(m);
    }
    prepare(el);
    syncShared(el); // заготовка собрана при выкладке сайта — показываем общие данные такими, какие они сейчас
    S.panelMode = null;
    S.libAfter = null;
    changed('блоки');
    select(el);
    el.scrollIntoView({ block: 'start', behavior: 'smooth' });
    toast('Блок добавлен. Нажмите на текст в нём и пишите');
  }

  /* ---------- пункты списков (карточки «Это про вас?», пункты списков) ---------- */
  function itemOp(op, item) {
    if (S.editing) S.editing.blur();
    if (!item || !item.isConnected) return;
    const list = item.parentElement;
    if (!editableList(list)) return;
    const loc = locate(list, false), arr = getAt(loc);
    if (!Array.isArray(arr)) return;
    const items = $$(':scope > [data-item]', list), i = items.indexOf(item);
    if (i < 0 || ['up', 'down', 'copy', 'del'].indexOf(op) < 0) return;
    if (op === 'del' && items.length <= 1) { toast('Последний пункт не удалить — просто измените его текст'); return; }
    const j = op === 'up' ? i - 1 : op === 'down' ? i + 1 : i;
    if (j < 0 || j >= items.length) return;
    if (op === 'up' || op === 'down') { const tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp; }
    else if (op === 'copy') arr.splice(i + 1, 0, clone(arr[i]));
    else arr.splice(i, 1);
    // тот же общий список может стоять в другом блоке (копия «Основателя») — меняем его так же, чтобы номера пунктов совпадали
    const key = keyOf(loc);
    const lists = loc.src ? $$('[data-list]', S.fd).filter(l => l === list || (editableList(l) && keyOf(locate(l, false)) === key)) : [list];
    lists.forEach(l => domItemOp(l, op, i, j));
    if (op === 'del') setItem(null);
    touch(scopeOf(loc), 'тексты');
    pushUndo();
    schedule();
  }
  function domItemOp(list, op, i, j) {
    const items = $$(':scope > [data-item]', list), a = items[i];
    if (!a) return;
    if (op === 'up') list.insertBefore(a, items[j]);
    else if (op === 'down') list.insertBefore(a, items[j].nextSibling);
    else if (op === 'copy') { const c = a.cloneNode(true); c.classList.remove('dm-ihover'); list.insertBefore(c, a.nextSibling); }
    else a.remove();
  }
  function syncShared(root) { // общие данные (цифры, основатель, услуги…) в блоке — как они сейчас, с правками этого сеанса
    $$('[data-list]', root).forEach(l => {
      const loc = locate(l, false);
      if (!loc || !loc.src || l.hasAttribute('data-fixed')) return;
      const arr = getAt(loc);
      if (!Array.isArray(arr)) return;
      const items = $$(':scope > [data-item]', l);
      while (items.length > Math.max(arr.length, 1)) items.pop().remove();
      while (items.length && items.length < arr.length) { const c = items[items.length - 1].cloneNode(true); l.appendChild(c); items.push(c); }
    });
    $$('[data-e]', root).forEach(el => { const loc = locate(el); if (loc && loc.src) show(el, getAt(loc)); });
  }

  /* ---------- оформление блока ---------- */
  function applyStyle(el, m) { // то же, что decorate() в build.py
    const st = m.style || {};
    ['pt', 'pb', 'ptm', 'pbm'].forEach(k => {
      const on = /^\d{1,3}$/.test(String(st[k] == null ? '' : st[k]));
      el.classList.toggle('blk-' + k, on);
      if (on) el.style.setProperty('--' + k, Math.min(+st[k], 400) + 'px'); else el.style.removeProperty('--' + k);
    });
    const bg = (S.data.bg || {})[st.bg] || (/^#[0-9a-f]{6}$/i.test(st.bg || '') ? st.bg : '');
    el.classList.toggle('blk-bg', !!bg);
    if (bg) el.style.setProperty('--bgc', bg); else el.style.removeProperty('--bgc');
    el.classList.toggle('blk-hm', st.show === 'desktop');
    el.classList.toggle('blk-hd', st.show === 'mobile');
    el.classList.toggle('blk-off', !!m.hidden);
  }
  function setStyle(key, v, commit) {
    const el = S.sel, m = el && model(el.getAttribute('data-blk'));
    if (!m) return;
    if (!m.style || typeof m.style !== 'object') m.style = {};
    if (v === '' || v == null) delete m.style[key]; else m.style[key] = v;
    applyStyle(el, m);
    touch('page', 'оформление');
    schedule();
    if (commit) { pushUndo(); renderPanel(); }
  }

  /* ---------- панель справа ---------- */
  function select(el, focusPanel) {
    const next = el && el.isConnected ? el : null;
    if (S.sel !== next) {
      if (S.sel) S.sel.classList.remove('dm-sel');
      S.sel = next;
      if (next) next.classList.add('dm-sel');
      S.panelMode = null;
      renderPanel();
      schedule();
    }
    if (focusPanel) ui.panel.scrollTop = 0;
  }
  function renderPanel() {
    if (!S.data) return;
    if (S.panelMode === 'lib') { renderLibrary(); return; }
    const el = S.sel && S.sel.isConnected ? S.sel : null, m = el && model(el.getAttribute('data-blk'));
    if (!m) { renderPage(); return; }
    const t = S.data.types[m.type] || { name: m.type, about: '' }, st = m.style || {};
    ui.panel.innerHTML =
      '<div class="ph"><div><b>' + esc(t.name) + '</b><span>' + esc(t.about) + '</span></div>' +
      '<button type="button" class="kx" data-p="close" title="Закрыть" aria-label="Закрыть">' + svg('x') + '</button></div>' +
      (m.hidden ? '<p class="pwarn">Блок скрыт: на сайте его нет. Здесь он полупрозрачный.</p>' : '') +
      '<section class="pg"><h3>Отступы</h3><p class="pnote">«Авто» — как задумано в дизайне. Телефон — отдельно.</p>' +
      pad('pt', 'Компьютер · сверху', st) + pad('pb', 'Компьютер · снизу', st) + pad('ptm', 'Телефон · сверху', st) + pad('pbm', 'Телефон · снизу', st) + '</section>' +
      '<section class="pg"><h3>Фон</h3><div class="sw">' + bgButtons(st) + '</div></section>' +
      '<section class="pg"><h3>Показывать на сайте</h3><div class="seg">' +
      [['', 'Везде'], ['desktop', 'Компьютер'], ['mobile', 'Телефон']].map(o => '<button type="button" data-show="' + o[0] + '" class="' + ((st.show || '') === o[0] ? 'on' : '') + '" aria-pressed="' + ((st.show || '') === o[0]) + '">' + o[1] + '</button>').join('') +
      '</div></section>' + optionsHtml(m) +
      '<section class="pg"><h3>Блок</h3><div class="pa">' +
      '<button type="button" data-p="up">' + svg('up', 16) + 'Выше</button><button type="button" data-p="down">' + svg('down', 16) + 'Ниже</button>' +
      '<button type="button" data-p="copy">' + svg('copy', 16) + 'Копия</button><button type="button" data-p="hide">' + svg(m.hidden ? 'eye' : 'eyeOff', 16) + (m.hidden ? 'Показать' : 'Скрыть') + '</button>' +
      '<button type="button" data-p="del" class="danger">' + svg('trash', 16) + 'Удалить</button></div>' +
      '<button type="button" class="kbtn kprimary wide" data-p="lib">' + svg('plus', 16) + 'Добавить блок ниже</button></section>' +
      '<section class="pg"><h3>Подсказка</h3><p class="pnote">' + esc(HELP[m.type] || HELP._) + '</p></section>';
  }
  /* свои настройки блока (например, сколько новостей показывать) — из build.py, BLOCK_OPTIONS */
  const optionsOf = m => ((S.data.types[m.type] || {}).options || []);
  const optValue = (m, o) => (m.data && m.data[o.key] != null && m.data[o.key] !== '' ? m.data[o.key] : o.default);
  function optionsHtml(m) {
    return optionsOf(m).map(o => '<section class="pg"><h3>' + esc(o.label) + '</h3><div class="seg" style="grid-template-columns:repeat(' + o.values.length + ',minmax(0,1fr))">' +
      o.values.map(v => {
        const on = String(optValue(m, o)) === String(v);
        return '<button type="button" data-opt="' + esc(o.key) + '" data-val="' + esc(v) + '" class="' + (on ? 'on' : '') + '" aria-pressed="' + on + '">' + esc(v) + '</button>';
      }).join('') + '</div></section>').join('');
  }
  function applyOptions(el, m) {
    optionsOf(m).forEach(o => {
      const v = optValue(m, o);
      if (o.cap) $$('[data-cap]', el).forEach(x => { x.hidden = +x.getAttribute('data-cap') >= +v; });
    });
  }
  function setOption(key, val) {
    const el = S.sel, m = el && model(el.getAttribute('data-blk'));
    const o = m && optionsOf(m).find(x => x.key === key);
    if (!o) return;
    if (!m.data || typeof m.data !== 'object') m.data = {};
    m.data[key] = typeof o.default === 'number' ? +val : val;
    applyOptions(el, m);
    touch('page', 'оформление');
    pushUndo();
    renderPanel();
    schedule();
  }
  function pad(k, label, st) {
    const has = /^\d{1,3}$/.test(String(st[k] == null ? '' : st[k]));
    return '<label class="pr"><span>' + label + '</span><input type="range" min="0" max="200" step="8" value="' + (has ? +st[k] : 0) + '" data-pad="' + k + '" class="' + (has ? '' : 'auto') + '">' +
      '<output>' + (has ? +st[k] + ' px' : 'авто') + '</output>' +
      (has ? '<button type="button" class="kx sm" data-reset="' + k + '" title="Как в дизайне" aria-label="Как в дизайне">' + svg('x', 14) + '</button>' : '<i></i>') + '</label>';
  }
  function bgButtons(st) {
    const cur = st.bg || '', custom = /^#[0-9a-f]{6}$/i.test(cur);
    return BGS.map(o => '<button type="button" class="swb' + (cur === o[0] ? ' on' : '') + '" data-bg="' + o[0] + '" aria-pressed="' + (cur === o[0]) + '" title="' + o[1] + '">' +
      '<i' + (o[0] ? ' style="background:' + SWATCH[o[0]] + '"' : '') + '></i><span>' + o[1] + '</span></button>').join('') +
      '<label class="swb' + (custom ? ' on' : '') + '" title="Свой цвет"><input type="color" data-bgc value="' + (custom ? cur : '#ffffff') + '"><span>Свой</span></label>';
  }
  function renderPage() {
    const rows = blocksDom().map(el => {
      const m = model(el.getAttribute('data-blk')) || {}, t = S.data.types[m.type] || {}, st = m.style || {};
      const badge = m.hidden ? 'скрыт' : st.show === 'desktop' ? 'только компьютер' : st.show === 'mobile' ? 'только телефон' : '';
      return '<li><button type="button" data-goto="' + esc(el.getAttribute('data-blk')) + '"><b>' + esc(t.name || m.type) + '</b>' + (badge ? '<em>' + badge + '</em>' : '') + '</button></li>';
    }).join('');
    ui.panel.innerHTML =
      '<div class="ph"><div><b>Страница «' + esc(S.data.page.title || 'Главная') + '»</b><span>Правьте прямо на странице слева.</span></div></div>' +
      '<section class="pg"><h3>Как это работает</h3><ol class="steps">' +
      '<li>Текст — нажмите и пишите. Enter — готово, Esc — отменить.</li>' +
      '<li>Фото — нажмите на фото и выберите новое.</li>' +
      '<li>Блок — наведите: выше, ниже, копия, скрыть, настройки, удалить.</li>' +
      '<li>Карточки и пункты списков — наведите на пункт: появятся свои кнопки.</li>' +
      '<li>Отступы, фон и показ на телефоне — нажмите на блок, настройки появятся здесь.</li>' +
      '<li>Всё готово — «Опубликовать». Сайт обновится примерно через минуту.</li></ol></section>' +
      '<section class="pg"><h3>Блоки страницы</h3><ul class="bl">' + rows + '</ul>' +
      '<button type="button" class="kbtn kprimary wide" data-p="lib">' + svg('plus', 16) + 'Добавить блок</button></section>';
  }
  function renderLibrary() {
    const items = Object.keys(S.data.types).map(t => {
      const v = S.data.types[t];
      return '<button type="button" class="lib" data-add-type="' + esc(t) + '"><b>' + esc(v.name) + '</b><span>' + esc(v.about) + '</span></button>';
    }).join('');
    ui.panel.innerHTML =
      '<div class="ph"><div><b>Добавить блок</b><span>' + (S.libAfter ? 'Появится под блоком «' + esc(blockName(S.libAfter)) + '»' : 'Появится в конце страницы') + '</span></div>' +
      '<button type="button" class="kx" data-p="back" title="Назад" aria-label="Назад">' + svg('x') + '</button></div><div class="libs">' + items + '</div>';
  }
  function bindPanel() {
    const p = ui.panel;
    p.addEventListener('input', e => {
      const r = e.target;
      if (r.dataset.pad) {
        r.classList.remove('auto');
        setStyle(r.dataset.pad, r.value);
        const out = r.parentNode.querySelector('output');
        if (out) out.textContent = r.value + ' px';
      } else if (r.hasAttribute('data-bgc')) setStyle('bg', r.value);
    });
    p.addEventListener('change', e => {
      const r = e.target;
      if (r.dataset.pad || r.hasAttribute('data-bgc')) { pushUndo(); renderPanel(); }
    });
    p.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b) return;
      if (S.editing) S.editing.blur();
      if (b.dataset.reset) { setStyle(b.dataset.reset, '', true); return; }
      if (b.hasAttribute('data-bg')) { setStyle('bg', b.getAttribute('data-bg'), true); return; }
      if (b.hasAttribute('data-show')) { setStyle('show', b.getAttribute('data-show'), true); return; }
      if (b.hasAttribute('data-opt')) { setOption(b.getAttribute('data-opt'), b.getAttribute('data-val')); return; }
      if (b.dataset.addType) { addBlock(b.dataset.addType); return; }
      if (b.dataset.goto) {
        const el = S.fd && $('[data-blk="' + CSS.escape(b.dataset.goto) + '"]', S.fd);
        if (el) { select(el); el.scrollIntoView({ block: 'start', behavior: 'smooth' }); }
        return;
      }
      const a = b.dataset.p;
      if (!a) return;
      if (a === 'close') { select(null); return; }
      if (a === 'back') { S.panelMode = null; renderPanel(); return; }
      if (a === 'lib') { openLibrary(S.sel); return; }
      const el = S.sel;
      if (!el) return;
      const ops = { up: () => moveBlock(el, -1), down: () => moveBlock(el, 1), copy: () => dupBlock(el), hide: () => toggleHide(el), del: () => delBlock(el) };
      if (ops[a]) ops[a]();
    });
  }

  /* ---------- отмена и возврат ---------- */
  function snap() {
    const src = {};
    Object.keys(S.src).forEach(n => { src[n] = S.src[n].doc; });
    return { doc: JSON.stringify(S.doc), src: JSON.stringify(src), html: $('main', S.fd).innerHTML, dirty: Array.from(S.dirty), kinds: Array.from(S.kinds) };
  }
  function pushUndo(initial) {
    if (!S.fd) return;
    const s = snap(), last = S.undo[S.undo.length - 1];
    if (last && last.doc === s.doc && last.src === s.src && last.html === s.html) return;
    S.undo.push(s);
    if (S.undo.length > 80) S.undo.splice(1, 1);
    if (!initial) S.redo = [];
    undoButtons();
  }
  function restore(s) {
    if (S.editing) { S.editing = null; tip(null); }
    S.doc = JSON.parse(s.doc);
    const src = JSON.parse(s.src);
    Object.keys(src).forEach(n => { if (S.src[n]) S.src[n].doc = src[n]; });
    $('main', S.fd).innerHTML = s.html;
    $$('.dm-hover, .dm-sel, .dm-ihover', S.fd).forEach(x => x.classList.remove('dm-hover', 'dm-sel', 'dm-ihover'));
    S.hover = null;
    S.hoverItem = null;
    const id = S.sel && S.sel.getAttribute('data-blk');
    S.sel = id ? $('[data-blk="' + CSS.escape(id) + '"]', S.fd) : null;
    if (S.sel) S.sel.classList.add('dm-sel');
    S.dirty = new Set(s.dirty);
    S.kinds = new Set(s.kinds);
    saveDraft();
    updateStatus();
    renderPanel();
    schedule();
    undoButtons();
  }
  function undo() { if (S.undo.length < 2) return; S.redo.push(S.undo.pop()); restore(S.undo[S.undo.length - 1]); }
  function redo() { const s = S.redo.pop(); if (!s) return; S.undo.push(s); restore(s); }
  function undoButtons() { ui.undo.disabled = S.undo.length < 2; ui.redo.disabled = !S.redo.length; }
  function onShortcut(e) {
    if (!(e.metaKey || e.ctrlKey)) return;
    const k = String(e.key || '').toLowerCase();
    if ((k === 'z' || k === 'я') && !e.shiftKey) { e.preventDefault(); undo(); }
    else if (((k === 'z' || k === 'я') && e.shiftKey) || k === 'y' || k === 'н') { e.preventDefault(); redo(); }
    else if (k === 's' || k === 'ы') {
      e.preventDefault();
      toast(S.dirty.size ? 'Черновик сохранён в этом браузере. Чтобы правки появились на сайте — «Опубликовать»' : 'Всё уже опубликовано');
    }
  }

  /* ---------- черновик в этом браузере ---------- */
  const refOf = v => JSON.stringify(v).slice(1, -1); // как путь к фото выглядит внутри JSON
  function pruneUploads() { // фото, на которые больше ничто не ссылается (и отмена к ним не вернёт), из памяти убираем
    const all = [JSON.stringify(S.doc)].concat(Object.keys(S.src).map(n => JSON.stringify(S.src[n].doc)), S.undo.map(s => s.doc + s.src), S.redo.map(s => s.doc + s.src)).join('');
    Object.keys(S.uploads).forEach(v => { if (all.indexOf(refOf(v)) === -1) delete S.uploads[v]; });
  }
  function draftObj() {
    let html = $('main', S.fd).innerHTML;
    Object.keys(S.uploads).forEach(v => { html = html.split(S.uploads[v].url).join('dm-upload:' + v); });
    const src = {};
    Object.keys(S.src).forEach(n => { src[n] = S.src[n].doc; });
    // отпечатки файлов на момент черновика: если их потом изменят в админке, публикация черновика это заметит
    return { v: 2, rev: S.rev, t: Date.now(), doc: S.doc, src, sha: Object.assign({}, S.sha), dirty: Array.from(S.dirty), kinds: Array.from(S.kinds), html, uploads: S.uploads };
  }
  function saveDraftNow() {
    if (!S.fd) return;
    if (!S.dirty.size) { LS.del(DRAFT); return; }
    pruneUploads();
    const d = draftObj();
    if (LS.set(DRAFT, JSON.stringify(d))) return;
    d.dropped = Object.keys(S.uploads).filter(v => !S.uploads[v].done); // фото не влезли: при возврате черновика их ссылки снимем
    d.uploads = {};
    if (!LS.set(DRAFT, JSON.stringify(d))) toast('Черновик не помещается в память браузера — опубликуйте правки, чтобы не потерять их', { err: true });
  }
  function dropRefs(o, value) { // ссылки на потерянное фото → пусто (на сайте будет фото по умолчанию)
    if (Array.isArray(o)) { o.forEach((x, i) => { if (x === value) o[i] = ''; else if (x && typeof x === 'object') dropRefs(x, value); }); return; }
    if (o && typeof o === 'object') Object.keys(o).forEach(k => { if (o[k] === value) o[k] = ''; else if (o[k] && typeof o[k] === 'object') dropRefs(o[k], value); });
  }
  function putHtml(html) { // черновик хранится в браузере — без скриптов и обработчиков событий, только разметка страницы
    const t = S.fd.createElement('template');
    t.innerHTML = html;
    $$('script', t.content).forEach(s => s.remove());
    $$('*', t.content).forEach(n => Array.from(n.attributes).forEach(a => {
      if (/^on/i.test(a.name) || (/^(href|src|action|formaction|xlink:href)$/i.test(a.name) && /^\s*javascript:/i.test(a.value))) n.removeAttribute(a.name);
    }));
    const main = $('main', S.fd);
    main.textContent = '';
    main.appendChild(t.content);
  }
  function saveDraft() { clearTimeout(S.dt); S.dt = setTimeout(saveDraftNow, 500); }
  function restoreDraftOffer() {
    const raw = LS.get(DRAFT);
    if (!raw) return;
    let d = null;
    try { d = JSON.parse(raw); } catch (e) { d = null; }
    if (!d || !d.doc || typeof d.html !== 'string') { LS.del(DRAFT); return; }
    const when = new Date(d.t).toLocaleString('ru-RU', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' });
    modal('<h2>Есть неопубликованные правки</h2><p>Черновик от ' + esc(when) + '. Вернуть его на страницу?</p>' +
      (d.rev !== S.rev ? '<p class="pwarn" style="margin:0">С тех пор сайт меняли. Если те же данные успели изменить в админке, при публикации конструктор предупредит.</p>' : ''),
      [['Вернуть черновик', () => applyDraft(d), 'primary'], ['Удалить черновик', () => LS.del(DRAFT)]]);
  }
  function applyDraft(d) {
    const dirty = new Set(d.dirty && d.dirty.length ? d.dirty : ['page']);
    const shas = d.sha || {};
    // возвращаем только то, что в черновике правили; отпечатки — тех времён, чтобы проверка нашла чужие правки, сделанные с тех пор
    if (dirty.has('page')) {
      S.doc = d.doc;
      S.sha[S.data.page.file] = shas[S.data.page.file] !== undefined ? shas[S.data.page.file] : S.sha[S.data.page.file];
    }
    Object.keys(d.src || {}).forEach(n => {
      if (!S.src[n] || !dirty.has('src:' + n)) return;
      S.src[n].doc = d.src[n];
      if (shas[S.src[n].file] !== undefined) S.sha[S.src[n].file] = shas[S.src[n].file];
    });
    S.uploads = d.uploads || {};
    (d.dropped || []).forEach(v => { dropRefs(S.doc, v); Object.keys(S.src).forEach(n => dropRefs(S.src[n].doc, v)); });
    if (dirty.has('page')) {
      let html = d.html;
      Object.keys(S.uploads).forEach(v => { html = html.split('dm-upload:' + v).join(S.uploads[v].url); });
      putHtml(html.replace(/dm-upload:[^"' )]*/g, ''));
    }
    syncShared($('main', S.fd)); // общие данные — из файлов, а не из старой разметки черновика
    S.dirty = dirty;
    S.kinds = new Set(d.kinds || []);
    S.sel = null;
    S.hover = null;
    S.hoverItem = null;
    pushUndo();
    updateStatus();
    renderPanel();
    schedule();
    toast(d.dropped && d.dropped.length ? 'Черновик вернулся, но новое фото не поместилось в память браузера — загрузите его ещё раз' : 'Черновик вернулся на страницу',
      d.dropped && d.dropped.length ? { err: true } : undefined);
  }

  /* ---------- фото ---------- */
  function imgSrc(v) {
    if (!v) return BASE + 'img/artem.webp';
    if (S.uploads[v]) return S.uploads[v].url;
    if (/^(https?:)?\/\//i.test(v) || /^data:/.test(v)) return v;
    return BASE + encodeURI(String(v).replace(/^\//, ''));
  }
  function pickImage(img) {
    S.pickFor = img;
    const f = $('#dm-file', S.fd);
    f.value = '';
    f.click();
  }
  function onFile(e) {
    const file = e.target.files && e.target.files[0], img = S.pickFor;
    if (!file || !img) return;
    if (!/^image\//.test(file.type)) { toast('Это не картинка — выберите фото', { err: true }); return; }
    toast('Готовлю фото…');
    const reader = new FileReader();
    reader.onload = () => {
      const im = new Image();
      im.onload = () => {
        const k = Math.min(1, 1600 / Math.max(im.naturalWidth, im.naturalHeight)); // больше 1600 px сайту не нужно
        const c = document.createElement('canvas');
        c.width = Math.max(1, Math.round(im.naturalWidth * k));
        c.height = Math.max(1, Math.round(im.naturalHeight * k));
        c.getContext('2d').drawImage(im, 0, 0, c.width, c.height);
        let url = c.toDataURL('image/webp', 0.86), ext = 'webp';
        if (url.indexOf('data:image/webp') !== 0) { url = c.toDataURL('image/jpeg', 0.86); ext = 'jpg'; }
        const name = slug(file.name.replace(/\.[^.]+$/, '')) + '-' + Date.now().toString(36) + '.' + ext;
        const value = '/img/uploads/' + name;
        S.uploads[value] = { path: 'src/img/uploads/' + name, url };
        const loc = locate(img);
        if (!setAt(loc, value)) return;
        S.kinds.add('фото');
        img.src = url;
        twins(img, loc, value);
        pushUndo();
        toast('Фото заменено. На сайте появится после «Опубликовать»');
      };
      im.onerror = () => toast('Не получилось открыть это фото', { err: true });
      im.src = reader.result;
    };
    reader.readAsDataURL(file);
  }

  /* ---------- вход, статус, публикация ---------- */
  const token = () => (J && J.token ? J.token() : '');
  function setNote(text, cls) { S.note = text || ''; S.noteCls = cls || ''; updateStatus(); }
  function updateStatus() {
    if (!ui.status) return;
    const n = S.dirty.size;
    ui.pub.disabled = !n || S.busy || !S.fd;
    if (S.busy) return;
    if (n) { ui.status.textContent = 'Есть неопубликованные правки'; ui.status.className = 'kstatus warn'; }
    else { ui.status.textContent = S.note || 'Всё опубликовано'; ui.status.className = 'kstatus' + (S.noteCls ? ' ' + S.noteCls : ''); }
  }
  async function headOid(t) {
    const r = await fetch(API + '/repos/' + S.data.repo + '/git/ref/heads/' + S.data.branch, { headers: { Authorization: 'Bearer ' + t, Accept: 'application/vnd.github+json' }, cache: 'no-store' });
    if (r.status === 401) throw new Error('Ключ входа больше не работает. Войдите в админку заново по своей ссылке.');
    if (!r.ok) throw new Error('GitHub не ответил (' + r.status + '). Попробуйте ещё раз.');
    return (await r.json()).object.sha;
  }
  function authCheck() {
    const t = token();
    ui.login.hidden = !!t;
    if (!t || !S.data || S.rev === 'local') return;
    headOid(t).then(h => {
      if (h && h !== S.rev && !S.dirty.size) setNote('Сайт обновляется после свежей правки — через минуту обновите эту страницу', 'warn');
    }).catch(() => { /* проверим при публикации */ });
  }
  async function blobSha(contentB64) { // отпечаток файла, как его считает git
    const bytes = Uint8Array.from(atob(contentB64), ch => ch.charCodeAt(0));
    const head = new TextEncoder().encode('blob ' + bytes.length + '\0');
    const all = new Uint8Array(head.length + bytes.length);
    all.set(head);
    all.set(bytes, head.length);
    const h = await crypto.subtle.digest('SHA-1', all);
    return Array.from(new Uint8Array(h), x => x.toString(16).padStart(2, '0')).join('');
  }
  function collect() {
    const files = [], json = o => b64(JSON.stringify(o, null, 2) + '\n');
    if (S.dirty.has('page')) files.push({ path: S.data.page.file, contents: json(S.doc) });
    Object.keys(S.src).forEach(n => { if (S.dirty.has('src:' + n)) files.push({ path: S.src[n].file, contents: json(S.src[n].doc) }); });
    const all = JSON.stringify([S.doc].concat(Object.keys(S.src).map(n => S.src[n].doc)));
    Object.keys(S.uploads).forEach(v => {
      const u = S.uploads[v];
      if (!u.done && all.indexOf(JSON.stringify(v).slice(1, -1)) !== -1) files.push({ path: u.path, contents: u.url.split(',')[1], upload: v });
    });
    return files;
  }
  const NICE = { 'content/site/home.json': 'главная страница', 'content/stats.json': 'цифры', 'content/founder.json': 'основатель', 'content/services.json': 'услуги',
    'content/clients.json': 'наши клиенты', 'content/steps.json': 'шаги', 'content/video.json': 'видео-визитка' };
  async function conflicts(t, head, files) {
    const bad = [];
    for (const f of files) {
      if (!/\.json$/.test(f.path)) continue;
      const r = await fetch(API + '/repos/' + S.data.repo + '/contents/' + f.path.split('/').map(encodeURIComponent).join('/') + '?ref=' + head,
        { headers: { Authorization: 'Bearer ' + t, Accept: 'application/vnd.github+json' }, cache: 'no-store' });
      if (r.status === 404) { if (S.sha[f.path]) bad.push(f.path); continue; }
      if (!r.ok) throw new Error('GitHub не ответил (' + r.status + '). Попробуйте ещё раз.');
      const j = await r.json();
      if (j.sha !== S.sha[f.path]) bad.push(f.path);
    }
    return bad;
  }
  function ghErr(err, status) {
    const m = (err && err.message) || '';
    if (/expected|head|fast.?forward/i.test(m)) return 'Сайт только что изменили. Нажмите «Опубликовать» ещё раз.';
    if (status === 403 || /permission|not accessible|resource not accessible/i.test(m)) return 'У ключа входа нет права сохранять правки (нужно Contents: Read and write).';
    return 'GitHub не принял правку' + (m ? ': ' + m : '') + '.';
  }
  function conflictModal(bad) {
    modal('<h2>Эти данные успели изменить</h2><p>Пока вы правили, в админке поменяли: <b>' + esc(bad.map(p => NICE[p] || p).join(', ')) + '</b>.</p>' +
      '<p>Можно обновить страницу и внести свои правки заново — или опубликовать поверх: тогда изменения из админки в этих данных пропадут.</p>',
      [['Обновить страницу', () => { LS.del(DRAFT); S.dirty.clear(); location.reload(); }, 'primary'], ['Опубликовать поверх', () => publish(true)], ['Отмена']]);
  }
  async function publish(force) {
    if (force !== true) force = false; // при нажатии на кнопку сюда приходит событие
    if (S.busy || !S.dirty.size || !S.fd) return;
    if (S.editing) S.editing.blur();
    const t = token();
    if (!t) {
      modal('<h2>Войдите, чтобы публиковать</h2><p>Откройте админку по своей ссылке для входа (её даёт владелец сайта) и вернитесь сюда. Правки сохранятся в этом браузере.</p>',
        [['Открыть админку', () => window.open('./', '_blank', 'noopener'), 'primary'], ['Позже']]);
      return;
    }
    if (J && J.who && !J.who()) {
      modal('<h2>Как вас подписывать в журнале правок?</h2><p>Имя видит только владелец сайта.</p><input class="kin" id="k-name" maxlength="40" placeholder="Например: Артём" autocomplete="name">',
        [['Опубликовать', () => { if (J.setWho($('#k-name').value)) publish(); else toast('Напишите имя', { err: true }); }, 'primary'], ['Отмена']]);
      setTimeout(() => { const i = $('#k-name'); if (i) i.focus(); }, 30);
      return;
    }
    S.busy = true;
    ui.pub.disabled = true;
    ui.pub.classList.add('loading');
    ui.status.textContent = 'Публикую…';
    ui.status.className = 'kstatus';
    try {
      const files = collect();
      if (!files.length) { S.dirty.clear(); toast('Нечего публиковать'); return; }
      const head = await headOid(t);
      if (!force) { // проверяем всегда: файл могли изменить в админке и до прошлой публикации из конструктора
        const bad = await conflicts(t, head, files);
        if (bad.length) { conflictModal(bad); return; }
      }
      const kinds = Array.from(S.kinds);
      const req = {
        query: 'mutation($input: CreateCommitOnBranchInput!) { createCommitOnBranch(input: $input) { commit { oid } } }',
        variables: { input: {
          branch: { repositoryNameWithOwner: S.data.repo, branchName: S.data.branch },
          expectedHeadOid: head,
          fileChanges: { additions: files.map(f => ({ path: f.path, contents: f.contents })) },
          message: { headline: 'Конструктор: ' + (S.data.page.title || 'главная').toLowerCase() + (kinds.length ? ' — ' + kinds.join(', ') : ''), body: 'Правка из конструктора сайта.' }
        } }
      };
      let body = JSON.stringify(req);
      if (J && J.addJournal) body = await J.addJournal(body); // строка журнала: кто, когда, IP — зашифровано для владельца
      const r = await fetch(API + '/graphql', { method: 'POST', headers: { Authorization: 'Bearer ' + t, 'Content-Type': 'application/json' }, body });
      const j = await r.json().catch(() => ({}));
      if (r.status === 401) throw new Error('Ключ входа больше не работает. Войдите в админку заново по своей ссылке.');
      const err = j && j.errors && j.errors[0];
      if (!r.ok || err || !(j.data && j.data.createCommitOnBranch)) throw new Error(ghErr(err, r.status));
      const oid = j.data.createCommitOnBranch.commit.oid;
      for (const f of files) {
        if (f.upload) S.uploads[f.upload].done = true;
        else S.sha[f.path] = await blobSha(f.contents);
      }
      S.rev = oid;
      S.dirty.clear();
      S.kinds.clear();
      LS.del(DRAFT);
      S.undo = [snap()];
      S.redo = [];
      undoButtons();
      watchDeploy(oid);
      toast('Опубликовано. Сайт обновится примерно через минуту');
      return true;
    } catch (e) {
      toast(e && e.message ? e.message : 'Не получилось опубликовать. Попробуйте ещё раз.', { err: true });
      return false;
    } finally {
      S.busy = false;
      ui.pub.classList.remove('loading');
      updateStatus();
    }
  }
  function watchDeploy(oid) {
    clearInterval(S.watch);
    const t0 = Date.now();
    setNote('Опубликовано · сайт обновляется…', 'ok');
    S.watch = setInterval(async () => {
      try {
        const r = await fetch(EDIT + 'data.json?nc=' + Date.now(), { cache: 'no-store' });
        const j = await r.json();
        if (j.rev === oid) { clearInterval(S.watch); S.watch = 0; setNote('Сайт обновлён', 'ok'); return; }
      } catch (e) { /* повторим */ }
      if (Date.now() - t0 > 6 * 60000) { clearInterval(S.watch); S.watch = 0; setNote('Сайт обновится чуть позже — загляните через пару минут', 'warn'); }
    }, 8000);
  }

  /* ---------- окна и сообщения ---------- */
  function modal(html, buttons) {
    const m = ui.modal;
    m.innerHTML = '<div class="kmb" role="dialog" aria-modal="true">' + html + '<div class="kma">' +
      buttons.map((b, i) => '<button type="button" class="kbtn ' + (b[2] === 'primary' ? 'kprimary' : 'kghost') + '" data-i="' + i + '">' + esc(b[0]) + '</button>').join('') + '</div></div>';
    m.hidden = false;
    m.onclick = e => {
      const b = e.target.closest('[data-i]');
      if (!b) return;
      const f = buttons[+b.getAttribute('data-i')][1];
      m.hidden = true;
      if (f) f();
    };
    m.onkeydown = e => { if (e.key === 'Escape') m.hidden = true; else if (e.key === 'Enter' && e.target.id === 'k-name') { e.preventDefault(); const b = $('[data-i="0"]', m); if (b) b.click(); } };
    const first = $('[data-i="0"]', m);
    if (first) first.focus();
  }
  function toast(text, o) {
    o = o || {};
    const t = ui.toast;
    t.innerHTML = '<span>' + esc(text) + '</span>' + (o.label ? '<button type="button">' + esc(o.label) + '</button>' : '');
    t.className = 'ktoast' + (o.err ? ' err' : '');
    t.hidden = false;
    if (o.label) $('button', t).onclick = () => { t.hidden = true; o.act(); };
    clearTimeout(S.tt);
    S.tt = setTimeout(() => { t.hidden = true; }, o.err ? 9000 : 4500);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
