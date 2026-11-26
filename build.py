#!/usr/bin/env python3
"""Сборка сайта «Доктор Маркетплейс».
content/ — всё, что правится в админке /admin: контакты, тексты, цены, кейсы, новости, документы, страницы.
src/     — шаблоны, стили, скрипты и иконки. Результат — site/ (готовые страницы для GitHub Pages или любого хостинга).
Стили и иконки вшиваются в каждую страницу, поэтому на старте нет лишних запросов. Только стандартная библиотека Python 3.9+.
Адрес сайта: переменные окружения SITE_BASE и SITE_URL (по умолчанию копия на GitHub Pages; для своего домена SITE_BASE=/)."""
import hashlib, html, json, math, os, pathlib, re, shutil, sys, time, unicodedata, urllib.parse

P = pathlib.Path(__file__).resolve().parent
SRC, OUT, C = P / 'src', P / 'site', P / 'content'
BASE = os.environ.get('SITE_BASE', '/doctor-marketplace-v2/')
ORIGIN = os.environ.get('SITE_URL', 'https://i78424325.github.io').rstrip('/')
SITE = ORIGIN + BASE
VER = time.strftime('%m%d%H%M')
INDEX = os.environ.get('SITE_INDEX') == '1'  # 1 — открыть сайт поисковикам (когда переедет на свой домен)
REV = os.environ.get('GITHUB_SHA') or 'local'  # какая версия репозитория собрана — конструктор сверяет её с последней правкой

def esc(s):
    """Экранирование для HTML. Фигурные скобки тоже: текст из админки никогда не станет шаблонным тегом {{…}}."""
    return html.escape('' if s is None else str(s)).replace('{', '&#123;')

def warn(msg):
    print('ВНИМАНИЕ: ' + msg, file=sys.stderr)

icons = {}
for f in (SRC / 'icons').glob('*.svg'):
    s = re.sub(r'\s+', ' ', f.read_text(encoding='utf-8')).strip()
    icons[f.stem] = s.replace('<svg ', '<svg class="i" aria-hidden="true" focusable="false" ', 1)

MARK = ('<svg viewBox="0 0 40 40" aria-hidden="true" focusable="false"><rect x=".75" y=".75" width="38.5" height="38.5" rx="11" fill="#4EB679" stroke="#3E9D65" stroke-opacity=".6" stroke-width="1.5"/>'
        '<path d="M6 22h6l3-7 4 13 3-9 2 3h3.5l6-8" fill="none" stroke="#0B1A12" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M28.5 14h5v5" fill="none" stroke="#0B1A12" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>')
OSECOM = ('<svg viewBox="0 0 140 40" role="img" aria-label="OS Ecom"><rect x=".75" y=".75" width="38.5" height="38.5" rx="11" fill="#141414" stroke="#FFFFFF" stroke-opacity=".18" stroke-width="1.5"/>'
          '<rect x="8" y="10" width="24" height="20" rx="4" fill="none" stroke="#F4F6F5" stroke-width="2"/><path d="M8 15.5h24" stroke="#F4F6F5" stroke-width="2"/>'
          '<circle cx="11.5" cy="12.75" r="1" fill="#F4F6F5"/><circle cx="14.5" cy="12.75" r="1" fill="#F4F6F5"/>'
          '<path d="M13 26l5-4.5 3.5 2.5 6-6" fill="none" stroke="#3EF0A6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
          '<text x="50" y="27" font-family="Manrope, system-ui, sans-serif" font-size="20" font-weight="700" fill="#14201A">OS</text>'
          '<text x="83" y="27" font-family="Manrope, system-ui, sans-serif" font-size="20" font-weight="500" fill="#5B6761">Ecom</text></svg>')

# ---------- контент из content/ ----------
def jload(rel):
    f = C / rel
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding='utf-8'))
    except ValueError as e:
        raise SystemExit('Ошибка в файле %s: %s' % (f.relative_to(P), e))

RU = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
              'a b v g d e e zh z i i k l m n o p r s t u f h ts ch sh sch _ y _ e yu ya'.split()))
def slugify(s):
    s = unicodedata.normalize('NFC', str(s or '')).lower()  # имена файлов на macOS бывают в разложенном виде
    s = ''.join(RU.get(ch, ch) for ch in s).replace('_', '')
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')

def num(x, default=99):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return default

def entries(folder):
    out = []
    for f in sorted((C / folder).glob('*.json')):
        d = jload('%s/%s' % (folder, f.name))
        if isinstance(d, dict) and not d.get('hidden'):
            d['_file'] = f.stem
            out.append(d)
    return out

def uniq(items, taken=(), what='Страница'):
    """Адреса не должны совпадать: занятый получает -2, -3… и предупреждение в журнале сборки."""
    seen = set(taken)
    for it in items:
        base, n = it['slug'] or 'page', 2
        it['slug'] = base
        while it['slug'] in seen:
            it['slug'] = '%s-%d' % (base, n)
            n += 1
        if it['slug'] != base:
            warn('%s «%s»: адрес «%s» уже занят, взят «%s»' % (what, it.get('title', ''), base, it['slug']))
        seen.add(it['slug'])
    return items

def flat_home(h):
    """Главная в админке разбита на блоки (hero, who, …); сборщик понимает и блоки, и старый плоский вид."""
    h = dict(h or {})
    for grp, keys in (('hero', {'chip': 'hero_chip', 'title': 'hero_title', 'lead': 'hero_lead', 'button': 'hero_cta'}),
                      ('who', {'chip': 'who_chip', 'title': 'who_title'}),
                      ('services_block', {'chip': 'services_chip', 'title': 'services_title'}),
                      ('news_block', {'chip': 'news_chip', 'title': 'news_title'})):
        g = h.get(grp)
        if isinstance(g, dict):
            for k, flat in keys.items():
                if not h.get(flat):
                    h[flat] = g.get(k) or ''
    if isinstance(h.get('who'), dict):
        h['who'] = h['who'].get('cards') or []
    return h

S, HOME, TX = jload('settings.json'), flat_home(jload('home.json')), jload('texts.json')
VIDEO = jload('video.json')

def msg_url(u, host):
    """Ссылка на бота или аккаунт: «@name», «t.me/name» → полная https-ссылка."""
    u = str(u or '').strip()
    if not u:
        return ''
    if u.startswith('@'):
        return 'https://%s/%s' % (host, u[1:])
    if re.match(r'^https?://', u, re.I):
        return re.sub(r'^http://', 'https://', u, flags=re.I)
    return 'https://' + u.lstrip('/')
for _k, _host in (('telegram_url', 't.me'), ('manager_telegram_url', 't.me'), ('max_url', 'max.ru'), ('manager_max_url', 'max.ru')):
    S[_k] = msg_url(S.get(_k), _host)

SERVICES = uniq([dict(s, slug=slugify(s.get('slug') or s['title']) or 'usluga', _i=k) for k, s in enumerate(jload('services.json').get('services', []))
                 if isinstance(s, dict) and s.get('title')], what='Услуга')  # _i — номер в файле, по нему конструктор находит услугу
BY_SLUG = {s['slug']: s for s in SERVICES}
FAQ = [i for i in jload('faq.json').get('items', []) if i.get('q')]
STATS_IX = [(k, i) for k, i in enumerate(jload('stats.json').get('items', [])) if isinstance(i, dict) and i.get('value')]
STATS = [i for _, i in STATS_IX]
STEPS = jload('steps.json')
CLIENTS = jload('clients.json')
DOCS = uniq(sorted(({'slug': slugify(d.get('url') or d['_file']), 'title': d.get('title') or d['_file'], 'order': num(d.get('order')),
                     'body': d.get('body', '')} for d in entries('docs')), key=lambda d: (d['order'], d['title'])))
# старые новости сохраняют адрес, у новой с тем же заголовком будет -2: ссылки, которыми уже поделились, не меняются
NEWS = list(reversed(uniq(sorted(({'slug': slugify(d.get('url') or re.sub(r'^\d{4}-\d{2}-\d{2}-?', '', d['_file']) or d.get('title')),
                                   'title': d.get('title') or 'Новость', 'date': str(d.get('date') or '')[:10], 'excerpt': d.get('excerpt') or '',
                                   'cover': d.get('cover') or '', 'video': d.get('video') or '', 'body': d.get('body') or '',
                                   'kind': 'Статья' if d.get('kind') == 'Статья' else 'Новость', 'topic': str(d.get('topic') or '').strip(),
                                   'seo_title': str(d.get('seo_title') or '').strip(), 'seo_description': str(d.get('seo_description') or '').strip()}
                                  for d in entries('news')),
                                 key=lambda n: (n['date'], n['slug'])), what='Новость')))

# кейсы — раздел «Кейсы» в админке (content/cases/*.json): площадки, цифры, график по месяцам, было → стало, скриншоты
MP = {'wb': 'Wildberries', 'ozon': 'Ozon'}
def mp_keys(v):
    out = []
    for x in (v if isinstance(v, list) else [v]):
        x = str(x or '').strip().lower()
        k = 'wb' if x in ('wb', 'wildberries', 'вб') else 'ozon' if x in ('ozon', 'озон') else ''
        if k and k not in out:
            out.append(k)
    return out

_AMOUNT = re.compile(r'(?<![\w.,])([-\u2212\u2013]?)(\d{1,3}(?:[ \u00a0\u202f]\d{3})+|\d+)(?:[.,](\d+))?(?:\s*(млрд|млн|тыс|k|к|m|м)(?![а-яёa-z]))?', re.I)
_MULT = {'млрд': 1e9, 'млн': 1e6, 'м': 1e6, 'm': 1e6, 'тыс': 1e3, 'к': 1e3, 'k': 1e3}
def to_num(x):
    """Одно число из цифры или текста: 300000, «1 250 000 ₽», «1,2 млн», «300 тыс», «−5%».
    Числа нет или их несколько («40 заказов в день за 2 мес») — None: лучше ничего не посчитать, чем посчитать неверно."""
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x) if math.isfinite(x) else None
    found = list(_AMOUNT.finditer(str(x)))
    if len(found) != 1:
        return None
    sign, whole, frac, unit = found[0].groups()
    v = float(re.sub(r'\D', '', whole) + ('.' + frac if frac else '')) * _MULT.get((unit or '').lower(), 1)
    return -v if sign else v

CASES = list(reversed(uniq(sorted(({
    'slug': slugify(d.get('url') or re.sub(r'^\d{4}-\d{2}-\d{2}-?', '', d['_file']) or d.get('title')),
    'title': str(d.get('title') or 'Кейс'), 'date': str(d.get('date') or '')[:10], 'excerpt': str(d.get('excerpt') or ''),
    'mp': mp_keys(d.get('marketplaces')), 'niche': str(d.get('niche') or '').strip(), 'period': str(d.get('period') or '').strip(),
    'services': [x.strip() for x in (d.get('services') if isinstance(d.get('services'), list) else [d.get('services')]) if isinstance(x, str) and x.strip()],
    'cover': str(d.get('cover') or ''), 'text': str(d.get('text') or ''), 'video': str(d.get('video') or ''),
    'results': [{'value': str(r['value']).strip(), 'label': str(r.get('label') or '').strip()} for r in d.get('results') or []
                if isinstance(r, dict) and r.get('value') is not None and str(r['value']).strip()],
    'metrics': [m for m in d.get('metrics') or [] if isinstance(m, dict) and m.get('label')],
    'chart': d.get('chart') if isinstance(d.get('chart'), dict) else {},
    'shots': [x for x in d.get('screenshots') or [] if isinstance(x, dict) and x.get('image')]}
    for d in entries('cases')), key=lambda c: (c['date'], c['slug'])), what='Кейс')))
RESERVED = {'uslugi', 'sait', 'keysy', 'o-nas', 'voprosy', 'kontakty', 'novosti', 'dokumenty', 'brief', 'admin', 'img', 'js', 'fonts'}
# у копии страницы (A/B) адрес остаётся за оригиналом: первым идёт файл, чьё имя совпадает с адресом
PAGES = sorted((dict(p, slug=slugify(p.get('url') or p['_file'])) for p in entries('pages')), key=lambda p: (slugify(p['_file']) != p['slug'], p['_file']))
PAGES = uniq(PAGES, taken=RESERVED, what='Страница')
COMPANY = S.get('company_name') or 'Доктор Маркетплейс'

# ---------- ссылки, медиа, мини-Markdown ----------
def media(u):
    """Файл из админки (img/uploads/…) → путь от корня сайта; внешние ссылки как есть."""
    u = str(u or '').strip()
    if not u or re.match(r'^(https?:)?//', u, re.I) or u.startswith('data:'):
        return u
    return BASE + urllib.parse.quote(u.lstrip('/'), safe="/%-._~!$&'()*+,;=:@")  # пробелы и кириллица в имени файла

def href(u, fallback=None):
    """Ссылка из админки → рабочий адрес: внешние как есть (https:// допишем сами), телефон → tel:, остальное — страницы сайта."""
    u = str(u or '').strip()
    if not u:
        return BASE + 'kontakty/' if fallback is None else fallback
    if re.match(r'^(https?:|mailto:|tel:|#)', u, re.I):
        return u
    if re.match(r'^\+?[\d\s()-]{10,}$', u):
        return 'tel:' + re.sub(r'[^\d+]', '', u)
    if not u.startswith('/') and re.match(r'^(www\.|[a-zа-я0-9-]+(\.[a-zа-я0-9-]+)*\.(ru|рф|com|net|org|me|io|su|pro|online|shop|store|info|biz|app|dev)(/|$))', u, re.I):
        return 'https://' + u
    return BASE + u.lstrip('/')

def link_tag(u, label):
    url = href(u, '#')
    ext = bool(re.match(r'^https?:', url, re.I))
    return '<a href="%s"%s>%s</a>' % (esc(url), ' target="_blank" rel="noopener"' if ext else '', label)

def inline(s):
    """Строка из редактора → HTML. Адреса ссылок и картинок прячем до разметки, чтобы курсив и жирный их не задели."""
    keep, urls = [], []
    def hold(x):
        keep.append(x)
        return '\x00%d\x00' % (len(keep) - 1)
    def hold_url(m):
        urls.append(m.group(1).strip().strip('<>').strip())
        return '](\x01%d\x01)' % (len(urls) - 1)
    s = str(s or '')
    s = re.sub(r'\\([\\`*_{}\[\]()#+\-.!|<>~])', lambda m: hold(esc(m.group(1))), s)  # \* → *
    s = re.sub(r'`([^`]+)`', lambda m: hold('<code>%s</code>' % esc(m.group(1))), s)
    s = re.sub(r'\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+"[^"]*")?\s*\)', hold_url, s)
    s = esc(s).replace('&amp;nbsp;', '&nbsp;')
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'~~(.+?)~~', r'<s>\1</s>', s)
    s = re.sub(r'(?<![\w*])[*_](?![\s*_])(.+?)(?<![\s*_])[*_](?![\w*])', r'<em>\1</em>', s)
    s = re.sub(r'!\[([^\]]*)\]\(\x01(\d+)\x01\)', lambda m: '<img src="%s" alt="%s" loading="lazy" decoding="async">' % (
        esc(media(urls[int(m.group(2))])), re.sub(r'<[^>]+>', '', m.group(1))), s)
    s = re.sub(r'\[([^\]]+)\]\(\x01(\d+)\x01\)', lambda m: link_tag(urls[int(m.group(2))], m.group(1)), s)
    s = re.sub(r'\x01(\d+)\x01', lambda m: esc(urls[int(m.group(1))]), s)
    return re.sub(r'\x00(\d+)\x00', lambda m: keep[int(m.group(1))], s)

