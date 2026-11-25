/* Бриф на создание интернет-магазина: пошаговая форма, черновик в браузере, голосовой ввод */
(function () {
  'use strict';
  var d = document;
  d.documentElement.classList.remove('no-js');
  var qa = /[?&]qa=1/.test(location.search);
  if (qa) d.documentElement.classList.add('qa');
  var reduce = qa || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var KEY = 'dm-brief-v1';
  var CHECK = '<svg class="i" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor"><path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"/></svg>', MIC = '<svg class="i" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor"><path d="M128,176a48.05,48.05,0,0,0,48-48V64a48,48,0,0,0-96,0v64A48.05,48.05,0,0,0,128,176ZM96,64a32,32,0,0,1,64,0v64a32,32,0,0,1-64,0Zm40,143.6V240a8,8,0,0,1-16,0V207.6A80.11,80.11,0,0,1,48,128a8,8,0,0,1,16,0,64,64,0,0,0,128,0,8,8,0,0,1,16,0A80.11,80.11,0,0,1,136,207.6Z"/></svg>';
  var VOICE = 'Можно надиктовать: нажмите на микрофон у поля';
  var STEPS = [
    { t: 'О бизнесе', qs: [
      { id: 'legal', t: 'Юридическая форма', k: 'one', o: ['ИП', 'ООО', 'Самозанятый', 'Пока нет'], h: 'Нужно для оплаты на сайте и договоров со службами доставки' },
      { id: 'where', t: 'Где вы продаёте сейчас?', k: 'many', o: ['Wildberries', 'Ozon', 'Яндекс Маркет', 'Авито', 'Соцсети', 'Офлайн-магазин', 'Пока нигде', 'Другое'] },
      { id: 'orders', t: 'Сколько заказов в месяц у вас сейчас?', k: 'one', o: ['До 100', '100–500', '500–2000', 'Больше 2000', 'Пока не продаю'] },
      { id: 'what', t: 'Что вы продаёте и чем ваш бренд отличается от конкурентов?', k: 'long', r: true, h: VOICE }
    ] },
    { t: 'Товары', qs: [
      { id: 'count', t: 'Сколько товаров будет на сайте?', k: 'one', r: true, o: ['До 50', '50–200', '200–1000', 'Больше 1000'] },
      { id: 'stock', t: 'Где хранится товар?', k: 'one', o: ['На складах маркетплейса (FBO)', 'У себя: склад, офис или дом', 'И там, и там'], h: 'Заказы с сайта отправляются с вашего склада: товар со складов маркетплейса обычно отправить нельзя' },
      { id: 'import', t: 'Перенести карточки с маркетплейса на сайт автоматически?', k: 'one', o: ['Да', 'Нет, сделаем заново', 'Не знаю'], h: 'Фото, описания, характеристики и цены перенесём сами — понадобится ключ доступа из кабинета продавца' },
      { id: 'mark', t: 'Подлежит ли товар маркировке «Честный знак»?', k: 'one', o: ['Да', 'Нет', 'Не знаю'] }
    ] },
    { t: 'Сайт', qs: [
      { id: 'extra', t: 'Что ещё добавить на сайт?', k: 'many', o: ['Роли для менеджеров', 'Управление через Телеграм-бот', 'Синхронизация цен и остатков с маркетплейсом', 'Промокоды и акции', 'Бонусы и «Приведи друга»', 'Отзывы покупателей', 'Блог', 'Вкладыш в заказы маркетплейса с промокодом на сайт'], h: 'Базовый набор уже входит — отметьте, что нужно сверху' },
      { id: 'ideas', t: 'Свои идеи и пожелания к сайту', k: 'long', h: 'Напишите или надиктуйте голосом' },
      { id: 'brand', t: 'Есть ли домен и фирменный стиль?', k: 'many', o: ['Есть домен', 'Есть логотип', 'Есть фирменные цвета и шрифты', 'Ничего нет — поможете'] },
      { id: 'refs', t: 'Сайты, которые вам нравятся, и каким должен быть ваш', k: 'long', h: 'Ссылки и пара слов: минимализм, ярко, премиум…' }
    ] },
    { t: 'Доставка и оплата', qs: [
      { id: 'delivery', t: 'Какие службы доставки подключить?', k: 'many', o: ['СДЭК', 'Яндекс Доставка', 'Ozon', 'Wildberries', 'Почта России', 'Свой курьер', 'Самовывоз', 'Подскажите', 'Другое'], h: 'Условия каждой службы для сайтов проверим заранее' },
      { id: 'bank', t: 'В каком банке подключить эквайринг?', k: 'one', o: ['Т-Банк — рекомендуем', 'Сбер', 'Альфа-Банк', 'Точка', 'ВТБ', 'Другой', 'Пока нет расчётного счёта'], h: 'Рекомендуем Т-Банк: интернет-эквайринг подключается быстро, а покупатели с картой Т-Банка платят через T-Pay в пару касаний. Плюс СБП и рассрочка «Долями»' },
      { id: 'pay', t: 'Какие способы оплаты нужны?', k: 'many', o: ['Картой онлайн', 'СБП', 'T-Pay', 'Рассрочка («Долями», «Сплит»)', 'При получении', 'Все перечисленные', 'Другое'] },
      { id: 'payother', t: 'Свой вариант по доставке и оплате', k: 'text', h: 'Если выбрали «Другое» — напишите, что именно' }
    ] },
    { t: 'Запуск', qs: [
      { id: 'who', t: 'Кто будет вести сайт после запуска?', k: 'one', o: ['Сам', 'Менеджер', 'Нужна помощь с ведением'] },
      { id: 'when', t: 'Когда нужен запуск?', k: 'one', r: true, o: ['Как можно скорее', 'В течение месяца', 'Через 1–3 месяца', 'Не спешу'] },
      { id: 'main', t: 'Что для вас самое важное? Что мы могли упустить?', k: 'long', h: 'Любые мысли и пожелания — можно голосом' }
    ] }
  ];
  var OTHER = /^(Другое|Другой)$/;
  var A = {}, step = 0, maxStep = 0;
  try { var saved = JSON.parse(localStorage.getItem(KEY) || 'null'); if (saved && saved.a) { A = saved.a; step = Math.min(saved.s || 0, STEPS.length); maxStep = Math.min(saved.m || step, STEPS.length); } } catch (e) {}
  function save() { try { localStorage.setItem(KEY, JSON.stringify({ a: A, s: step, m: maxStep, t: Date.now() })); } catch (e) {} }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function has(v) { return Array.isArray(v) ? v.length > 0 : !!(v && String(v).trim()); }
  function nums() { var n = 0, m = {}; STEPS.forEach(function (s) { s.qs.forEach(function (q) { m[q.id] = ++n; }); }); return m; }
  var NUM = nums();
  var host = d.getElementById('bsteps'), bar = d.getElementById('bar'), lbl = d.getElementById('bprog-step'), ttl = d.getElementById('bprog-title');
  var pills = d.getElementById('pills'), back = d.getElementById('back'), next = d.getElementById('next'), toast = d.getElementById('toast');

  // поле с микрофоном; имя для экранных дикторов — заголовок вопроса (у «Другое» — «вопрос — свой вариант»)
  function voiceField(id, val, multiline, short, q, other) {
    var name = other ? ' aria-label="' + esc(q.t + ' — свой вариант') + '"' : ' aria-labelledby="qt-' + q.id + '"';
    var f = multiline
      ? '<textarea class="inp' + (short ? ' short' : '') + '" id="' + id + '" rows="' + (short ? 2 : 4) + '" placeholder="Ваш ответ"' + name + '>' + esc(val || '') + '</textarea>'
      : '<input class="inp" id="' + id + '" type="text" placeholder="Ваш вариант" value="' + esc(val || '') + '"' + name + '>';
    return '<div class="voice-wrap">' + f + '<button type="button" class="mic" data-mic="' + id + '" aria-label="Надиктовать голосом" aria-describedby="qt-' + q.id + '">' + MIC + '</button></div><p class="voice-status" id="' + id + '-st" aria-live="polite"></p>';
  }
  function renderQ(q) {
    var a = A[q.id] || {}, h = '<div class="q" id="q-' + q.id + '"><p class="q-title" id="qt-' + q.id + '"><span class="q-num">' + NUM[q.id] + '.</span>' + esc(q.t) + (q.r ? '<span class="q-req">обязательно</span>' : '') + '</p>';
    if (q.h) h += '<p class="q-hint">' + esc(q.h) + '</p>';
    if (q.o) {
      var sel = q.k === 'many' ? (a.v || []) : [a.v];
      h += '<div class="opts" role="group" aria-label="' + esc(q.t) + '">' + q.o.map(function (o) {
        return '<button type="button" class="opt ' + q.k + '" data-q="' + q.id + '" data-v="' + esc(o) + '" aria-pressed="' + (sel.indexOf(o) > -1) + '"><span class="tick">' + CHECK + '</span>' + esc(o) + '</button>';
      }).join('') + '</div>';
      if (q.o.some(function (o) { return OTHER.test(o); })) {
        var shown = sel.some(function (o) { return OTHER.test(o); });
        h += '<div class="other" id="other-' + q.id + '"' + (shown ? '' : ' hidden') + '>' + voiceField('ot-' + q.id, a.other, false, false, q, true) + '</div>';
      }
    } else {
      h += voiceField('tx-' + q.id, a.v, true, q.k === 'text', q, false);
    }
    return h + '<p class="q-err" id="err-' + q.id + '" aria-live="polite"></p></div>';
  }
  function fmtVal(q) {
    var a = A[q.id] || {}, v = a.v;
    if (!has(v)) return '';
    if (Array.isArray(v)) return v.map(function (o) { return OTHER.test(o) && a.other ? o + ': ' + a.other.trim() : o; }).join(', ');
    return OTHER.test(v) && a.other ? v + ': ' + a.other.trim() : String(v).trim();
  }
  function renderReview() {
    return '<h2 tabindex="-1">Проверьте ответы</h2><div class="sum">' + STEPS.map(function (s, i) {
      return '<section class="sum-step"><header><h3>' + esc(s.t) + '</h3><button type="button" data-goto="' + i + '">Изменить</button></header><dl>' + s.qs.map(function (q) {
        var v = fmtVal(q), need = q.r && !v;
        return '<div><dt>' + NUM[q.id] + '. ' + esc(q.t) + '</dt><dd' + (v ? '' : ' class="empty' + (need ? ' need' : '') + '"') + '>' + esc(v || (need ? 'Нужен ответ — это обязательный вопрос' : 'Без ответа')) + '</dd></div>';
      }).join('') + '</dl></section>';
    }).join('') + '</div><div class="bdone" id="bdone" hidden tabindex="-1"><span class="ok">' + CHECK + '</span><h3 class="heading-5">Бриф готов</h3><p>Это демо-версия сайта: в рабочей версии бриф сразу придёт команде в Телеграм и на почту. Пока можно скопировать ответы или скачать их файлом.</p><div class="row"><button type="button" class="btn btn-ghost btn-sm" id="copy">' + '<svg class="i" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor"><path d="M216,32H88a8,8,0,0,0-8,8V80H40a8,8,0,0,0-8,8V216a8,8,0,0,0,8,8H168a8,8,0,0,0,8-8V176h40a8,8,0,0,0,8-8V40A8,8,0,0,0,216,32ZM160,208H48V96H160Zm48-48H176V88a8,8,0,0,0-8-8H96V48H208Z"/></svg>' + '<span>Скопировать ответы</span></button><button type="button" class="btn btn-ghost btn-sm" id="dl">' + '<svg class="i" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor"><path d="M224,144v64a8,8,0,0,1-8,8H40a8,8,0,0,1-8-8V144a8,8,0,0,1,16,0v56H208V144a8,8,0,0,1,16,0Zm-101.66,5.66a8,8,0,0,0,11.32,0l40-40a8,8,0,0,0-11.32-11.32L136,124.69V32a8,8,0,0,0-16,0v92.69L93.66,98.34a8,8,0,0,0-11.32,11.32Z"/></svg>' + '<span>Скачать файлом</span></button><button type="button" class="btn btn-ghost btn-sm" id="again"><span>Заполнить заново</span></button></div></div>';
  }
  function asText() {
    var dt = new Date(), lines = ['Бриф на создание интернет-магазина — Доктор Маркетплейс', 'Дата: ' + dt.toLocaleDateString('ru-RU'), ''];
    STEPS.forEach(function (s) { lines.push(s.t.toUpperCase()); s.qs.forEach(function (q) { lines.push(NUM[q.id] + '. ' + q.t + ': ' + (fmtVal(q) || '—')); }); lines.push(''); });
    return lines.join('\n');
  }
  function say(t) { toast.textContent = t; toast.classList.add('on'); clearTimeout(say.t); say.t = setTimeout(function () { toast.classList.remove('on'); }, 2600); }

  function render(focus) {
    var isReview = step >= STEPS.length;
    host.innerHTML = '<div class="bstep show" id="step-' + step + '">' + (isReview ? renderReview() : '<h2 tabindex="-1">Шаг ' + (step + 1) + '. ' + esc(STEPS[step].t) + '</h2>' + STEPS[step].qs.map(renderQ).join('')) + '</div>';
    if (!reduce) { var el = host.firstChild; el.classList.remove('show'); void el.offsetWidth; el.classList.add('show'); }
    bar.style.setProperty('--p', isReview ? 1 : step / STEPS.length);
    lbl.textContent = isReview ? 'Проверка' : 'Шаг ' + (step + 1) + ' из ' + STEPS.length;
    ttl.textContent = isReview ? 'Почти готово' : STEPS[step].t;
    pills.innerHTML = STEPS.map(function (s, i) { return s.t; }).concat(['Проверка']).map(function (t, i) {
      var cur = i === step, done = i < step || i <= maxStep;
      return '<button type="button" class="pill' + (done && !cur ? ' done' : '') + '"' + (cur ? ' aria-current="step"' : '') + (i > maxStep ? ' disabled' : '') + ' data-goto="' + i + '">' + esc(t) + '</button>';
    }).join('');
    back.hidden = step === 0;
    next.querySelector('span').textContent = isReview ? 'Отправить бриф' : (step === STEPS.length - 1 ? 'К проверке' : 'Далее');
    next.hidden = false; next.closest('.bnav').hidden = false;
    if (window.DMVoice) Array.prototype.forEach.call(host.querySelectorAll('[data-mic]'), function (b) { var id = b.getAttribute('data-mic'); window.DMVoice.attach(b, d.getElementById(id), d.getElementById(id + '-st'), function (val) { applyField(id, val); }); });
    if (focus) {
      // начало шага — сразу под липкой полосой прогресса (scrollIntoView у липкого блока не прокручивает)
      var bp = d.getElementById('bprog'), st = parseFloat(getComputedStyle(bp).top) || 0;
      var y = Math.max(0, host.getBoundingClientRect().top + window.pageYOffset - st - bp.offsetHeight - 16);
      if (Math.abs(window.pageYOffset - y) > 4) window.scrollTo({ top: y, behavior: reduce ? 'auto' : 'smooth' });
      var h2 = host.querySelector('h2'); if (h2) h2.focus({ preventScroll: true });
    }
    save();
  }
  function validStep() {
    var ok = true, first = null;
    STEPS[step].qs.forEach(function (q) {
      var card = d.getElementById('q-' + q.id), err = d.getElementById('err-' + q.id), bad = q.r && !has((A[q.id] || {}).v);
      card.classList.toggle('invalid', bad); err.textContent = bad ? (q.o ? 'Выберите вариант — это обязательный вопрос.' : 'Напишите пару слов — это обязательный вопрос.') : '';
      if (bad && !first) first = card;
    });
    if (first) { first.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' }); ok = false; }
    return ok;
  }
  // первый шаг, где не отвечен обязательный вопрос (-1 — всё отвечено)
  function firstMissing() { for (var i = 0; i < STEPS.length; i++) { if (STEPS[i].qs.some(function (q) { return q.r && !has((A[q.id] || {}).v); })) return i; } return -1; }
  function go(i) { if (window.DMVoice) window.DMVoice.stop(); step = Math.max(0, Math.min(i, STEPS.length)); maxStep = Math.max(maxStep, step); render(true); }
  // ответ из поля → в A (поле на странице или уже убрано, если диктовка закончилась после перехода)
  function applyField(fid, value) {
    var m;
    if ((m = /^tx-(.+)$/.exec(fid))) { (A[m[1]] || (A[m[1]] = {})).v = value; var card = d.getElementById('q-' + m[1]); if (card && card.classList.contains('invalid') && has(value)) { card.classList.remove('invalid'); d.getElementById('err-' + m[1]).textContent = ''; } }
    else if ((m = /^ot-(.+)$/.exec(fid))) (A[m[1]] || (A[m[1]] = {})).other = value;
    save();
  }

  host.addEventListener('click', function (e) {
    var o = e.target.closest('.opt');
    if (o) {
      var id = o.getAttribute('data-q'), v = o.getAttribute('data-v'), q = null;
      STEPS.forEach(function (s) { s.qs.forEach(function (x) { if (x.id === id) q = x; }); });
      var a = A[id] || (A[id] = {});
      if (q.k === 'many') { a.v = a.v || []; var k = a.v.indexOf(v); if (k > -1) a.v.splice(k, 1); else a.v.push(v); }
      else a.v = a.v === v ? '' : v;
      var sel = q.k === 'many' ? a.v : [a.v];
      Array.prototype.forEach.call(o.parentNode.children, function (b) { b.setAttribute('aria-pressed', String(sel.indexOf(b.getAttribute('data-v')) > -1)); });
      var other = d.getElementById('other-' + id);
      if (other) { var on = sel.some(function (x) { return OTHER.test(x); }); other.hidden = !on; if (on && OTHER.test(v) && sel.indexOf(v) > -1) d.getElementById('ot-' + id).focus(); }
      var card = d.getElementById('q-' + id); if (card.classList.contains('invalid') && has(a.v)) { card.classList.remove('invalid'); d.getElementById('err-' + id).textContent = ''; }
      save(); return;
    }
    var g = e.target.closest('[data-goto]'); if (g) { go(+g.getAttribute('data-goto')); return; }
    if (e.target.closest('#copy')) { var txt = asText(); var fallback = function () { var ta = d.createElement('textarea'); ta.value = txt; d.body.appendChild(ta); ta.select(); try { d.execCommand('copy'); say('Ответы скопированы'); } catch (x) { say('Не получилось скопировать. Скачайте файлом.'); } ta.remove(); }; if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(txt).then(function () { say('Ответы скопированы'); }, fallback); else fallback(); return; }
    if (e.target.closest('#dl')) { var blob = new Blob([asText()], { type: 'text/plain;charset=utf-8' }), url = URL.createObjectURL(blob), a2 = d.createElement('a'); a2.href = url; a2.download = 'Бриф — Доктор Маркетплейс.txt'; d.body.appendChild(a2); a2.click(); setTimeout(function () { URL.revokeObjectURL(url); a2.remove(); }, 500); say('Файл с ответами скачан'); return; }
    if (e.target.closest('#again')) { A = {}; step = 0; maxStep = 0; try { localStorage.removeItem(KEY); } catch (x) {} render(true); return; }
  });
  host.addEventListener('input', function (e) { applyField(e.target.id, e.target.value); });
  pills.addEventListener('click', function (e) { var g = e.target.closest('[data-goto]'); if (g && !g.disabled) go(+g.getAttribute('data-goto')); });
  back.addEventListener('click', function () { go(step - 1); });
  next.addEventListener('click', function () {
    if (next.classList.contains('loading')) return;
    if (window.DMVoice) window.DMVoice.stop();
    if (step < STEPS.length) { if (validStep()) go(step + 1); return; }
    // перед отправкой — все обязательные вопросы (на проверку можно попасть вкладками, минуя «Далее»)
    var miss = firstMissing();
    if (miss > -1) { go(miss); validStep(); say('Ответьте на обязательный вопрос — и бриф можно отправить'); return; }
    next.classList.add('loading'); next.setAttribute('aria-busy', 'true');
    setTimeout(function () {
      next.classList.remove('loading'); next.removeAttribute('aria-busy');
      var done = d.getElementById('bdone');
      if (!done || step < STEPS.length) return; // за эту секунду ушли с проверки — отправку не показываем
      try { localStorage.removeItem(KEY); } catch (x) {}
      next.hidden = true; back.hidden = true; next.closest('.bnav').hidden = true; ttl.textContent = 'Бриф готов'; lbl.textContent = 'Готово';
      done.hidden = false; done.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' }); done.focus({ preventScroll: true });
    }, 1100);
  });
  var restore = d.getElementById('restore');
  if (restore && Object.keys(A).some(function (k) { return has((A[k] || {}).v); })) {
    restore.hidden = false;
    d.getElementById('restart').addEventListener('click', function () { A = {}; step = 0; maxStep = 0; try { localStorage.removeItem(KEY); } catch (x) {} restore.hidden = true; render(true); });
  }
  render(false);
})();