def md(text):
    """Текст из редактора админки → HTML: заголовки, абзацы (Shift+Enter — перенос строки), списки, цитаты, код, жирный, ссылки, картинки."""
    out, para, items, quote = [], [], [], []
    st = {'kind': None, 'start': 1}
    def flush_p():
        if para:
            out.append('<p>%s</p>' % '<br>'.join(inline(l.strip().rstrip('\\').strip()) for l in para))
            del para[:]
    def flush_list():
        if items:
            attr = ' start="%d"' % st['start'] if st['kind'] == 'ol' and st['start'] != 1 else ''
            out.append('<%s%s>%s</%s>' % (st['kind'], attr, ''.join('<li>%s</li>' % inline(i) for i in items), st['kind']))
            del items[:]
        st['kind'] = None
    def flush_quote():
        if quote:
            groups, cur = [], []
            for q in quote + ['']:
                if q:
                    cur.append(q)
                elif cur:
                    groups.append(cur)
                    cur = []
            if groups:
                out.append('<blockquote>%s</blockquote>' % ''.join('<p>%s</p>' % '<br>'.join(inline(x) for x in g) for g in groups))
            del quote[:]
    def flush():
        flush_p(); flush_list(); flush_quote()
    code = None
    for raw in str(text or '').replace('\r\n', '\n').split('\n'):
        s = raw.strip()
        if code is not None:
            if s.startswith('```'):
                out.append('<pre><code>%s</code></pre>' % esc('\n'.join(code)))
                code = None
            else:
                code.append(raw)
            continue
        if s.startswith('```'):
            flush()
            code = []
            continue
        if s.startswith('>'):
            flush_p(); flush_list()
            quote.append(s[1:].strip())
            continue
        flush_quote()
        if not s:
            flush()
            continue
        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            flush()
            lvl = {1: 2, 2: 2, 3: 3}.get(len(m.group(1)), 4)
            out.append('<h%d>%s</h%d>' % (lvl, inline(m.group(2).rstrip('#').strip()), lvl))
            continue
        if re.match(r'^(-{3,}|\*{3,}|_{3,})$', s):
            flush()
            out.append('<hr>')
            continue
        m, k = re.match(r'^[-*+•]\s+(.*)$', s), 'ul'
        if not m:
            m, k = re.match(r'^(\d+)[.)]\s+(.*)$', s), 'ol'
        if m:
            flush_p()
            if st['kind'] and st['kind'] != k:
                flush_list()
            if not items and k == 'ol':
                st['start'] = int(m.group(1))
            st['kind'] = k
            items.append(m.group(m.lastindex))
            continue
        if items:
            flush_list()
        para.append(raw)
    if code is not None:
        out.append('<pre><code>%s</code></pre>' % esc('\n'.join(code)))
    flush()
    return '\n'.join(out)

def accent(s):
    """*слова* в заголовках → выделение фирменным цветом."""
    return re.sub(r'\*([^*]+)\*', r'<em>\1</em>', esc(s or ''))

def video_html(url, poster='', autoplay=False):
    """Видео: файл mp4/webm из админки, ссылка или код вставки VK Видео / Rutube / YouTube → плеер.
    Незнакомая ссылка — кнопка «Смотреть видео»: чужие сайты обычно запрещают показывать себя во фрейме."""
    url = str(url or '').strip()
    if not url:
        return ''
    m = re.search(r'<iframe[^>]+src="([^"]+)"', url, re.I)  # вставили код из «Поделиться → Код для вставки»
    if m:
        url = html.unescape(m.group(1))
    if url.startswith('//'):
        url = 'https:' + url
    if re.search(r'\.(mp4|webm|mov|m4v)(\?|#|$)', url, re.I) or not re.match(r'^https?://', url, re.I):
        return '<video controls playsinline preload="%s"%s%s src="%s"></video>' % (
            'auto' if autoplay else 'none', ' autoplay' if autoplay else '', ' poster="%s"' % esc(media(poster)) if poster else '', esc(media(url)))
    src = ''
    m = re.search(r'rutube\.ru/(?:video/(?:private/)?|shorts/|play/embed/)([0-9a-f]{32})', url, re.I)
    if m:
        src = 'https://rutube.ru/play/embed/' + m.group(1)
    elif re.search(r'(vk\.com|vk\.ru|vkvideo\.ru)/video_ext\.php\?', url, re.I):
        src = url + ('&autoplay=1' if autoplay and 'autoplay=' not in url else '')
    else:
        m = re.search(r'(?:vk\.com|vkvideo\.ru|vk\.ru)/\S*?(?:video|clip)(-?\d+)_(\d+)', url, re.I)
        if m:
            h = re.search(r'[?&]hash=([0-9a-f]+)', url)
            src = 'https://vk.com/video_ext.php?oid=%s&id=%s&hd=2%s%s' % (m.group(1), m.group(2), '&hash=' + h.group(1) if h else '', '&autoplay=1' if autoplay else '')
        else:
            m = re.search(r'(?:youtube\.com/\S*?[?&]v=|youtu\.be/|youtube(?:-nocookie)?\.com/(?:shorts|embed|live)/)([\w-]{11})', url, re.I)
            if m:
                src = 'https://www.youtube-nocookie.com/embed/%s%s' % (m.group(1), '?autoplay=1' if autoplay else '')
    if not src:
        return '<a class="video-link" href="%s" target="_blank" rel="noopener">{{icon:play}}<span>Смотреть видео</span></a>' % esc(url)
    return ('<iframe src="%s" title="Видео" loading="lazy" allow="autoplay; encrypted-media; fullscreen; picture-in-picture; screen-wake-lock" allowfullscreen></iframe>' % esc(src))

def price_value(s):
    p = str(s.get('price_from') or '').strip()
    return re.sub(r'\s*(₽|руб(\.|лей)?|р\.)$', '', re.sub(r'^от\s*', '', p, flags=re.I), flags=re.I).strip()  # «от 15000 ₽» → 15000

def price_html(s, cls='price'):
    p = price_value(s)
    if p:
        p = re.sub(r'(?<=\d)(?=(\d{3})+(?!\d))', '&nbsp;', re.sub(r'\s+', '', p)) if re.fullmatch(r'[\d\s]+', p) else esc(p)
        return '<span class="%s">от <b>%s&nbsp;₽</b></span>' % (cls, p)
    return '<span class="%s %s-empty">Цена от …&nbsp;₽</span>' % (cls, cls)

MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
def ru_date(d):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', d or '')
    return '%d %s %s' % (int(m.group(3)), MONTHS[int(m.group(2)) - 1], m.group(1)) if m else esc(d or '')

def crumbs(*items):
    parts = ['<a href="{{base}}">Главная</a>']
    for label, url in items:
        parts.append('<span class="sep" aria-hidden="true">/</span>')
        parts.append('<a href="%s">%s</a>' % (url, esc(label)) if url else '<span aria-current="page">%s</span>' % esc(label))
    return '<nav class="crumbs" aria-label="Вы здесь">%s</nav>' % ''.join(parts)

def icon(name, fallback='check-circle'):
    return '{{icon:%s}}' % (name if name in icons else fallback)

# ---------- пометки для конструктора: только в версии страницы для редактора (admin/edit/), на сайте их нет ----------
def ea(ed, name, fmt=None, fb=None):
    """Поле, которое правится прямо на странице: data-e — имя поля («.» — сам пункт списка), data-fmt — разметка ([WB], *акцент*),
    data-fb — что показывает сайт, пока поле пустое (конструктор показывает то же самое)."""
    return (' data-e="%s"%s%s' % (name, ' data-fmt="%s"' % fmt if fmt else '', ' data-fb="%s"' % esc(fb) if fb else '')) if ed else ''

def el(ed, name, fixed=False, src=None):
    """Список: data-list — поле-список; data-fixed — на странице правится только текст; data-src — общий файл (stats, founder…)."""
    return (' data-list="%s"%s%s' % (name, ' data-fixed' if fixed else '', ' data-src="%s"' % src if src else '')) if ed else ''

def ei(ed, i=None):
    return (' data-item' + (' data-i="%d"' % i if i is not None else '')) if ed else ''

def es(ed, src):
    return ' data-src="%s"' % src if ed else ''

# ---------- блоки ----------
_vz = re.split(r'<!--@viz ([a-z0-9-]+)-->', (SRC / 'pages' / 'viz.html').read_text(encoding='utf-8'))
VIZ = {_vz[i]: _vz[i + 1].strip() for i in range(1, len(_vz), 2)}

def bento_html(ed=False):
    """Плитки услуг в порядке из админки: первая — большая (2×2), ряд добирается широкими плитками."""
    n = len(SERVICES)
    wides = (4 - (n + 3) % 4) % 4 if n > 1 else 0
    wide = set(range(max(1, n - 1 - wides), n - 1)) if wides else set()
    out = []
    for k, s in enumerate(SERVICES):
        slug = s['slug']
        size = ' tile-big' if k == 0 else (' tile-wide' if k in wide else '')
        url = '{{base}}sait/' if slug == 'sait' else '{{base}}uslugi/%s/' % slug
        out.append('<a class="tile tile-%s%s" href="%s" data-reveal style="--d:%dms"%s><div class="tile-copy"><h3%s>%s</h3><p%s>%s</p>%s</div>'
                   '<div class="viz" aria-hidden="true">%s</div><span class="tile-go" aria-hidden="true">{{icon:arrow-up-right}}</span></a>'
                   % (slug, size, url, (k % 4) * 70, ei(ed, s['_i']), ea(ed, 'title'), esc(s['title']),
                      ea(ed, 'tile_text', fb=s.get('short', '')), esc(s.get('tile_text') or s.get('short', '')),
                      '' if slug == 'sait' and not price_value(s) else price_html(s), VIZ.get(slug, '')))
    return ''.join(out)

def answer_html(a):
    """Ответ в вопросах — это HTML (можно ссылки). Пустая строка — новый абзац, перенос — новая строка; {{base}} — адрес сайта."""
    a = str(a or '').replace('\r\n', '\n').replace('{{base}}', BASE).replace('{', '&#123;')
    parts = [p.strip() for p in re.split(r'\n\s*\n', a) if p.strip()]
    return ''.join('<p>%s</p>' % p.replace('\n', '<br>') for p in parts) or '<p></p>'

def faq_html(items):
    return ''.join('<details><summary>%s<span class="pm">{{icon:plus}}</span></summary><div class="ans">%s</div></details>'
                   % (esc(i['q']), answer_html(i.get('a'))) for i in items)

def steps_html(items, compact=False, ed=False, lst='items'):
    line = '' if compact else '<div class="steps-line" aria-hidden="true"><i></i></div>'
    cls = ' compact' if compact else (' three' if len(items) == 3 else '')
    body = ''.join('<div class="step"%s%s><span class="num">%02d</span><div><h3%s>%s</h3><p%s>%s</p></div></div>'
                   % ('' if compact else ' data-reveal style="--d:%dms"' % (k * 100), ei(ed, k), k + 1,
                      ea(ed, 'title'), esc(i.get('title', '')), ea(ed, 'text'), esc(i.get('text', '')))
                   for k, i in enumerate(items))
    return '<div class="steps%s"%s>%s%s</div>' % (cls, el(ed, lst, True, 'steps'), line, body)

def stat_value(v):
    return esc(html.unescape(str(v))).replace(' ', '&nbsp;').replace('\xa0', '&nbsp;')

def stats_html(ed=False):
    return '<div class="stats"%s>' % el(ed, 'items', True, 'stats') + ''.join(
        '<div class="stat" data-reveal style="--d:%dms"%s><b%s>%s</b><span%s>%s</span></div>'
        % (n * 60, ei(ed, k), ea(ed, 'value'), stat_value(i['value']), ea(ed, 'label'), esc(i.get('label', ''))) for n, (k, i) in enumerate(STATS_IX)) + '</div>'

def tagline_words(text):
    """Главная мысль по словам: *слова* — фирменным цветом, слова проявляются по очереди."""
    words, i = [], 0
    for seg in re.split(r'(\*[^*]+\*)', str(text or '')):
        acc = seg.startswith('*')
        for w in seg.strip('*').split():
            words.append('<span class="w%s" style="--i:%d">%s</span>' % (' acc' if acc else '', i, esc(w)))
            i += 1
    return ' '.join(words)

def clients_html(ed=False, b=None):
    logos = [l for l in (CLIENTS.get('logos') or []) if l.get('image')]
    if logos:
        def one(l):
            img = '<img src="%s" alt="%s" loading="lazy" decoding="async">' % (esc(media(l['image'])), esc(l.get('name', '')))
            return '<li>%s</li>' % (('<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(href(l['url'], '#')), img)) if l.get('url') else img)
        items = ''.join(one(l) for l in logos)
        while len(logos) < 6 and items.count('<li>') < 6:  # строка должна заполнять ширину экрана
            items += ''.join(one(l) for l in logos)
    else:  # логотипов пока нет — аккуратные места под них, чтобы было видно, как работает строка
        items = ''.join('<li class="ph">{{icon:image}}<span>Логотип клиента</span></li>' for _ in range(7))
    h_id = hid(b, 'cl-h') if b else 'cl-h'  # у копии блока свой id заголовка
    return ('<section class="clients" aria-labelledby="%s"><div class="wrap clients-head"><h2 class="clients-h" id="%s"%s>%s</h2></div>'
            '<div class="marquee"><div class="marquee-in"><ul>%s</ul><ul aria-hidden="true">%s</ul></div></div></section>'
            % (h_id, h_id, es(ed, 'clients') + ea(ed, 'title', fb='Наши клиенты'), esc(CLIENTS.get('title') or 'Наши клиенты'), items, items))

def who_html(cards, ed=False):
    out = []
    for k, w in enumerate(c for c in cards or [] if isinstance(c, dict)):
        out.append('<article class="card" data-reveal style="--d:%dms"%s><span class="n"%s>%s</span><h3 class="heading-6"%s>%s</h3><ul class="checks"%s>%s</ul>%s</article>'
                   % (k * 80, ei(ed), ea(ed, 'label'), esc(w.get('label', '')), ea(ed, 'title', 'accent'), accent(w.get('title', '')), el(ed, 'items'),
                      ''.join('<li%s>{{icon:check-circle}}<span%s>%s</span></li>' % (ei(ed), ea(ed, '.'), esc(t)) for t in w.get('items') or []),
                      '<a class="link-arrow link-acc" href="%s"><span%s>%s</span>{{icon:arrow-right}}</a>' % (esc(href(w.get('link'), BASE + 'uslugi/')), ea(ed, 'link_text'), esc(w['link_text'])) if w.get('link_text') else ''))
    return ''.join(out)

# основатель — свой файл content/founder.json (правится в конструкторе прямо на главной); в старых версиях лежал внутри home.json
F = jload('founder.json') or (HOME.get('founder') if isinstance(HOME.get('founder'), dict) else None) or {}
def founder_html(cta, ed=False):
    photo = media(F.get('photo')) or BASE + 'img/artem.webp'
    return ('<div class="founder"%s><div class="portrait" data-reveal><img src="%s" alt="%s" width="336" height="336" loading="lazy" decoding="async"%s>'
            '<span class="chip"><i class="dot"></i>Основатель компании</span></div><div data-reveal style="--d:100ms"><span class="chip"%s>%s</span>'
            '<h2 class="heading-2" style="margin-top:16px"%s>%s</h2><p class="lead" style="margin-top:8px"%s>%s</p><ul class="checks"%s>%s</ul>'
            '<div class="hero-cta">%s</div></div></div>'
            % (es(ed, 'founder'), esc(photo), esc('%s — %s' % (F.get('name', ''), F.get('role', ''))), ea(ed, 'photo') + (' data-img' if ed else ''),
               ea(ed, 'chip', fb='Кто ведёт ваш магазин'), esc(F.get('chip') or 'Кто ведёт ваш магазин'), ea(ed, 'name'), esc(F.get('name', '')), ea(ed, 'role'), esc(F.get('role', '')),
               el(ed, 'items'), ''.join('<li%s>{{icon:seal-check}}<span%s>%s</span></li>' % (ei(ed), ea(ed, '.'), esc(t)) for t in F.get('items') or []), cta))

def news_tag(n):
    """Метка материала: «Новость» или «Статья» и рубрика — «Статья · Реклама»."""
    return ' · '.join(x for x in (n['kind'], n['topic']) if x)

def news_cards(items):
    if not items:
        return '<div class="empty">{{icon:newspaper}}<p>Скоро здесь появятся новости и статьи.</p></div>'
    out = []
    for n in items:
        cover = ('<span class="nc-img"><img src="%s" alt="" loading="lazy" decoding="async"></span>' % esc(media(n['cover']))) if n['cover'] else \
                '<span class="nc-img nc-ph">%s</span>' % ('{{icon:play}}' if n['video'] else '{{icon:newspaper}}')
        out.append('<a class="news-card" href="{{base}}novosti/%s/" data-reveal data-fi data-kind="|%s|" data-topic="|%s|">%s<span class="nc-body">'
                   '<span class="nc-meta"><time datetime="%s">%s</time><span class="nc-tag">%s</span></span><b>%s</b><span>%s</span></span></a>'
                   % (n['slug'], esc(n['kind']), esc(n['topic']), cover, esc(n['date']), ru_date(n['date']), esc(news_tag(n)), esc(n['title']), esc(n['excerpt'])))
    return '<div class="news-grid%s">' % (' news-one' if len(out) == 1 else '') + ''.join(out) + '</div>'

NEWS_MAX = 6  # на главной — от 3 до 6 последних материалов списком заголовков
def news_count(d):
    try:
        return max(3, min(NEWS_MAX, int(d.get('count') or NEWS_MAX)))
    except (TypeError, ValueError):
        return NEWS_MAX

def news_list_html(items, ed=False, count=NEWS_MAX):
    """Список заголовков: дата, «Новость/Статья · рубрика», заголовок. В конструкторе — все шесть, лишние спрятаны (data-cap)."""
    if not items:
        return '<div class="empty">{{icon:newspaper}}<p>Скоро здесь появятся новости и статьи.</p></div>'
    rows = ''.join('<li%s%s><a class="nl-item" href="{{base}}novosti/%s/"><span class="nl-meta"><time datetime="%s">%s</time><span class="nl-tag">%s</span></span>'
                   '<b class="nl-title">%s</b>{{icon:arrow-right}}</a></li>'
                   % (' data-cap="%d"' % k if ed else '', ' hidden' if k >= count else '', n['slug'], esc(n['date']), ru_date(n['date']), esc(news_tag(n)), esc(n['title']))
                   for k, n in enumerate(items))
    return '<ol class="nlist" data-reveal>%s</ol>' % rows

def filter_bar(chips):
    """Кнопки фильтра над карточками: (ключ:значение, подпись). У карточек — data-fi и data-<ключ>="|значение|…|"; работает в site.js."""
    chips = [('', 'Все')] + chips
    if len(chips) < 2:
        return ''
    return '<div class="nfilter" role="group" aria-label="Что показать">%s</div>' % ''.join(
        '<button type="button" class="nf%s" data-nf="%s" aria-pressed="%s">%s</button>' % (' on' if not f else '', esc(f), 'true' if not f else 'false', esc(label)) for f, label in chips)

def news_filters(items):
    """«Все / Новости / Статьи / рубрики» — только если есть из чего выбирать."""
    kinds = [k for k in ('Новость', 'Статья') if any(n['kind'] == k for n in items)]
    topics = sorted({n['topic'] for n in items if n['topic']})
    return filter_bar(([('kind:Новость', 'Новости'), ('kind:Статья', 'Статьи')] if len(kinds) > 1 else []) + ([('topic:' + t, t) for t in topics] if len(topics) > 1 else []))

# ---------- кейсы: график из цифр, карточки, страница кейса ----------
def fmt_num(v):
    """300000 → «300 тыс», 1250000 → «1,25 млн», 12.5 → «12,5» — для подписей графика."""
    a = abs(v)
    s, u = (('%.2f' % (v / 1e9), ' млрд') if a >= 999.5e6 else ('%.2f' % (v / 1e6), ' млн') if a >= 999.5e3 else
            ('%.0f' % (v / 1e3), ' тыс') if a >= 1e4 else ('%.1f' % (v / 1e3), ' тыс') if a >= 1e3 else
            ('%.0f' % v, '') if a >= 100 else ('%.1f' % v, '') if a >= 10 else ('%.2f' % v, ''))
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s.replace('.', ',').replace('-', '\u2212') + u

_MON_RE = re.compile(r'\b(?:январ|феврал|март|апрел|июн|июл|август|сентябр|октябр|ноябр|декабр)[а-яё]*|\bма[йя]\b', re.I)
def short_label(s, size=12):
    """Подпись месяца под осью: «Сентябрь 2026» → «Сен 2026»; совсем длинная — с многоточием (полная — во всплывающей подсказке)."""
    s = str(s).strip()
    if len(s) > 10:
        s = _MON_RE.sub(lambda m: m.group(0)[:3], s)
    return s if len(s) <= size else s[:size - 1].rstrip() + '…'

def nice_top(m):
    """Верх шкалы — круглое число чуть больше максимума."""
    if m <= 0:
        return 1.0
    e = 10 ** math.floor(math.log10(m))
    return next(f * e for f in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10) if m <= f * e + 1e-9)

CHART = {  # ширина, высота, поля слева, справа, сверху, снизу и сколько подписей месяцев (0 — маленький график на карточке, без осей)
    # три размера под ширину экрана — подписи везде остаются читаемыми (11–15 px)
    'lg': (740, 340, 64, 28, 32, 42, 10), 'md': (560, 300, 60, 24, 30, 40, 7), 'sm': (360, 280, 54, 18, 30, 40, 4),
    'mini': (320, 200, 16, 16, 24, 20, 0)}
MP_COLORS = {'wb': ('#CB11AB', '#7B1FC4'), 'ozon': ('#005BFF', '#005BFF')}
MP_SOLID = {'wb': '#A116BE', 'ozon': '#005BFF'}  # мини-график на карточке — без градиентов: карточка может стоять на странице дважды

def chart_series(c):
    """Точки графика и линии площадок, у которых есть хотя бы две цифры."""
    pts = [p for p in (c['chart'] or {}).get('points') or [] if isinstance(p, dict) and str(p.get('label') or '').strip()]
    series = [(k, [to_num(p.get(k)) for p in pts]) for k in ('wb', 'ozon')]
    return pts, [(k, vals) for k, vals in series if sum(v is not None for v in vals) >= 2]

def chart_start(c, pts):
    """С какого месяца работаем мы: галочка у месяца (или его подпись в поле start)."""
    i = next((i for i, p in enumerate(pts) if p.get('start') is True), None)
    s = str((c['chart'] or {}).get('start') or '').strip().lower()
    if i is None and s:
        i = next((i for i, p in enumerate(pts) if str(p['label']).strip().lower() == s), None)
    return i

def chart_svg(c, uid, size='lg'):
    """Линии Wildberries (фирменный фиолетовый) и Ozon (синий) по точкам из админки; период «до нас» и отметка «Начали работу»."""
    pts, series = chart_series(c)
    if len(pts) < 2 or not series:
        return ''
    W, H, L, R, T, B, xn = CHART[size]
    n, bottom = len(pts), H - B
    vmax = max(v for _, vals in series for v in vals if v is not None)
    if vmax <= 0:  # одни нули — показывать нечего
        return ''
    top = nice_top(vmax)
    X = lambda i: L + (W - L - R) * i / (n - 1)
    Y = lambda v: T + (bottom - T) * (1 - min(max(v, 0), top) / top)
    used = [k for k, _ in series]
    out = [] if not xn else ['<defs>'] + ['<linearGradient id="s%s-%s" gradientUnits="userSpaceOnUse" x1="%d" y1="0" x2="%d" y2="0"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
                        '<linearGradient id="f%s-%s" gradientUnits="userSpaceOnUse" x1="0" y1="%d" x2="0" y2="%d"><stop offset="0" stop-color="%s" stop-opacity=".22"/><stop offset="1" stop-color="%s" stop-opacity="0"/></linearGradient>'
                        % (k, uid, L, W - R, c1, c2, k, uid, T, bottom, c2, c2) for k, (c1, c2) in MP_COLORS.items() if k in used] + ['</defs>']
    si = chart_start(c, pts)
    if si:  # до начала работы — чуть темнее
        out.append('<rect class="pre" x="%d" y="%d" width="%.1f" height="%d"/>' % (L, T, X(si) - L, bottom - T))
    if xn:
        for k in range(5):
            v = top * k / 4
            out.append('<line class="gl" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/><text class="yl" x="%d" y="%.1f">%s</text>' % (L, W - R, Y(v), Y(v), L - 8, Y(v) + 4, esc(fmt_num(v))))
        step = max(1, math.ceil(n / xn))
        xs = list(range(0, n, step))
        if n - 1 - xs[-1] >= max(2, step // 2 + 1):  # последний месяц подписываем, если не налезает на соседнюю подпись
            xs.append(n - 1)
        out += ['<text class="xl" x="%.1f" y="%d">%s</text>' % (X(i), H - 14, esc(short_label(pts[i]['label']))) for i in xs]
    if si is not None:
        out.append('<line class="st" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/>' % (X(si), X(si), T - (12 if xn else 0), bottom))
        if xn:
            right = si <= (n - 1) / 2
            out.append('<text class="stl" x="%.1f" y="%d"%s>Начали работу</text>' % (X(si) + (6 if right else -6), T - 4, '' if right else ' text-anchor="end"'))
    for k, vals in series:
        dots = [(i, v) for i, v in enumerate(vals) if v is not None]  # пустой месяц не рвёт линию: соединяем соседние цифры
        seg = [(X(i), Y(v)) for i, v in dots]
        d = 'M' + ' L'.join('%.1f %.1f' % p for p in seg)
        fill, stroke = ('url(#f%s-%s)' % (k, uid), 'url(#s%s-%s)' % (k, uid)) if xn else ('%s" fill-opacity=".14' % MP_SOLID[k], MP_SOLID[k])
        out.append('<path class="ar" d="%s L%.1f %d L%.1f %d Z" fill="%s"/><path class="ln" d="%s" pathLength="1" stroke="%s"/>'
                   % (d, seg[-1][0], bottom, seg[0][0], bottom, fill, d, stroke))
        if xn:
            out += ['<circle class="pt pt-%s" cx="%.1f" cy="%.1f" r="4"><title>%s, %s: %s</title></circle>' % (k, X(i), Y(v), MP[k], esc(str(pts[i]['label']).strip()), esc(fmt_num(v)))
                    for i, v in dots]
        else:
            out.append('<circle class="pt pt-%s" cx="%.1f" cy="%.1f" r="5"/>' % (k, X(dots[-1][0]), Y(dots[-1][1])))
    if not xn:  # на карточке график — картинка к заголовку, читать его отдельно не нужно
        return '<svg class="cchart cchart-mini" viewBox="0 0 %d %d" aria-hidden="true" focusable="false">%s</svg>' % (W, H, ''.join(out))
    vals_of = lambda vals: [v for v in vals if v is not None]
    label = '%s: %s' % (str((c['chart'] or {}).get('title') or 'Динамика продаж'),
                        '; '.join('%s — с %s до %s' % (MP[k], fmt_num(vals_of(vals)[0]), fmt_num(vals_of(vals)[-1])) for k, vals in series))
    return '<svg class="cchart cchart-%s" viewBox="0 0 %d %d" role="img" aria-label="%s" focusable="false">%s</svg>' % (size, W, H, esc(label), ''.join(out))

def chart_block(c):
    """График на странице кейса: заголовок и легенда, два размера (компьютер и телефон) и таблица цифр для экранного чтеца."""
    uid = 'c-' + c['slug']
    big = chart_svg(c, uid)
    if not big:
        return ''
    pts, series = chart_series(c)
    title = str((c['chart'] or {}).get('title') or 'Динамика продаж')
    rows = ''.join('<tr><th scope="row">%s</th>%s</tr>' % (esc(str(p['label']).strip()), ''.join('<td>%s</td>' % (esc(fmt_num(vals[i])) if vals[i] is not None else '—') for _, vals in series))
                   for i, p in enumerate(pts))
    table = '<table class="visually-hidden"><caption>%s</caption><tr><th scope="col">Месяц</th>%s</tr>%s</table>' % (esc(title), ''.join('<th scope="col">%s</th>' % MP[k] for k, _ in series), rows)
    return ('<figure class="cchart-box" data-reveal><figcaption><b>%s</b><span class="cc-legend">%s</span></figcaption>%s%s%s</figure>'
            % (esc(title), ''.join('<span class="lg lg-%s">%s</span>' % (k, MP[k]) for k, _ in series), big,
               chart_svg(c, uid + '-m', 'md') + chart_svg(c, uid + '-s', 'sm'), table))

def mp_badges(c):
    return ''.join('<span class="mpb mpb-%s">%s</span>' % (k, MP[k]) for k in c['mp'])

def growth(before, after, label=''):
    """Было 300 000 → стало 1 200 000: «×4»; 100 → 140: «+40%». Позицию и место не считаем: там меньше — значит лучше."""
    if re.search(r'топ|позиц|мест', '%s %s %s' % (label, before, after), re.I):
        return ''
    b, a = to_num(before), to_num(after)
    if b is None or a is None or b <= 0:
        return ''
    r = a / b
    if r >= 2:
        return '×' + ('%.1f' % r).rstrip('0').rstrip('.').replace('.', ',')
    p = (r - 1) * 100
    return ('+' if p >= 0 else '−') + '%.0f%%' % abs(p)

def case_card(c, k=0, ed=False, hide=False):
    """Карточка кейса: мини-график (нет графика — обложка), площадки, ниша, заголовок и главная цифра."""
    viz = chart_svg(c, 'm-' + c['slug'], 'mini')
    pic = ('<span class="cc-viz">%s</span>' % viz if viz else
           '<span class="cc-img"><img src="%s" alt="" loading="lazy" decoding="async"></span>' % esc(media(c['cover'])) if c['cover'] else
           '<span class="cc-img cc-ph">{{icon:chart-line-up}}</span>')
    big = c['results'][0] if c['results'] else None
    return ('<a class="case-card" href="{{base}}keysy/%s/" data-reveal data-fi data-mp="|%s|" data-svc="|%s|"%s%s>%s<span class="cc-body">'
            '<span class="cc-tags">%s%s</span><b class="cc-title">%s</b>%s</span></a>'
            % (c['slug'], '|'.join(c['mp']), '|'.join(esc(s) for s in c['services']),
               ' data-cap="%d"' % k if ed else '', ' hidden' if hide else '', pic, mp_badges(c),
               '<span class="cc-niche">%s</span>' % esc(c['niche']) if c['niche'] else '', esc(c['title']),
               '<span class="cc-res"><strong>%s</strong><span>%s</span></span>' % (esc(big['value']), esc(big.get('label') or '')) if big else
               '<span class="cc-ex">%s</span>' % esc(c['excerpt']) if c['excerpt'] else ''))

def case_filters(items):
    mps = [k for k in ('wb', 'ozon') if any(k in c['mp'] for c in items)]
    svcs = [s for s in SERVICES if any(s['slug'] in c['services'] for c in items)]
    return filter_bar(([('mp:' + k, MP[k]) for k in mps] if len(mps) > 1 else []) + ([('svc:' + s['slug'], s['title']) for s in svcs] if len(svcs) > 1 else []))

def cell(x):
    return esc(str(x).strip()) if x is not None and str(x).strip() else '—'

def case_page(c):
    nums = ''.join('<li><b>%s</b><span>%s</span></li>' % (esc(r.get('value', '')), esc(r.get('label', ''))) for r in c['results'])
    metrics = ''.join('<tr><th scope="row">%s</th><td>%s</td><td>%s</td><td class="mg">%s</td></tr>'
                      % (esc(m.get('label', '')), cell(m.get('before')), cell(m.get('after')),
                         esc(str(m.get('change') or '').strip() or growth(m.get('before'), m.get('after'), m.get('label', '')))) for m in c['metrics'])
    shots = ''.join('<figure class="shot"><a href="%s" target="_blank" rel="noopener"><img src="%s" alt="%s" loading="lazy" decoding="async"></a>%s</figure>'
                    % (esc(media(s['image'])), esc(media(s['image'])), esc(s.get('caption') or 'Скриншот из кабинета'), '<figcaption>%s</figcaption>' % esc(s['caption']) if s.get('caption') else '')
                    for s in c['shots'])
    svc_links = ''.join('<a class="chip" href="%s">%s</a>' % ('{{base}}sait/' if s == 'sait' else '{{base}}uslugi/%s/' % s, esc(BY_SLUG[s]['title'])) for s in c['services'] if s in BY_SLUG)
    more = [x for x in CASES if x['slug'] != c['slug']][:3]
    body = ''.join(x for x in (
        '<figure class="case-cover"><img src="%s" alt="" decoding="async"></figure>' % esc(media(c['cover'])) if c['cover'] else '',
        '<ul class="case-nums case-nums-lg" data-reveal>%s</ul>' % nums if nums else '',
        chart_block(c),
        '<div class="mtable" data-reveal><table><thead><tr><th scope="col">Показатель</th><th scope="col">Было</th><th scope="col">Стало</th><th scope="col">Изменение</th></tr></thead><tbody>%s</tbody></table></div>' % metrics if metrics else '',
        '<div class="card case-story" data-reveal><h2 class="heading-5">Что сделали</h2><div class="prose">%s</div></div>' % md(c['text']) if c['text'].strip() else '',
        '<div class="case-shots" data-reveal><h2 class="heading-5">Скриншоты из кабинета</h2><div class="shots">%s</div></div>' % shots if shots else '',
        '<div class="video-box" data-reveal>%s</div>' % video_html(c['video'], c['cover']) if c['video'] else '',
        '<div class="case-svcs" data-reveal><span>Услуги в этом кейсе:</span>%s</div>' % svc_links if svc_links else ''))
    return ('<section class="phero">{{phero-bg}}<div class="wrap narrow">%s<div class="np-meta">%s%s%s</div><h1 class="heading-2 grad">%s</h1>%s</div></section>'
            % (crumbs(('Кейсы', '{{base}}keysy/'), (c['title'], None)), ''.join('<span class="chip mpc mpc-%s">%s</span>' % (k, MP[k]) for k in c['mp']),
               '<span class="chip">%s</span>' % esc(c['niche']) if c['niche'] else '', '<span class="chip">%s</span>' % esc(c['period']) if c['period'] else '',
               esc(c['title']), '<p class="lead">%s</p>' % esc(c['excerpt']) if c['excerpt'] else '')
            + '<section class="sec sec-tight"><div class="wrap narrow"><div class="case-page">%s</div>'
              '<a class="link-arrow link-acc" href="{{base}}keysy/" style="margin-top:40px"><span class="flip">{{icon:arrow-right}}</span><span>Все кейсы</span></a></div></section>' % body
            + ('<section class="sec" style="padding-top:0"><div class="wrap"><h2 class="heading-5">Другие кейсы</h2><div class="case-grid" style="margin-top:24px">%s</div></div></section>'
               % ''.join(case_card(x, k) for k, x in enumerate(more)) if more else '')
            + cta_band('Хотите такой же результат?', 'Разберём ваш магазин на бесплатной консультации и покажем, где точки роста.'))

def svc_cases_html(s):
    """Кейсы на странице услуги: из раздела «Кейсы» (с этой услугой) и старые — из самой услуги."""
    own = [c for c in CASES if s['slug'] in c['services']]
    legacy = [c for c in (s.get('cases') or []) if c.get('title')]
    if not own:
        return cases_html(s)
    return ('<div class="case-grid">%s</div>' % ''.join(case_card(c, k) for k, c in enumerate(own[:6]))
            + ('<a class="link-arrow link-acc" href="{{base}}keysy/" style="margin-top:24px"><span>Все кейсы</span>{{icon:arrow-right}}</a>' if len(own) > 6 else '')
            + ('<div style="margin-top:24px">%s</div>' % cases_html(s) if legacy else ''))

def hero_title(raw):
    t = esc(raw or '')
    t = re.sub(r'(^|\s)(\S{1,2}) (?=\[)', lambda m: m.group(1) + m.group(2) + '&nbsp;', t)  # «на», «и», «в» не висят в конце строки
    t = t.replace('[WB]', '<span class="mk mk-wb">Wildberries</span>').replace('[OZON]', '<span class="mk mk-ozon">Ozon</span>')
    return re.sub(r'\[([^\]]+)\]', r'<span class="lead-word">\1</span>', t)

def hero_stats(ed=False):
    return ''.join('<div class="num"%s><b%s>%s</b><span%s>%s</span></div>' % (ei(ed, k), ea(ed, 'value'), stat_value(i['value']), ea(ed, 'label'), esc(i.get('label', '')))
                   for k, i in STATS_IX[:2])

def video_card(ed=False):
    """Видео-визитка на первом экране. Пока видео нет — обложка «скоро» с фото основателя."""
    url, poster = VIDEO.get('url') or S.get('video_url', ''), VIDEO.get('poster') or S.get('video_poster', '')
    cap = esc(VIDEO.get('caption') or S.get('video_caption') or 'Видео-визитка основателя')
    who = esc('%s · %s' % (F.get('name', ''), 'основатель компании'))
    face = media(F.get('photo')) or BASE + 'img/artem.webp'
    bg = ('<img class="vc-poster" src="%s" alt="" decoding="async" fetchpriority="high">' % esc(media(poster))) if poster else \
         ('<span class="vc-rings" aria-hidden="true"></span><span class="vc-face"><img src="%s" alt="" width="336" height="336" decoding="async"%s></span>'
          % (esc(face), es(ed, 'founder') + ea(ed, 'photo') + (' data-img' if ed else '')))
    body = '%s<span class="vplay" aria-hidden="true"><i></i>{{icon:play}}</span><span class="vcap"><b%s>%s</b><span>%s</span></span>' % (bg, es(ed, 'video') + ea(ed, 'caption', fb=S.get('video_caption') or 'Видео-визитка основателя'), cap, who)
    if url:
        return ('<button class="vcard%s" type="button" data-video aria-label="Смотреть: %s">%s</button><template id="video-tpl">%s</template>'
                % (' has-poster' if poster else '', cap, body, video_html(url, poster, autoplay=True)))
    return '<div class="vcard vcard-soon" role="img" aria-label="%s — скоро">%s<span class="vsoon">Скоро здесь</span></div>' % (cap, body)

DOC_SLUGS = {d['slug'] for d in DOCS}
def doc_url(slug):
    if slug in DOC_SLUGS:
        return BASE + 'dokumenty/%s/' % slug
    warn('нет документа «%s» — ссылка у галочки согласия ведёт на список документов' % slug)
    return BASE + 'dokumenty/'

def consents(prefix):
    return ('<label class="check"><input type="checkbox" id="%s-pd" name="consent_pd" required><span class="box">{{icon:check}}</span><span>Согласен на <a href="%s" target="_blank">обработку персональных данных</a> и принимаю <a href="%s" target="_blank">политику конфиденциальности</a> <b class="req">*</b></span></label>'
            '<label class="check"><input type="checkbox" id="%s-ads" name="consent_ads"><span class="box">{{icon:check}}</span><span>Согласен получать <a href="%s" target="_blank">индивидуальные предложения</a></span></label>' % (prefix, doc_url('soglasie-pd'), doc_url('politika'), prefix, doc_url('soglasie-reklama')))

def cases_html(s):
    cases = [c for c in (s.get('cases') or []) if c.get('title')]
    if not cases:
        return ('<div class="empty empty-cases"><span class="sk" aria-hidden="true"><i></i><i></i><i></i></span>{{icon:chart-line-up}}'
                '<p>Кейсы по этой услуге скоро появятся здесь: фото, видео и результаты продвижения.</p></div>')
    out = []
    for c in cases:
        if c.get('video'):
            m = '<div class="video-box">%s</div>' % video_html(c['video'], c.get('image'))
        elif c.get('image'):
            m = '<img src="%s" alt="" loading="lazy" decoding="async">' % esc(media(c['image']))
        else:
            m = ''
        res = ''.join('<li><b>%s</b><span>%s</span></li>' % (esc(r.get('value', '')), esc(r.get('label', ''))) for r in (c.get('results') or []) if r.get('value'))
        out.append('<article class="case" data-reveal>%s<div class="case-body"><h3>%s</h3>%s%s<div class="case-text prose">%s</div></div></article>'
                   % ('<div class="case-media">%s</div>' % m if m else '', esc(c['title']),
                      '<p class="case-res">%s</p>' % esc(c['result']) if c.get('result') else '',
                      '<ul class="case-nums">%s</ul>' % res if res else '', md(c.get('text', ''))))
    return '<div class="cases">' + ''.join(out) + '</div>'

def cta_band(title=None, text=None, button=None, ed=False, link=None):
    """Тёмная плашка с кнопкой: по умолчанию — окно записи; link — своя страница (например brief/)."""
    t = TX.get('cta') or {}
    btn = button or t.get('button') or 'Записаться'
    return ('<section class="sec" aria-label="%s"><div class="wrap"><div class="cta-band" data-reveal>'
            '<div><h2 class="heading-3"%s>%s</h2><p%s>%s</p></div>'
            '<div class="hero-cta"><a class="btn btn-primary btn-lg btn-shine" href="%s"%s><span%s>%s</span>{{icon:arrow-right}}</a></div></div></div></section>'
            % (esc(btn) if link else 'Бесплатная консультация',
               ea(ed, 'title', fb=t.get('title') or 'Начните с бесплатной консультации'), esc(title or t.get('title') or 'Начните с бесплатной консультации'),
               ea(ed, 'text', fb=t.get('text') or ''), esc(text or t.get('text') or ''),
               '{{base}}' + link if link else '{{base}}kontakty/', '' if link else ' data-lead',
               ea(ed, 'button', fb=t.get('button') or 'Записаться'), esc(btn)))

OPTIONS = '<option value="">Пока не знаю</option>' + ''.join('<option value="%s">%s</option>' % (s['slug'], esc(s['title'])) for s in SERVICES)

def service_body(s):
    slug = s['slug']
    others = ''.join('<a href="%s">%s%s</a>' % ('{{base}}sait/' if o['slug'] == 'sait' else '{{base}}uslugi/%s/' % o['slug'], icon(o.get('icon')), esc(o['title']))
                     for o in SERVICES if o['slug'] != slug)
    lead = '<a class="btn btn-primary%s" href="{{base}}kontakty/?usluga=%s" data-lead data-service="%s"><span>%s</span>{{icon:arrow-right}}</a>'
    return (
        '<section class="phero" aria-labelledby="ph">{{phero-bg}}<div class="wrap phero-grid"><div>' + crumbs(('Услуги', '{{base}}uslugi/'), (s['title'], None)) +
        '<span class="chip chip-accent">%sУслуга</span><h1 class="heading-1 grad" id="ph">%s</h1><p class="lead">%s</p>' % (icon(s.get('icon')), esc(s['title']), esc(s.get('short', ''))) +
        '<div class="price-row">%s</div><div class="hero-cta">' % price_html(s, 'price-lg') + lead % (' btn-lg btn-shine', slug, slug, 'Обсудить на консультации') + '</div></div>'
        '<div class="phero-viz" data-play aria-hidden="true"><div class="viz">%s</div></div></div></section>' % VIZ.get(slug, '') +
        '<section class="sec" style="padding-top:32px" aria-label="Подробно об услуге"><div class="wrap"><div class="svc-layout"><div>'
        '<div class="card"><h2 class="heading-5">Что входит</h2><ul class="checks">' + ''.join('<li>{{icon:check-circle}}<span>%s</span></li>' % esc(t) for t in s.get('items') or []) + '</ul></div>'
        '<div class="card" style="margin-top:16px"><h2 class="heading-5">Как проходит работа</h2>' + steps_html(STEPS.get('items') or [], compact=True) + '</div></div>'
        '<aside class="aside-cta" aria-labelledby="aside-h"><span class="ic">{{icon:calendar-check}}</span><h2 class="heading-6" id="aside-h">Обсудим вашу задачу</h2>'
        '<p>Бесплатная онлайн-встреча с аналитиком: разберём магазин и подскажем, с чего начать.</p><div class="aside-price">Стоимость %s</div>' % price_html(s) +
        lead % (' btn-shine', slug, slug, 'Записаться на консультацию') + '<a class="tel" href="tel:{{phone_href}}">{{icon:phone}}{{phone}}</a></aside></div>'
        '<div class="sec-head" style="margin-top:80px" data-reveal><span class="chip">Кейсы</span><h2 class="heading-3" style="margin-top:16px">Результаты по услуге «%s»</h2></div>' % esc(s['title']) +
        '<div style="margin-top:32px">' + svc_cases_html(s) + '</div>'
        '<h2 class="heading-5" style="margin-top:64px">Другие услуги</h2><div class="others">' + others + '</div></div></section>' + cta_band())

# «Сайт для селлера» — своя страница sait/: цена и кейсы из админки показываются на ней, только когда заполнены
SAIT = next((s for s in SERVICES if s['slug'] == 'sait'), None)

def sait_price():
    return '<div class="price-row">%s</div>' % price_html(SAIT, 'price-lg') if SAIT and price_value(SAIT) else ''


def block_html(b):
    """Блоки страниц, собранных в админке (раздел «Страницы»)."""
    t = b.get('type')
    if t == 'hero':
        btn = '<div class="hero-cta"><a class="btn btn-primary btn-lg btn-shine" href="%s"%s><span>%s</span>{{icon:arrow-right}}</a></div>' % (
            esc(href(b.get('button_link'))), '' if b.get('button_link') else ' data-lead', esc(b['button'])) if b.get('button') else ''
        img = '<div class="phero-img"><img src="%s" alt="" decoding="async"></div>' % esc(media(b['image'])) if b.get('image') else ''
        return ('<section class="phero"><div class="wrap%s"><div>%s<h1 class="heading-1 grad">%s</h1>%s%s</div>%s</div></section>'
                % (' phero-grid' if img else '', '<span class="chip chip-accent">%s</span>' % esc(b['chip']) if b.get('chip') else '',
                   accent(b.get('title', '')), '<p class="lead">%s</p>' % esc(b['text']) if b.get('text') else '', btn, img))
    if t == 'text':
        return '<section class="sec sec-tight"><div class="wrap narrow prose">%s%s</div></section>' % ('<h2>%s</h2>' % esc(b['title']) if b.get('title') else '', md(b.get('body', '')))
    if t == 'image':
        return ('<section class="sec sec-tight"><div class="wrap"><figure class="figure"><img src="%s" alt="%s" loading="lazy" decoding="async">%s</figure></div></section>'
                % (esc(media(b.get('image'))), esc(b.get('caption', '')), '<figcaption>%s</figcaption>' % esc(b['caption']) if b.get('caption') else ''))
    if t == 'video':
        return '<section class="sec sec-tight"><div class="wrap narrow"><div class="video-box">%s</div></div></section>' % video_html(b.get('url'), b.get('poster'))
    if t == 'services':
        return '<section class="sec"><div class="wrap"><div class="bento">%s</div></div></section>' % bento_html()
    if t == 'faq':
        return '<section class="sec"><div class="wrap"><div class="faq" style="max-width:880px">%s</div></div></section>' % faq_html(FAQ)
    if t == 'clients':
        return clients_html()
    if t == 'stats':
        return '<section class="sec sec-tight"><div class="wrap">%s</div></section>' % stats_html()
    if t == 'steps':
        return '<section class="sec"><div class="wrap">%s</div></section>' % steps_html(STEPS.get('items') or [])
    if t == 'news':
        return '<section class="sec"><div class="wrap">%s</div></section>' % news_cards(NEWS[:3])
    if t == 'cta':
        return cta_band(b.get('title'), b.get('text'), b.get('button'))
    return ''

# ---------- конструктор: страница из блоков (сейчас — главная). Блок: {id, type, data, style, hidden} ----------
# Сайт собирается дважды: обычная страница и версия для редактора admin/edit/ — с пометками полей и скрытыми блоками.
BG = {'page': 'var(--bg)', 'alt': 'var(--bg2)', 'white': 'var(--s1)', 'mint': '#E7F2EB', 'sand': '#F5EFE3'}

def hid(b, base):
    """id заголовка блока: у копии блока свой, чтобы на странице не было двух одинаковых."""
    return base if b['id'] == b['type'] else '%s-%s' % (base, b['id'])

def head_html(b, d, ed, h_id, chip_default='', title_default='', link=None):
    """Шапка секции: чип и заголовок; link — ссылка справа («Все услуги»)."""
    head = '<div class="sec-head"%s><span class="chip"%s>%s</span><h2 class="heading-2" id="%s"%s>%s</h2></div>' % (
        '' if link else ' data-reveal', ea(ed, 'chip', fb=chip_default), esc(d.get('chip') or chip_default), hid(b, h_id),
        ea(ed, 'title', fb=title_default), esc(d.get('title') or title_default))
    if link:
        return '<div class="sec-head-row" data-reveal>%s<a class="link-arrow" href="%s"><span>%s</span>{{icon:arrow-right}}</a></div>' % (head, link[0], link[1])
    return head

def blk_hero(b, d, ed):
    chip = '<span%s>%s</span>' % (ea(ed, 'chip'), esc(d.get('chip', ''))) if ed else esc(d.get('chip', ''))
    return ('<section class="hero" aria-labelledby="%s"><div class="grid-bg" aria-hidden="true"></div><div class="glow glow-a" aria-hidden="true"></div>'
            '<div class="glow glow-b" aria-hidden="true"></div><div class="wrap hero-grid"><div class="hero-copy">'
            '<span class="chip hi-in"><i class="dot"></i>%s</span><h1 class="display hi-in" id="%s" style="--d:60ms"%s>%s</h1>'
            '<p class="lead hi-in" style="--d:120ms"%s>%s</p><div class="hero-cta hi-in" style="--d:180ms">'
            '<a class="btn btn-primary btn-lg btn-shine" href="{{base}}kontakty/" data-lead><span%s>%s</span>{{icon:arrow-right}}</a>'
            '<a class="link-arrow" href="{{base}}uslugi/"><span>Все услуги</span>{{icon:arrow-right}}</a></div>'
            '<div class="trust hi-in" style="--d:240ms"%s>%s</div></div><div class="hero-art hi-in" style="--d:140ms">%s</div></div></section>'
            % (hid(b, 'hero-h'), chip, hid(b, 'hero-h'), ea(ed, 'title', 'hero'), hero_title(d.get('title')), ea(ed, 'lead'), esc(d.get('lead', '')),
               ea(ed, 'button', fb='Получить бесплатную консультацию'), esc(d.get('button') or 'Получить бесплатную консультацию'),
               el(ed, 'items', True, 'stats'), hero_stats(ed), video_card(ed)))

def blk_who(b, d, ed):
    return ('<section class="sec" aria-labelledby="%s"><div class="wrap">%s<div class="who"%s>%s</div></div></section>'
            % (hid(b, 'who-h'), head_html(b, d, ed, 'who-h'), el(ed, 'cards'), who_html(d.get('cards'), ed)))

def blk_services(b, d, ed):
    return ('<section class="sec sec-alt" aria-labelledby="%s"><div class="wrap">%s<div class="bento bento-scroll"%s>%s</div>'
            '<p class="swipe-hint">{{icon:arrow-right}}Листайте карточки</p></div></section>'
            % (hid(b, 'svc-h'), head_html(b, d, ed, 'svc-h', link=('{{base}}uslugi/', 'Все услуги')), el(ed, 'services', True, 'services'), bento_html(ed)))

def blk_stats(b, d, ed):
    return ('<section class="sec sec-tight" aria-labelledby="%s"><div class="wrap"><h2 class="visually-hidden" id="%s">Опыт в цифрах</h2>%s</div></section>'
            % (hid(b, 'num-h'), hid(b, 'num-h'), stats_html(ed)))

def blk_tagline(b, d, ed):
    return '<section class="tagline" aria-label="Наш подход"><div class="wrap"><p%s>%s</p></div></section>' % (ea(ed, 'text', 'tagline'), tagline_words(d.get('text')))

def blk_founder(b, d, ed):
    """cta: about — кнопка «О компании» (главная), lead — запись на консультацию (страница «О компании»); tight — меньше отступы."""
    cta = ('<a class="btn btn-primary btn-shine" href="{{base}}kontakty/" data-lead><span>Получить бесплатную консультацию</span>{{icon:arrow-right}}</a>'
           if d.get('cta') == 'lead' else '<a class="btn btn-ghost" href="{{base}}o-nas/"><span>О компании</span>{{icon:arrow-right}}</a>')
    return '<section class="sec%s" aria-label="Основатель компании"><div class="wrap">%s</div></section>' % (' sec-tight' if d.get('tight') else '', founder_html(cta, ed))

def blk_news(b, d, ed):
    n = news_count(d)
    return ('<section class="sec sec-alt" aria-labelledby="%s"><div class="wrap">%s<div style="margin-top:40px">%s</div></div></section>'
            % (hid(b, 'news-h'), head_html(b, d, ed, 'news-h', link=('{{base}}novosti/', 'Все новости и статьи')),
               news_list_html(NEWS[:NEWS_MAX] if ed else NEWS[:n], ed, n)))

def blk_steps(b, d, ed):
    """list: items — «Как мы работаем», site — «Как начать» (шаги заказа сайта)."""
    site = d.get('list') == 'site'
    h = 'start-h' if site else 'how-h'
    return ('<section class="sec" aria-labelledby="%s"><div class="wrap">%s%s</div></section>'
            % (hid(b, h), head_html(b, d, ed, h, 'Как начать' if site else 'Как мы работаем',
                                    'Три шага до своего магазина' if site else 'Четыре шага от первой встречи до стабильного роста'),
               steps_html(STEPS.get('site' if site else 'items') or [], ed=ed, lst='site' if site else 'items')))

def blk_faq(b, d, ed):
    """topic: site — вопросы о сайте (без ссылки «Все вопросы»), иначе — первые шесть общих."""
    site = d.get('topic') == 'site'
    h = 'sfaq-h' if site else 'hfaq-h'
    items = [i for i in FAQ if i.get('topic') == 'site'] if site else [i for i in FAQ if i.get('topic') != 'site'][:6]
    return ('<section class="sec" aria-labelledby="%s"><div class="wrap">%s<div class="faq" style="margin-top:40px;max-width:880px">%s</div></div></section>'
            % (hid(b, h), head_html(b, d, ed, h, 'Вопрос — ответ', 'Частые вопросы о сайте' if site else 'Частые вопросы',
                                    None if site else ('{{base}}voprosy/', 'Все вопросы')), faq_html(items)))

def blk_cta(b, d, ed):
    link = re.sub(r'[^a-z0-9/_-]', '', str(d.get('link') or '')) or None
    return cta_band(d.get('title'), d.get('text'), d.get('button'), ed, link)

# ---------- блоки остальных страниц: «Услуги», «Сайт для селлера», «О компании», «Вопросы», «Контакты», «Новости» ----------
CTX = {'crumb': None}  # подпись страницы в «хлебных крошках»; ставится, пока собирается страница

def chip_html(text, ed, accent=False, badge=None):
    if accent:  # зелёная метка: с точкой или с плашкой «НОВОЕ»
        first = '<span class="badge-new"%s>%s</span>' % (ea(ed, 'badge'), esc(badge)) if badge is not None else '<i class="dot"></i>'
        return '<span class="chip chip-accent">%s%s</span>' % (first, '<span%s>%s</span>' % (ea(ed, 'chip'), esc(text)) if ed else esc(text))
    return '<span class="chip"%s>%s</span>' % (ea(ed, 'chip'), esc(text))

def crumbs_here():
    return crumbs((CTX['crumb'], None)) if CTX['crumb'] else ''

def blk_phero(b, d, ed):
    return ('<section class="phero" aria-labelledby="%s">{{phero-bg}}<div class="wrap">%s%s<h1 class="heading-1 grad" id="%s"%s>%s</h1><p class="lead"%s>%s</p></div></section>'
            % (hid(b, 'ph'), crumbs_here(), chip_html(d.get('chip', ''), ed, d.get('accent')), hid(b, 'ph'), ea(ed, 'title'), esc(d.get('title', '')),
               ea(ed, 'lead'), esc(d.get('lead', ''))))

SAIT_HERO = {'badge': 'НОВОЕ', 'chip': 'Сайт для селлера', 'title': 'Свой сайт — продажи без комиссии маркетплейса',
             'lead': 'Покупатели с Wildberries и Ozon возвращаются к вам напрямую: свой магазин, свои цены и своя база клиентов. Делаем вместе с партнёром — командой OS Ecom.',
             'button': 'Заполнить бриф — 5 минут', 'link_text': 'Наши сайты'}
def blk_sait_hero(b, d, ed):
    return ('<section class="phero" aria-labelledby="%s">{{phero-bg}}<div class="wrap phero-grid"><div>%s%s<h1 class="heading-1 grad" id="%s"%s>%s</h1>'
            '<p class="lead"%s>%s</p>{{sait-price}}<div class="hero-cta"><a class="btn btn-primary btn-lg btn-shine" href="{{base}}brief/"><span%s>%s</span>{{icon:arrow-right}}</a>'
            '<a class="link-arrow" href="#portfolio"><span%s>%s</span>{{icon:arrow-right}}</a></div></div>'
            '<div class="phero-viz phero-viz-sait" data-play aria-hidden="true"><div class="viz">{{viz:sait}}</div></div></div></section>'
            % (hid(b, 'ph'), crumbs_here(), chip_html(d.get('chip', ''), ed, True, d.get('badge') or ''), hid(b, 'ph'), ea(ed, 'title'), esc(d.get('title', '')),
               ea(ed, 'lead'), esc(d.get('lead', '')), ea(ed, 'button', fb=SAIT_HERO['button']), esc(d.get('button') or SAIT_HERO['button']),
               ea(ed, 'link_text', fb=SAIT_HERO['link_text']), esc(d.get('link_text') or SAIT_HERO['link_text'])))

def blk_services_all(b, d, ed):
    return ('<section class="sec sec-tight" aria-label="Список услуг"><div class="wrap"><div class="bento" style="margin-top:0"%s>%s</div></div></section>'
            % (el(ed, 'services', True, 'services'), bento_html(ed)))

SAIT_FEATS = [('browser', 'Админ-панель', 'Полностью редактируете все карточки: фото, тексты, цены, наличие'),
              ('chart-line-up', 'Статистика и Метрика', 'Аналитика в админке и Яндекс Метрика с Вебвизором'),
              ('magnifying-glass', 'Индексация в поиске', 'Все страницы в Яндексе и Google — сайт находят в поиске'),
              ('storefront', 'Личный кабинет', 'Заказы, статусы и бонусы покупателя'),
              ('truck', 'Доставка и оплата', 'СДЭК, Яндекс и другие службы, онлайн-оплата и СБП'),
              ('telegram-logo', 'Заказы в Телеграм', 'Каждый заказ сразу приходит на почту и в Телеграм')]
def blk_features(b, d, ed):
    items = ''.join('<div class="feat" data-reveal%s%s><span class="ic">%s</span><div><b%s>%s</b><span%s>%s</span></div></div>'
                    % (' style="--d:%dms"' % (k % 3 * 60) if k % 3 else '', ei(ed), icon(f.get('icon')), ea(ed, 'title'), esc(f.get('title', '')), ea(ed, 'text'), esc(f.get('text', '')))
                    for k, f in enumerate(x for x in d.get('items') or [] if isinstance(x, dict)))
    return ('<section class="sec sec-tight" aria-labelledby="%s"><div class="wrap">%s<div class="feats"%s>%s</div></div></section>'
            % (hid(b, 'feat-h'), head_html(b, d, ed, 'feat-h', 'Что будет на сайте', 'Всё для продаж — уже внутри'), el(ed, 'items'), items))

def blk_why(b, d, ed):
    items = ''.join('<div class="card" data-reveal style="--d:%dms"%s><span class="ic">%s</span><p%s>%s</p></div>' % (k * 60, ei(ed), icon(w.get('icon')), ea(ed, 'text'), esc(w.get('text', '')))
                    for k, w in enumerate(x for x in d.get('items') or [] if isinstance(x, dict)))
    return ('<section class="sec" aria-labelledby="%s"><div class="wrap">%s<div class="why"%s>%s</div></div></section>'
            % (hid(b, 'why-h'), head_html(b, d, ed, 'why-h', 'Почему мы', 'За вашим магазином — целая команда'), el(ed, 'items'), items))

PORTFOLIO = ('Портфолио', 'Наши сайты', 'Работающий магазин электроники и три демо-сайта для разных ниш. Нажмите, чтобы открыть сайт.')
def blk_portfolio(b, d, ed):
    return ('<section class="sec" id="%s" aria-labelledby="%s"><div class="wrap"><div class="sec-head" data-reveal><span class="chip"%s>%s</span>'
            '<h2 class="heading-2" id="%s"%s>%s</h2><p%s>%s</p></div><div style="margin-top:40px">{{proj-feature}}</div>{{demos}}</div></section>'
            % (hid(b, 'portfolio'), hid(b, 'ex-h'), ea(ed, 'chip', fb=PORTFOLIO[0]), esc(d.get('chip') or PORTFOLIO[0]), hid(b, 'ex-h'),
               ea(ed, 'title', fb=PORTFOLIO[1]), esc(d.get('title') or PORTFOLIO[1]), ea(ed, 'text', fb=PORTFOLIO[2]), esc(d.get('text') or PORTFOLIO[2])))

def blk_cases(b, d, ed):
    """Кейсы одной услуги: из раздела «Кейсы» (где отмечена услуга) и простые — из самой услуги; пока их нет — на сайте блока нет, в конструкторе заглушка."""
    s = BY_SLUG.get(d.get('service') or 'sait')
    if s and (any(s['slug'] in c['services'] for c in CASES) or [c for c in (s.get('cases') or []) if c.get('title')]):
        return ('<section class="sec" aria-labelledby="%s"><div class="wrap"><div class="sec-head" data-reveal><span class="chip">Кейсы</span>'
                '<h2 class="heading-2" id="%s">Результаты по услуге «%s»</h2></div><div style="margin-top:40px">%s</div></div></section>'
                % (hid(b, 'scase-h'), hid(b, 'scase-h'), esc(s['title']), svc_cases_html(s)))
    if ed:
        return ('<section class="sec sec-tight" aria-label="Кейсы"><div class="wrap"><div class="empty">{{icon:chart-line-up}}'
                '<p>Кейсы услуги «%s» появятся здесь, когда их добавят в «Разделах»: «Кейсы» (в кейсе отметьте эту услугу).</p></div></div></section>' % esc(s['title'] if s else ''))
    return ''

CASES_MAX = 9  # на главной — последние 3, 6 или 9 кейсов
def cases_count(d):
    try:
        return max(3, min(CASES_MAX, int(d.get('count') or 3)))
    except (TypeError, ValueError):
        return 3

def blk_cases_feed(b, d, ed):
    """Последние кейсы с мини-графиками и ссылкой «Все кейсы»; пока кейсов нет — на сайте блока нет, в конструкторе заглушка."""
    if not CASES:
        return ('<section class="sec sec-tight" aria-label="Кейсы"><div class="wrap"><div class="empty">{{icon:chart-line-up}}<p>Здесь появятся последние кейсы '
                'с графиками продаж, когда их добавят в «Разделах»: «Кейсы». Пока кейсов нет, на сайте этого блока не видно.</p></div></div></section>') if ed else ''
    n = cases_count(d)
    return ('<section class="sec" aria-labelledby="%s"><div class="wrap">%s<div class="case-grid" style="margin-top:40px">%s</div></div></section>'
            % (hid(b, 'cases-h'), head_html(b, d, ed, 'cases-h', 'Кейсы', 'Результаты наших клиентов', link=('{{base}}keysy/', 'Все кейсы')),
               ''.join(case_card(c, k, ed, k >= n) for k, c in enumerate(CASES[:CASES_MAX if ed else n]))))

def blk_cases_list(b, d, ed):
    if not CASES:
        return ('<section class="sec sec-tight" aria-label="Кейсы"><div class="wrap"><div class="empty empty-cases"><span class="sk" aria-hidden="true"><i></i><i></i><i></i></span>'
                '{{icon:chart-line-up}}<p>Скоро здесь появятся кейсы: графики продаж на Wildberries и Ozon, цифры до и после и что мы сделали.</p></div></div></section>')
    return ('<section class="sec sec-tight" aria-label="Все кейсы"><div class="wrap">%s<div class="case-grid">%s</div></div></section>'
            % (case_filters(CASES), ''.join(case_card(c, k) for k, c in enumerate(CASES))))

def blk_news_list(b, d, ed):
    return '<section class="sec sec-tight" aria-label="Все новости и статьи"><div class="wrap">%s%s</div></section>' % (news_filters(NEWS), news_cards(NEWS))

FAQ_ASIDE = ('Не нашли свой вопрос?', 'Задайте его на бесплатной консультации: разберём ваш магазин и подскажем, с чего начать.', 'Задать вопрос')
def blk_faq_page(b, d, ed):
    return ('<section class="sec sec-tight" aria-label="Вопросы и ответы"><div class="wrap"><div class="faq-grid"><div class="faq">%s</div>'
            '<aside class="faq-aside" aria-labelledby="%s"><span class="ic">{{icon:chats-circle}}</span><h2 class="heading-6" id="%s"%s>%s</h2><p class="body-6"%s>%s</p>'
            '<a class="btn btn-primary btn-shine" href="{{base}}kontakty/" data-lead><span%s>%s</span>{{icon:arrow-right}}</a>'
            '<a class="tel" href="tel:{{phone_href}}">{{icon:phone}}{{phone}}</a></aside></div></div></section>'
            % (faq_html(FAQ), hid(b, 'faq-aside-h'), hid(b, 'faq-aside-h'), ea(ed, 'aside_title', fb=FAQ_ASIDE[0]), esc(d.get('aside_title') or FAQ_ASIDE[0]),
               ea(ed, 'aside_text', fb=FAQ_ASIDE[1]), esc(d.get('aside_text') or FAQ_ASIDE[1]), ea(ed, 'button', fb=FAQ_ASIDE[2]), esc(d.get('button') or FAQ_ASIDE[2])))

CONTACT = ('Что будет на встрече', 'Удобнее в мессенджере?', 'Наведите камеру на QR-код или нажмите кнопку — бот запишет вас за пару касаний.')
CONTACT_FORM = (
    '<form class="form" id="consult-form" data-lead-form novalidate>'
    '<div class="field"><label for="f-name">Как к вам обращаться <b>*</b></label><input class="inp" id="f-name" name="name" type="text" autocomplete="name" placeholder="Имя" required><p class="err" id="f-name-err" aria-live="polite"></p></div>'
    '<div class="field"><label for="f-contact">Телефон или ник в Телеграме <b>*</b></label><input class="inp" id="f-contact" name="contact" type="text" autocomplete="tel" placeholder="+7 900 000-00-00 или @username" required><p class="err" id="f-contact-err" aria-live="polite"></p></div>'
    '<div class="field"><label for="f-store">Название магазина или ссылка</label><input class="inp" id="f-store" name="store" type="text" autocomplete="organization" placeholder="Например, «Уютный дом» на Wildberries"></div>'
    '<div class="field"><label for="f-service">Что вас интересует</label><select class="inp" id="f-service" name="service">{{service-options}}</select></div>'
    '<div class="field"><label for="f-comment">Комментарий</label><div class="voice-wrap"><textarea class="inp" id="f-comment" name="comment" rows="3" placeholder="Коротко о вашем магазине и задаче"></textarea><button type="button" class="mic" data-mic="f-comment" aria-label="Надиктовать голосом">{{icon:microphone}}</button></div><p class="voice-status" id="f-comment-st" aria-live="polite"></p></div>'
    '<div class="consents">{{consents-form}}</div><p class="err form-err" aria-live="polite"></p>'
    '<button class="btn btn-primary btn-lg btn-shine" type="submit"><span>Получить консультацию</span></button>'
    '<p class="demo-note" data-demo>Демо-версия: заявка пока никуда не отправляется</p></form>'
    '<div class="done" hidden tabindex="-1"><span class="ok">{{icon:check}}</span><h2 class="heading-5">Заявка принята</h2>'
    '<p data-done-text>В рабочей версии заявка сразу придёт менеджеру и в amoCRM, и с вами свяжутся. Сейчас это демо: заявка никуда не отправлена.</p>'
    '<a class="link-arrow link-acc" href="{{base}}uslugi/"><span>Пока посмотреть услуги</span>{{icon:arrow-right}}</a></div>')
def blk_contact(b, d, ed):
    meet = ''.join('<li%s>%s<span%s>%s</span></li>' % (ei(ed), icon(MEET_ICONS[k % len(MEET_ICONS)]), ea(ed, '.'), esc(t))
                   for k, t in enumerate(x for x in d.get('items') or [] if isinstance(x, str)))
    return ('<section class="sec sec-tight" aria-label="Заявка и контакты"><div class="wrap"><div class="cta-box"><div>'
            '<h2 class="heading-5"%s>%s</h2><ul class="checks"%s>%s</ul>'
            '<h2 class="heading-6" style="margin-top:40px"%s>%s</h2><p class="body-6 muted" style="margin-top:8px"%s>%s</p>'
            '<div class="msg-row"><a class="msg-btn msg-max" href="{{base}}kontakty/" data-lead data-channel="max"><b class="max-mini">MAX</b>MAX</a>'
            '<a class="msg-btn msg-tg" href="{{base}}kontakty/" data-lead data-channel="tg">{{icon:telegram-logo}}Telegram</a></div>'
            '<div class="contacts"><a href="tel:{{phone_href}}">{{icon:phone}}{{phone}}</a><a href="mailto:{{email}}">{{icon:envelope-simple}}{{email}}</a></div>'
            '<div class="docs">{{doc-links}}</div></div><div>'
            % (ea(ed, 'meet_title', fb=CONTACT[0]), esc(d.get('meet_title') or CONTACT[0]), el(ed, 'items'), meet,
               ea(ed, 'msg_title', fb=CONTACT[1]), esc(d.get('msg_title') or CONTACT[1]), ea(ed, 'msg_text', fb=CONTACT[2]), esc(d.get('msg_text') or CONTACT[2]))
            + CONTACT_FORM + '</div></div></div></section>')

PARTNER = ('Сайты и Телеграм-боты для селлеров: свой интернет-магазин, цены и заказы под контролем.', 'Услуга «Сайт для селлера»')
def blk_partners(b, d, ed):
    return ('<section class="sec" aria-labelledby="%s"><div class="wrap">%s<div class="partners"><div class="partner" data-reveal>{{logo-osecom}}<div><p%s>%s</p>'
            '<a class="link-arrow link-acc" href="{{base}}sait/"><span%s>%s</span>{{icon:arrow-right}}</a></div></div></div></div></section>'
            % (hid(b, 'partners-h'), head_html(b, d, ed, 'partners-h', 'Наши партнёры', 'Работаем с теми, кто усиливает ваш магазин'),
               ea(ed, 'text', fb=PARTNER[0]), esc(d.get('text') or PARTNER[0]), ea(ed, 'link_text', fb=PARTNER[1]), esc(d.get('link_text') or PARTNER[1])))

BLOCKS = {  # тип → (название в конструкторе, что внутри, сборка); порядок — как в списке «Добавить блок»
    'hero': ('Первый экран главной', 'Заголовок, кнопка записи, видео-визитка', blk_hero),
    'phero': ('Заголовок страницы', 'Метка, крупный заголовок и подзаголовок', blk_phero),
    'sait-hero': ('Первый экран «Сайт для селлера»', 'Заголовок, цена, кнопка брифа и картинка', blk_sait_hero),
    'clients': ('Наши клиенты', 'Бегущая строка с логотипами', lambda b, d, ed: clients_html(ed, b)),
    'who': ('Это про вас?', 'Карточки «кому поможем» со списками', blk_who),
    'services': ('Услуги', 'Плитки услуг с ценами и заголовком', blk_services),
    'services-all': ('Все услуги плитками', 'Плитки всех услуг без заголовка', blk_services_all),
    'stats': ('Цифры', 'Опыт в цифрах', blk_stats),
    'tagline': ('Главная мысль', 'Крупная фраза, слова проявляются по очереди', blk_tagline),
    'features': ('Преимущества с иконками', 'Короткие пункты с иконками в три колонки', blk_features),
    'why': ('Почему мы', 'Карточки с иконками', blk_why),
    'founder': ('Основатель', 'Фото, имя и достижения', blk_founder),
    'portfolio': ('Наши сайты', 'Работающий магазин и демо-сайты', blk_portfolio),
    'cases-feed': ('Кейсы', 'Последние кейсы с графиками продаж: 3, 6 или 9', blk_cases_feed),
    'cases-list': ('Все кейсы', 'Карточки всех кейсов с фильтром по площадкам и услугам', blk_cases_list),
    'cases': ('Кейсы услуги', 'Кейсы «Сайта для селлера» из «Разделов»', blk_cases),
    'news': ('Новости и статьи', 'Список заголовков последних материалов, от 3 до 6', blk_news),
    'news-list': ('Все новости', 'Карточки всех новостей', blk_news_list),
    'steps': ('Как мы работаем', 'Шаги работы по порядку', blk_steps),
    'faq': ('Вопросы и ответы', 'Частые вопросы, раскрываются по нажатию', blk_faq),
    'faq-page': ('Все вопросы', 'Все вопросы и плашка «Не нашли свой вопрос?»', blk_faq_page),
    'partners': ('Партнёры', 'Карточка партнёра OS Ecom', blk_partners),
    'contact': ('Заявка и контакты', 'Форма записи, мессенджеры, телефон и почта', blk_contact),
    'cta': ('Призыв записаться', 'Тёмная плашка с кнопкой записи', blk_cta),
}
BLOCK_DEFAULTS = {  # с чем появляется новый блок из списка «Добавить блок» (дальше текст правится на месте)
    'hero': {'chip': 'Эксперты по Wildberries и Ozon', 'title': 'Заголовок с [акцентом]', 'lead': 'Коротко: что вы делаете и для кого.', 'button': 'Получить бесплатную консультацию'},
    'phero': {'chip': 'Раздел', 'title': 'Заголовок страницы', 'lead': 'Коротко о том, что на этой странице.'},
    'sait-hero': dict(SAIT_HERO),
    'who': {'chip': 'Это про вас?', 'title': 'Заголовок блока', 'cards': [{'label': '01 · Этап', 'title': 'Вы *описание ситуации* клиента', 'items': ['Что сделаем', 'Что получит клиент'], 'link_text': '', 'link': ''}]},
    'services': {'chip': 'Услуги', 'title': 'Полный спектр услуг для вашего успеха на маркетплейсах'},
    'tagline': {'text': 'Главная мысль компании — *важные слова* выделяются цветом.'},
    'features': {'chip': 'Что вы получите', 'title': 'Заголовок блока', 'items': [{'icon': i, 'title': t, 'text': x} for i, t, x in SAIT_FEATS[:3]]},
    'why': {'chip': 'Почему мы', 'title': 'За вашим магазином — целая команда', 'items': (TX.get('o_nas') or {}).get('why') or [{'icon': 'seal-check', 'text': 'Чем вы сильны'}]},
    'news': {'chip': 'Новости', 'title': 'Новости и статьи'},
    'cases-feed': {'chip': 'Кейсы', 'title': 'Результаты наших клиентов', 'count': 3},
    'cases': {'service': 'sait'},
    'contact': {'items': (TX.get('kontakty') or {}).get('meeting') or ['Онлайн-встреча в удобное для вас время']},
}

BLOCK_OPTIONS = {  # настройки блока в панели конструктора; cap — сколько пунктов показывать (лишние в конструкторе прячутся сразу)
    'news': [{'key': 'count', 'label': 'Сколько материалов показывать', 'values': [3, 4, 5, 6], 'default': NEWS_MAX, 'cap': True}],
    'cases-feed': [{'key': 'count', 'label': 'Сколько кейсов показывать', 'values': [3, 6, 9], 'default': 3, 'cap': True}],
}

# страницы сайта, которые собираются из блоков: ключ (имя файла content/site/<ключ>.json), адрес, подпись в «хлебных крошках», название в конструкторе
PAGE_KEYS = [('home', '', None, 'Главная'), ('uslugi', 'uslugi/', 'Услуги', 'Услуги'), ('sait', 'sait/', 'Сайт для селлера', 'Сайт для селлера'),
             ('keysy', 'keysy/', 'Кейсы', 'Кейсы'), ('o-nas', 'o-nas/', 'О компании', 'О компании'), ('voprosy', 'voprosy/', 'Вопросы', 'Вопросы'), ('kontakty', 'kontakty/', 'Контакты', 'Контакты'),
             ('novosti', 'novosti/', 'Новости', 'Новости')]

def default_page(key):
    """Страница в том виде, в каком она была до конструктора (заголовки — из texts.json): для переноса и для отката к старым версиям сайта."""
    T = lambda k: TX.get(k) or {}
    ph = lambda chip, k, **kw: ('phero', dict(chip=chip, title=T(k).get('title', ''), lead=T(k).get('lead', ''), **kw))
    pages = {
        'uslugi': [ph('Услуги', 'uslugi'), ('services-all', {}), ('steps', {}), ('cta', {})],
        'sait': [('sait-hero', dict(SAIT_HERO)),
                 ('features', {'chip': 'Что будет на сайте', 'title': 'Всё для продаж — уже внутри', 'items': [{'icon': i, 'title': t, 'text': x} for i, t, x in SAIT_FEATS]}),
                 ('portfolio', {'chip': PORTFOLIO[0], 'title': PORTFOLIO[1], 'text': PORTFOLIO[2]}), ('cases', {'service': 'sait'}),
                 ('steps', {'list': 'site'}), ('faq', {'topic': 'site'}),
                 ('cta', {'title': 'Готовы обсудить свой сайт?', 'text': 'Заполните бриф — по ответам подготовимся к созвону, где обсудим сроки и стоимость. Отвечать можно голосом.',
                          'button': 'Заполнить бриф', 'link': 'brief/'})],
        'o-nas': [ph('О компании', 'o_nas'), ('founder', {'cta': 'lead', 'tight': True}),
                  ('why', {'chip': 'Почему мы', 'title': 'За вашим магазином — целая команда', 'items': T('o_nas').get('why') or []}),
                  ('stats', {}), ('steps', {}), ('partners', {}), ('cta', {})],
        'voprosy': [ph('Вопрос — ответ', 'voprosy'), ('faq-page', {})],
        'kontakty': [ph('Бесплатно и без обязательств', 'kontakty', accent=True), ('contact', {'items': T('kontakty').get('meeting') or []})],
        'novosti': [ph('Новости', 'novosti'), ('news-list', {}), ('cta', {})],
        'keysy': [('phero', {'chip': 'Кейсы', 'title': 'Результаты наших клиентов',
                             'lead': 'Графики продаж на Wildberries и Ozon, цифры до и после и что мы сделали для каждого магазина.'}), ('cases-list', {}), ('cta', {})],
    }
    return {'title': {k: t for k, _, _, t in PAGE_KEYS}[key], 'blocks': [{'id': t, 'type': t, 'data': d, 'style': {}} for t, d in pages[key]]}

def norm_blocks(blocks):
    """У каждого блока — понятный уникальный id и словари data/style; незнакомые типы сохраняются как есть (на сайте их нет)."""
    out, seen = [], set()
    for b in blocks or []:
        if not isinstance(b, dict):
            continue
        t = str(b.get('type') or '')
        bid = re.sub(r'[^a-z0-9-]', '', str(b.get('id') or '').lower()) or re.sub(r'[^a-z0-9-]', '', t.lower()) or 'blok'
        base, k = bid, 2
        while bid in seen:
            bid, k = '%s-%d' % (base, k), k + 1
        seen.add(bid)
        out.append(dict(b, id=bid, type=t, data=b.get('data') if isinstance(b.get('data'), dict) else {}, style=b.get('style') if isinstance(b.get('style'), dict) else {}))
    return out

def decorate(h, b, ed):
    """Оформление блока из конструктора — на первый тег блока: свои отступы, фон, показ только на компьютере или только на телефоне."""
    st, cls, css = b.get('style') or {}, [], []
    for k in ('pt', 'pb', 'ptm', 'pbm'):
        v = str(st.get(k, '')).strip()
        if re.fullmatch(r'\d{1,3}', v):
            cls.append('blk-' + k)
            css.append('--%s:%dpx' % (k, min(int(v), 400)))
    bg = BG.get(st.get('bg')) or (st['bg'] if re.fullmatch(r'#[0-9a-fA-F]{6}', str(st.get('bg') or '')) else '')
    if bg:
        cls.append('blk-bg')
        css.append('--bgc:%s' % bg)
    cls += {'desktop': ['blk-hm'], 'mobile': ['blk-hd']}.get(st.get('show'), [])
    if b.get('hidden'):
        cls.append('blk-off')
    extra = ' data-blk="%s" data-type="%s"' % (b['id'], b['type']) if ed else ''
    m = re.match(r'(\s*<[a-z0-9]+)([^>]*)>', h)
    if not m or not (cls or css or extra):
        return h
    attrs = m.group(2)
    if cls:
        attrs = re.sub(r'\sclass="([^"]*)"', lambda x: ' class="%s %s"' % (x.group(1), ' '.join(cls)), attrs, count=1) if ' class="' in attrs else attrs + ' class="%s"' % ' '.join(cls)
    if css:
        attrs = re.sub(r'\sstyle="([^"]*)"', lambda x: ' style="%s;%s"' % (x.group(1).rstrip(';'), ';'.join(css)), attrs, count=1) if ' style="' in attrs else attrs + ' style="%s"' % ';'.join(css)
    return m.group(1) + attrs + extra + '>' + h[m.end():]

def render_blocks(blocks, ed=False):
    return ''.join(decorate(BLOCKS[b['type']][2](b, b['data'], ed), b, ed) for b in blocks if b['type'] in BLOCKS and (ed or not b.get('hidden')))

def legacy_home(raw):
    """Главная в старом виде (content/home.json: hero, who, … и порядок sections) → блоки. Нужна, если сайт откатили к версии до конструктора."""
    h = flat_home(raw)
    data = {'hero': {'chip': h.get('hero_chip', ''), 'title': h.get('hero_title', ''), 'lead': h.get('hero_lead', ''), 'button': h.get('hero_cta', '')},
            'who': {'chip': h.get('who_chip', ''), 'title': h.get('who_title', ''), 'cards': h.get('who') or []},
            'services': {'chip': h.get('services_chip', ''), 'title': h.get('services_title', '')},
            'news': {'chip': h.get('news_chip', ''), 'title': h.get('news_title', '')},
            'tagline': {'text': h.get('tagline', '')}}
    order = ['hero'] + [s.get('type') if isinstance(s, dict) else s for s in h.get('sections') or []]
    return {'title': 'Главная', 'blocks': [{'id': t, 'type': t, 'data': data.get(t, {}), 'style': {}} for t in order if t in BLOCKS]}

def load_doc(key):
    """Страница из конструктора: content/site/<ключ>.json; нет файла (откат к старой версии) — прежний вид страницы."""
    d = jload('site/%s.json' % key)
    if not (isinstance(d, dict) and isinstance(d.get('blocks'), list)):
        d = legacy_home(jload('home.json')) if key == 'home' else default_page(key)
    d['blocks'] = norm_blocks(d['blocks'])
    return d

# ---------- стили ----------
def mini(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    css = re.sub(r'\s+', ' ', css)
    css = re.sub(r'\s*([{};,>])\s*', r'\1', css)
    css = re.sub(r'([{;])([a-z-]+) ?: ?', r'\1\2:', css)
    return css.replace(';}', '}').strip()
FONTS = (SRC / 'css' / 'fonts.css').read_text(encoding='utf-8').replace('url(../fonts/', 'url({{base}}fonts/')
CSS = mini(FONTS + (SRC / 'css' / 'style.css').read_text(encoding='utf-8')).replace('{{base}}', BASE)
CSS_BRIEF = mini((SRC / 'css' / 'brief.css').read_text(encoding='utf-8'))
assert '{{' not in CSS + CSS_BRIEF
def braces_ok(css):  # непарная скобка молча выбрасывает целый блок стилей — такую сборку не выпускаем
    depth = 0
    for ch in re.sub(r'"[^"]*"|\'[^\']*\'', '', css):
        depth += (ch == '{') - (ch == '}')
        if depth < 0:
            return False
    return depth == 0
if not braces_ok(CSS) or not braces_ok(CSS_BRIEF):
    raise SystemExit('Ошибка в стилях: непарные фигурные скобки в src/css/*.css')

def logo_html():
    return '<img src="%s" alt="" width="32" height="32">' % esc(media(S['logo'])) if S.get('logo') else MARK

def tokens(text):
    for k, v in (('{{logo}}', logo_html()), ('{{logo-osecom}}', OSECOM), ('{{ver}}', VER), ('{{site}}', SITE), ('{{company}}', esc(COMPANY)),
                 ('{{phone}}', esc(S.get('phone', ''))), ('{{phone_href}}', esc(S.get('phone_href', ''))), ('{{email}}', esc(S.get('email', ''))),
                 ('{{year}}', time.strftime('%Y')), ('{{base}}', BASE)):
        text = text.replace(k, v)
    text = re.sub(r'\{\{icon:([a-z0-9-]+)\}\}', lambda m: icons.get(m.group(1), icons['check']), text)
    left = [t for t in re.findall(r'\{\{[^}]*\}\}', text) if t != '{{css}}']
    assert not left, left
    return text

NAV = [('uslugi', 'uslugi/', 'Услуги')] + ([('keysy', 'keysy/', 'Кейсы')] if CASES else []) + [  # «Кейсы» в меню — когда появится первый кейс
       ('novosti', 'novosti/', 'Новости'), ('o-nas', 'o-nas/', 'О компании'), ('voprosy', 'voprosy/', 'Вопросы'), ('kontakty', 'kontakty/', 'Контакты')]
LAYOUT = (SRC / 'layout.html').read_text(encoding='utf-8')
WIDGETS = (SRC / 'pages' / 'widgets.html').read_text(encoding='utf-8')
STICKY = '<div class="sticky-cta"><a class="btn btn-primary" href="{{base}}kontakty/" data-lead><span>Бесплатная консультация</span>{{icon:arrow-right}}</a></div>'

def chat_alt_html():
    """Ссылки под чатом: прямо менеджеру, если его аккаунт указан в админке, иначе — запись через бота."""
    links = []
    for key, ch, label in (('manager_max_url', 'max', 'MAX'), ('manager_telegram_url', 'tg', 'Telegram')):
        u = S.get(key)
        links.append('<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(u), label) if u else
                     '<a href="{{base}}kontakty/" data-lead data-channel="%s">%s</a>' % (ch, label))
    return '<p class="chat-alt">Или в мессенджере: %s</p>' % ' · '.join(links)

def widgets_html():
    tg, mx = S.get('telegram_url', ''), S.get('max_url', '')
    out = WIDGETS
    for k, v in (('{{tg-raw}}', esc(tg)), ('{{max-raw}}', esc(mx)), ('{{endpoint}}', esc(S.get('lead_endpoint', ''))),
                 ('{{mtg}}', esc(S.get('manager_telegram_url') or tg)), ('{{mmax}}', esc(S.get('manager_max_url') or mx)),
                 ('{{chat_label}}', esc(S.get('chat_label') or 'Напишите нам, мы онлайн')),
                 ('{{chat_greeting}}', esc(S.get('chat_greeting') or 'Здравствуйте! Чем помочь вашему магазину?')), ('{{chat-alt}}', chat_alt_html()),
                 ('{{service-options}}', OPTIONS), ('{{consents-lead}}', consents('l')), ('{{consents-chat}}', consents('c'))):
        out = out.replace(k, v)
    return out

def page(key, title, desc, body, sticky=True, scripts=('site',), head='', noindex=False, og_type='website', og_image=None):
    def a(k, url, label, li=False):
        x = '<a href="{{base}}%s"%s>%s</a>' % (url, ' aria-current="page"' if k == key else '', label)
        return '<li>%s</li>' % x if li else x
    nav = ''.join(a(*n) for n in NAV)
    out = LAYOUT
    for k, v in (('{{content}}', body), ('{{nav}}', nav), ('{{mnav}}', a('home', '', 'Главная') + nav),
                 ('{{fnav}}', a('home', '', 'Главная', True) + ''.join(a(*n, li=True) for n in NAV) + a('sait', 'sait/', 'Сайт для селлера', True)),
                 ('{{fdocs}}', ''.join('<li><a href="{{base}}dokumenty/%s/">%s</a></li>' % (d['slug'], esc(d['title'])) for d in DOCS)),
                 ('{{footer_text}}', esc(S.get('footer_text', ''))), ('{{widgets}}', widgets_html()),
                 ('{{robots}}', 'index, follow' if INDEX and not noindex else 'noindex, nofollow'),
                 ('{{title}}', esc(title)), ('{{desc}}', esc(desc)), ('{{head}}', head),
                 ('{{og_type}}', og_type), ('{{og_image}}', esc(og_image or SITE + 'img/og.png')),
                 ('{{scripts}}', ''.join('<script src="{{base}}js/%s.js?v={{ver}}" defer></script>' % s for s in scripts)),
                 ('{{sticky}}', STICKY if sticky else '')):
        out = out.replace(k, v)
    out = tokens(out).replace(' — ', '\u00a0— ')  # тире не переносится в начало строки
    return out.replace('{{css}}', CSS)

# ---------- портфолио на странице «Сайт для селлера» (наши работы, не контент Артёма) ----------
PROJECTS = [
    ('megaopt', 'МегаОпт', 'Работающий магазин', 'https://i78424325.github.io/', '#FFFFFF',
     'Магазин электроники: каталог с поиском, корзина и личный кабинет, оплата при получении.', ['Каталог и поиск', 'Корзина и кабинет', 'Мобильная версия']),
    ('osj', 'ОСЬ', 'Демо: бренд одежды', 'https://i78424325.github.io/os-odezhda/', '#E3E2DF', 'Бренд одежды: фирменный стиль, лукбук и корзина.', []),
    ('lapa', 'Лапа и Хвост', 'Демо: зоомагазин', 'https://i78424325.github.io/lapa-i-hvost/', '#EDF1EA', 'Калькулятор суточной нормы корма и подписка на доставку.', []),
    ('protektor', 'ПРОТЕКТОР', 'Демо: шины и диски', 'https://i78424325.github.io/protektor-shiny/', '#F6F7F7', 'Подбор шин по размеру и по машине, запись на шиномонтаж.', []),
]
LOCK = '<svg class="i" viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="2" fill="currentColor"/><path d="M5 7V5a3 3 0 0 1 6 0v2" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>'
def phone_html(slug, sb, alt):
    return ('<div class="phone"><div class="phone-scr"><div class="phone-sb" style="--sb:%s"><span>9:41</span><span class="ico"><i></i><i></i></span></div>'
            '<img src="{{base}}img/work/%s-m.webp" alt="%s" width="600" height="1298" loading="lazy" decoding="async"></div></div>' % (sb, slug, alt))
def proj_feature_html():
    slug, name, kind, url, sb, text, tags = PROJECTS[0]
    return ('<article class="proj-feature" data-reveal><div class="proj-copy"><span class="chip chip-accent"><i class="dot"></i>%s</span><h3>%s</h3><p>%s</p>'
            '<ul class="tags">%s</ul><a class="link-arrow link-acc" href="%s" target="_blank" rel="noopener"><span>Открыть сайт</span>{{icon:arrow-up-right}}</a></div>'
            '<div class="proj-art"><div class="browser"><div class="browser-bar"><i></i><i></i><i></i><span class="url">%s<span>megaopt</span></span></div>'
            '<img src="{{base}}img/work/%s-d.webp" alt="Сайт «%s» на компьютере" width="1600" height="1000" loading="lazy" decoding="async"></div>%s</div></article>'
            % (kind, name, text, ''.join('<li>%s</li>' % t for t in tags), url, LOCK, slug, name, phone_html(slug, sb, 'Сайт «%s» на телефоне' % name)))
def demos_html():
    cls = {'osj': 'd-osj', 'lapa': 'd-lapa', 'protektor': 'd-prot'}
    return '<div class="demos">' + ''.join(
        '<a class="demo %s" href="%s" target="_blank" rel="noopener" data-reveal style="--d:%dms"><div class="dc"><span class="chip">%s</span><h3>%s</h3><p>%s</p></div>'
        '<span class="go" aria-hidden="true">{{icon:arrow-up-right}}</span>%s</a>'
        % (cls[slug], url, k * 100, kind, name, text, phone_html(slug, sb, 'Демо-сайт «%s» на телефоне' % name))
        for k, (slug, name, kind, url, sb, text, _t) in enumerate(PROJECTS[1:])) + '</div>'

# ---------- сборка страниц ----------
MEET_ICONS = ['calendar-check', 'chart-line-up', 'chats-circle', 'seal-check', 'clock']
SECTIONS = {  # общие куски, которые блоки и шаблоны вставляют по имени
    '{{service-options}}': OPTIONS, '{{consents-form}}': consents('f'),
    '{{proj-feature}}': proj_feature_html(), '{{demos}}': demos_html(), '{{viz:sait}}': VIZ.get('sait', ''), '{{sait-price}}': sait_price(),
    '{{phero-bg}}': '<div class="grid-bg" aria-hidden="true"></div><div class="glow glow-a" aria-hidden="true"></div>',
    '{{doc-links}}': ''.join('<a href="{{base}}dokumenty/%s/">%s</a>' % (d['slug'], esc(d['title'])) for d in DOCS),
}
def fill(text, crumb=None):
    for _ in range(2):  # блоки могут содержать другие блоки (например, фон в шапке услуги)
        for k, v in SECTIONS.items():
            text = text.replace(k, v)
    text = re.sub(r'\{\{t:([a-z_]+)\.([a-z_]+)\}\}', lambda m: esc(str((TX.get(m.group(1)) or {}).get(m.group(2), ''))), text)
    return text.replace('{{crumbs}}', crumbs(crumb) if crumb else '')

parts = re.split(r'<!--@page ([a-z0-9-]+)-->', (SRC / 'pages' / 'inner.html').read_text(encoding='utf-8'))
inner = {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}
FAQ_LD = '<script type="application/ld+json">%s</script>' % json.dumps({'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
    {'@type': 'Question', 'name': str(i['q']), 'acceptedAnswer': {'@type': 'Answer', 'text': re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', answer_html(i.get('a'))))).strip()}}
    for i in FAQ]}, ensure_ascii=False).replace('</', '<\\/').replace('{{', '{\\u007b')

# ---------- страницы из блоков (главная, «Услуги», «Сайт для селлера», «О компании», «Вопросы», «Контакты», «Новости») ----------
SITE_DOCS = {k: load_doc(k) for k, _, _, _ in PAGE_KEYS}
CRUMB = {k: c for k, _, c, _ in PAGE_KEYS}
PAGE_META = {  # заголовок вкладки, описание для поиска (None — подзаголовок страницы), особые настройки страницы
    'home': ('%s — рост продаж на Wildberries и Ozon' % COMPANY, 'Аналитика, реклама, дизайн карточек, SEO и сопровождение селлеров Wildberries и Ozon. Начните с бесплатной консультации.', {}),
    'uslugi': ('Услуги — %s' % COMPANY, 'Бизнес-трекер, реклама, дизайн и SEO карточек, фото и видео, работа с покупателями, подбор ниши.', {}),
    'sait': ('Сайт для селлера — %s' % COMPANY, 'Свой интернет-магазин для селлера Wildberries и Ozon: админ-панель, Метрика, доставка, оплата и заказы в Телеграм.', {}),
    'o-nas': ('О компании — %s' % COMPANY, None, {}),
    'voprosy': ('Частые вопросы — %s' % COMPANY, 'Ответы о работе с Wildberries и Ozon, оплате и рекламе.', {'head': FAQ_LD}),
    'kontakty': ('Бесплатная консультация — %s' % COMPANY, 'Запишитесь на бесплатную онлайн-встречу с аналитиком маркетплейсов.', {'sticky': False, 'scripts': ('voice', 'site')}),
    'novosti': ('Новости — %s' % COMPANY, None, {}),
    'keysy': ('Кейсы — %s' % COMPANY, 'Кейсы селлеров Wildberries и Ozon: графики продаж, цифры до и после и что мы сделали для магазина.', {'noindex': not CASES}),
}
def render_page(key, ed=False):
    CTX['crumb'] = CRUMB[key]
    try:
        return fill(render_blocks(SITE_DOCS[key]['blocks'], ed))
    finally:
        CTX['crumb'] = None
def lead_of(key):
    b = next((b for b in SITE_DOCS[key]['blocks'] if b['type'] in ('phero', 'sait-hero', 'hero') and not b.get('hidden')), None)
    return str((b or {}).get('data', {}).get('lead') or '')
def site_page(key, ed=False):
    title, desc, kw = PAGE_META[key]
    if ed:  # версия для конструктора: не для поисковиков, с меткой версии сборки
        kw = dict(kw, noindex=True, head=kw.get('head', '') + '<meta name="dm-rev" content="%s">' % esc(REV))
        title = 'Конструктор — %s' % title
    return page(key, title, lead_of(key) if desc is None else desc, render_page(key, ed), **kw)

def news_post(n):
    if n['video']:
        top = '<div class="video-box">%s</div>' % video_html(n['video'], n['cover'])
    elif n['cover']:
        top = '<figure class="figure"><img src="%s" alt="" decoding="async"></figure>' % esc(media(n['cover']))
    else:
        top = ''
    more = [x for x in NEWS if x['slug'] != n['slug']][:3]
    return ('<section class="phero"><div class="wrap narrow">%s<div class="np-meta"><time class="chip" datetime="%s">%s</time><span class="chip chip-accent">%s</span></div>'
            '<h1 class="heading-2 grad">%s</h1>%s</div></section>'
            '<section class="sec sec-tight"><div class="wrap narrow">%s<article class="prose">%s</article>'
            '<a class="link-arrow link-acc" href="{{base}}novosti/" style="margin-top:40px"><span class="flip">{{icon:arrow-right}}</span><span>Все новости и статьи</span></a></div></section>'
            % (crumbs(('Новости', '{{base}}novosti/'), (n['title'], None)), esc(n['date']), ru_date(n['date']), esc(news_tag(n)), esc(n['title']),
               '<p class="lead">%s</p>' % esc(n['excerpt']) if n['excerpt'] else '', top, md(n['body'])) +
            ('<section class="sec" style="padding-top:0"><div class="wrap"><h2 class="heading-5">Читайте также</h2><div style="margin-top:24px">%s</div></div></section>' % news_cards(more) if more else '') + cta_band())

def abs_url(u):
    """Путь на сайте → полный адрес (для соцсетей и поисковиков)."""
    return u if re.match(r'^https?://', u or '', re.I) else ORIGIN + (u or '')

def article_ld(n):
    """Разметка статьи для Яндекса и Google: заголовок, дата, рубрика, обложка, издатель."""
    ld = {'@context': 'https://schema.org', '@type': 'NewsArticle' if n['kind'] == 'Новость' else 'Article',
          'headline': (n['seo_title'] or n['title'])[:110], 'description': n['seo_description'] or n['excerpt'] or n['title'],
          'datePublished': n['date'], 'dateModified': n['date'], 'mainEntityOfPage': SITE + 'novosti/%s/' % n['slug'],
          'author': {'@type': 'Organization', 'name': COMPANY},
          'publisher': {'@type': 'Organization', 'name': COMPANY, 'logo': {'@type': 'ImageObject', 'url': SITE + 'img/og.png'}}}
    if n['cover']:
        ld['image'] = [abs_url(media(n['cover']))]
    if n['topic']:
        ld['articleSection'] = n['topic']
    return '<script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False).replace('</', '<\\/').replace('{{', '{\\u007b')

def doc_page(d):
    nav = ''.join('<li><a href="{{base}}dokumenty/%s/"%s>%s</a></li>' % (o['slug'], ' aria-current="page"' if o['slug'] == d['slug'] else '', esc(o['title'])) for o in DOCS)
    return ('<section class="phero"><div class="wrap">%s<h1 class="heading-2 grad">%s</h1></div></section>'
            '<section class="sec sec-tight"><div class="wrap doc-layout"><article class="prose card doc">%s</article><aside class="doc-nav card"><b>Документы</b><ul>%s</ul></aside></div></section>'
            % (crumbs(('Документы', '{{base}}dokumenty/'), (d['title'], None)), esc(d['title']), md(d['body']), nav))

DOCS_LIST = ('<section class="phero">{{phero-bg}}<div class="wrap">%s<h1 class="heading-1 grad">Документы</h1><p class="lead">Оферта, политика обработки персональных данных и согласия.</p></div></section>'
             '<section class="sec sec-tight"><div class="wrap"><div class="doc-list">%s</div></div></section>'
             % (crumbs(('Документы', None)), ''.join('<a class="doc-item" href="{{base}}dokumenty/%s/" data-reveal><span class="ic">{{icon:file-text}}</span><b>%s</b>{{icon:arrow-right}}</a>'
                                                     % (d['slug'], esc(d['title'])) for d in DOCS)))

PAGES_OUT = [(url, site_page(key)) for key, url, _, _ in PAGE_KEYS] + [
    ('dokumenty/', page('dokumenty', 'Документы — %s' % COMPANY, 'Оферта, политика обработки персональных данных и согласия.', fill(DOCS_LIST), sticky=False)),
] + [('uslugi/%s/' % s['slug'], page('uslugi', '%s — %s' % (s['title'], COMPANY), s.get('short', ''), fill(service_body(s)))) for s in SERVICES if s['slug'] != 'sait'] \
  + [('novosti/%s/' % n['slug'], page('novosti', '%s — %s' % (n['seo_title'] or n['title'], COMPANY), n['seo_description'] or n['excerpt'] or n['title'],
                                       fill(news_post(n)), head=article_ld(n), og_type='article', og_image=abs_url(media(n['cover'])) if n['cover'] else None)) for n in NEWS] \
  + [('keysy/%s/' % c['slug'], page('keysy', '%s — %s' % (c['title'], COMPANY), c['excerpt'] or c['title'], fill(case_page(c)),
                                     og_image=abs_url(media(c['cover'])) if c['cover'] else None)) for c in CASES] \
  + [('dokumenty/%s/' % d['slug'], page('dokumenty', '%s — %s' % (d['title'], COMPANY), d['title'], fill(doc_page(d)), sticky=False)) for d in DOCS] \
  + [('%s/' % p['slug'], page(p['slug'], '%s — %s' % (p.get('title') or p['slug'], COMPANY), p.get('description', ''), fill(''.join(block_html(b) for b in p.get('blocks') or []))))
     for p in PAGES]

if OUT.exists():
    for item in OUT.iterdir():
        if item.name != '.git':
            shutil.rmtree(item) if item.is_dir() else item.unlink()
OUT.mkdir(exist_ok=True)
shutil.copytree(SRC / 'fonts', OUT / 'fonts')
(OUT / 'img' / 'work').mkdir(parents=True)
for f in list((SRC / 'img').glob('*.webp')) + [SRC / 'img' / 'og.png'] + list((SRC / 'img' / 'work').glob('*.webp')):
    shutil.copy2(f, OUT / f.relative_to(SRC))
for sub in ('img/uploads', 'admin'):
    if (SRC / sub).exists():
        shutil.copytree(SRC / sub, OUT / sub)
for _f in list((OUT / 'admin').glob('*.yml')) + list((OUT / 'admin').glob('*.html')) if (OUT / 'admin').exists() else []:
    # адрес сайта и версия файлов — от текущей сборки (остальные {{…}} в config.yml — шаблоны самой админки)
    _f.write_text(_f.read_text(encoding='utf-8').replace('{{base}}', BASE).replace('{{site}}', SITE).replace('{{ver}}', VER)
                  .replace("'{{service_options}}'", json.dumps([{'label': s['title'], 'value': s['slug']} for s in SERVICES], ensure_ascii=False)), encoding='utf-8')
(OUT / 'js').mkdir()
for name in ('site', 'voice', 'brief'):
    (OUT / 'js' / (name + '.js')).write_text(tokens((SRC / 'js' / (name + '.js')).read_text(encoding='utf-8')), encoding='utf-8')
for path, text in PAGES_OUT:
    (OUT / path).mkdir(parents=True, exist_ok=True)
    (OUT / path / 'index.html').write_text(text, encoding='utf-8')

# ---------- конструктор: версии страниц для редактора (с пометками полей и скрытыми блоками) и их данные ----------
def blob_sha(rel):
    """Отпечаток файла как в git: конструктор проверяет, не изменили ли файл в админке, пока он был открыт."""
    f = C / rel
    if not f.exists():
        return None
    b = f.read_bytes()
    return hashlib.sha1(b'blob %d\x00' % len(b) + b).hexdigest()
LIB = {t: tokens(fill(render_blocks(norm_blocks([{'id': 'zznewzz', 'type': t, 'data': BLOCK_DEFAULTS.get(t, {})}]), True))).replace(' — ', ' — ')
       for t in BLOCKS}  # заготовки для «Добавить блок»; zznewzz конструктор меняет на id нового блока
EDIT_COMMON = {
    'rev': REV, 'ver': VER, 'repo': os.environ.get('GITHUB_REPOSITORY') or 'i78424325/doctor-marketplace-v2', 'branch': 'main',
    'pages': [{'key': k, 'title': t, 'url': BASE + u} for k, u, _, t in PAGE_KEYS],
    'sources': {n: {'file': 'content/%s.json' % n, 'doc': (F if n == 'founder' else jload('%s.json' % n)) or {}, 'sha': blob_sha('%s.json' % n)}
                for n in ('stats', 'founder', 'services', 'clients', 'steps', 'video')},
    'types': {t: {'name': v[0], 'about': v[1], 'options': BLOCK_OPTIONS.get(t, [])} for t, v in BLOCKS.items()},
    'defaults': BLOCK_DEFAULTS, 'library': LIB, 'bg': BG,
}
for _k, _u, _c, _t in PAGE_KEYS:  # admin/edit/<ключ>/ — страница для правки и её данные
    _dir = OUT / 'admin' / 'edit' / _k
    _dir.mkdir(parents=True, exist_ok=True)
    (_dir / 'index.html').write_text(site_page(_k, True), encoding='utf-8')
    (_dir / 'data.json').write_text(json.dumps(dict(EDIT_COMMON, doc=SITE_DOCS[_k], page={
        'key': _k, 'title': _t, 'url': BASE + _u, 'file': 'content/site/%s.json' % _k, 'sha': blob_sha('site/%s.json' % _k)}), ensure_ascii=False), encoding='utf-8')
(OUT / '404.html').write_text(page('404', 'Страница не найдена — %s' % COMPANY, 'Такой страницы нет.', fill(inner['404']), sticky=False), encoding='utf-8')
brief = tokens((SRC / 'brief' / 'index.html').read_text(encoding='utf-8')).replace('{{css}}', CSS + CSS_BRIEF)
(OUT / 'brief').mkdir()
(OUT / 'brief' / 'index.html').write_text(brief, encoding='utf-8')
(OUT / 'favicon.svg').write_text(MARK.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ', 1).replace(' aria-hidden="true" focusable="false"', ''), encoding='utf-8')
_lastmod = dict([('novosti/%s/' % n['slug'], n['date']) for n in NEWS] + [('keysy/%s/' % c['slug'], c['date']) for c in CASES])
_lastmod = {p: d for p, d in _lastmod.items() if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d)}
(OUT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n' % '\n'.join(
    '<url><loc>%s</loc>%s</url>' % (esc(SITE + p), '<lastmod>%s</lastmod>' % _lastmod[p] if p in _lastmod else '') for p, _ in PAGES_OUT if CASES or p != 'keysy/'), encoding='utf-8')
(OUT / 'robots.txt').write_text('User-agent: *\n%s\n' % ('Allow: /\nSitemap: %ssitemap.xml' % SITE if INDEX else 'Disallow: /'), encoding='utf-8')
(OUT / '.nojekyll').write_text('', encoding='utf-8')
sizes = sorted(((p.stat().st_size, str(p.relative_to(OUT))) for p in OUT.rglob('index.html')), reverse=True)
print('built', VER, '→', OUT, '| страниц:', len(PAGES_OUT) + 2, '| новостей:', len(NEWS), '| кейсов:', len(CASES), '| документов:', len(DOCS), '| своих страниц:', len(PAGES),
      '| самая тяжёлая:', sizes[0][1], sizes[0][0] // 1024, 'КБ | CSS:', len(CSS) // 1024, 'КБ')
