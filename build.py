#!/usr/bin/env python3
"""Сборка сайта «Доктор Маркетплейс».
content/ — всё, что правится в админке /admin: контакты, тексты, цены, кейсы, новости, документы, страницы.
src/     — шаблоны, стили, скрипты и иконки. Результат — site/ (готовые страницы для GitHub Pages или любого хостинга).
Стили и иконки вшиваются в каждую страницу, поэтому на старте нет лишних запросов. Только стандартная библиотека Python 3.9+.
Адрес сайта: переменные окружения SITE_BASE и SITE_URL (по умолчанию копия на GitHub Pages; для своего домена SITE_BASE=/)."""
import html, json, os, pathlib, re, shutil, sys, time, unicodedata, urllib.parse

P = pathlib.Path(__file__).resolve().parent
SRC, OUT, C = P / 'src', P / 'site', P / 'content'
BASE = os.environ.get('SITE_BASE', '/doctor-marketplace-v2/')
SITE = os.environ.get('SITE_URL', 'https://i78424325.github.io').rstrip('/') + BASE
VER = time.strftime('%m%d%H%M')
INDEX = os.environ.get('SITE_INDEX') == '1'  # 1 — открыть сайт поисковикам (когда переедет на свой домен)

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

SERVICES = uniq([dict(s, slug=slugify(s.get('slug') or s['title']) or 'usluga') for s in jload('services.json').get('services', []) if s.get('title')], what='Услуга')
BY_SLUG = {s['slug']: s for s in SERVICES}
FAQ = [i for i in jload('faq.json').get('items', []) if i.get('q')]
STATS = [i for i in jload('stats.json').get('items', []) if i.get('value')]
STEPS = jload('steps.json')
CLIENTS = jload('clients.json')
DOCS = uniq(sorted(({'slug': slugify(d.get('url') or d['_file']), 'title': d.get('title') or d['_file'], 'order': num(d.get('order')),
                     'body': d.get('body', '')} for d in entries('docs')), key=lambda d: (d['order'], d['title'])))
# старые новости сохраняют адрес, у новой с тем же заголовком будет -2: ссылки, которыми уже поделились, не меняются
NEWS = list(reversed(uniq(sorted(({'slug': slugify(d.get('url') or re.sub(r'^\d{4}-\d{2}-\d{2}-?', '', d['_file']) or d.get('title')),
                                   'title': d.get('title') or 'Новость', 'date': str(d.get('date') or '')[:10], 'excerpt': d.get('excerpt') or '',
                                   'cover': d.get('cover') or '', 'video': d.get('video') or '', 'body': d.get('body') or ''} for d in entries('news')),
                                 key=lambda n: (n['date'], n['slug'])), what='Новость')))
RESERVED = {'uslugi', 'sait', 'o-nas', 'voprosy', 'kontakty', 'novosti', 'dokumenty', 'brief', 'admin', 'img', 'js', 'fonts'}
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

def price_html(s, cls='price'):
    p = str(s.get('price_from') or '').strip()
    p = re.sub(r'\s*(₽|руб(\.|лей)?|р\.)$', '', re.sub(r'^от\s*', '', p, flags=re.I), flags=re.I).strip()  # «от 15000 ₽» → 15000
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

# ---------- блоки ----------
_vz = re.split(r'<!--@viz ([a-z0-9-]+)-->', (SRC / 'pages' / 'viz.html').read_text(encoding='utf-8'))
VIZ = {_vz[i]: _vz[i + 1].strip() for i in range(1, len(_vz), 2)}

def bento_html():
    """Плитки услуг в порядке из админки: первая — большая (2×2), ряд добирается широкими плитками."""
    n = len(SERVICES)
    wides = (4 - (n + 3) % 4) % 4 if n > 1 else 0
    wide = set(range(max(1, n - 1 - wides), n - 1)) if wides else set()
    out = []
    for k, s in enumerate(SERVICES):
        slug = s['slug']
        size = ' tile-big' if k == 0 else (' tile-wide' if k in wide else '')
        url = '{{base}}sait/' if slug == 'sait' else '{{base}}uslugi/%s/' % slug
        out.append('<a class="tile tile-%s%s" href="%s" data-reveal style="--d:%dms"><div class="tile-copy"><h3>%s</h3><p>%s</p>%s</div>'
                   '<div class="viz" aria-hidden="true">%s</div><span class="tile-go" aria-hidden="true">{{icon:arrow-up-right}}</span></a>'
                   % (slug, size, url, (k % 4) * 70, esc(s['title']), esc(s.get('tile_text') or s.get('short', '')),
                      '' if slug == 'sait' else price_html(s), VIZ.get(slug, '')))
    return ''.join(out)

def answer_html(a):
    """Ответ в вопросах — это HTML (можно ссылки). Пустая строка — новый абзац, перенос — новая строка; {{base}} — адрес сайта."""
    a = str(a or '').replace('\r\n', '\n').replace('{{base}}', BASE).replace('{', '&#123;')
    parts = [p.strip() for p in re.split(r'\n\s*\n', a) if p.strip()]
    return ''.join('<p>%s</p>' % p.replace('\n', '<br>') for p in parts) or '<p></p>'

def faq_html(items):
    return ''.join('<details><summary>%s<span class="pm">{{icon:plus}}</span></summary><div class="ans">%s</div></details>'
                   % (esc(i['q']), answer_html(i.get('a'))) for i in items)

def steps_html(items, compact=False):
    line = '' if compact else '<div class="steps-line" aria-hidden="true"><i></i></div>'
    cls = ' compact' if compact else (' three' if len(items) == 3 else '')
    body = ''.join('<div class="step"%s><span class="num">%02d</span><div><h3>%s</h3><p>%s</p></div></div>'
                   % ('' if compact else ' data-reveal style="--d:%dms"' % (k * 100), k + 1, esc(i.get('title', '')), esc(i.get('text', '')))
                   for k, i in enumerate(items))
    return '<div class="steps%s">%s%s</div>' % (cls, line, body)

def stat_value(v):
    return esc(html.unescape(str(v))).replace(' ', '&nbsp;').replace('\xa0', '&nbsp;')

def stats_html():
    return '<div class="stats">' + ''.join('<div class="stat" data-reveal style="--d:%dms"><b>%s</b><span>%s</span></div>'
                                           % (k * 60, stat_value(i['value']), esc(i.get('label', ''))) for k, i in enumerate(STATS)) + '</div>'

def tagline_html():
    words, i = [], 0
    for seg in re.split(r'(\*[^*]+\*)', HOME.get('tagline', '')):
        acc = seg.startswith('*')
        for w in seg.strip('*').split():
            words.append('<span class="w%s" style="--i:%d">%s</span>' % (' acc' if acc else '', i, esc(w)))
            i += 1
    return '<section class="tagline" aria-label="Наш подход"><div class="wrap"><p>%s</p></div></section>' % ' '.join(words)

def clients_html():
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
    return ('<section class="clients" aria-labelledby="cl-h"><div class="wrap clients-head"><h2 class="clients-h" id="cl-h">%s</h2></div>'
            '<div class="marquee"><div class="marquee-in"><ul>%s</ul><ul aria-hidden="true">%s</ul></div></div></section>'
            % (esc(CLIENTS.get('title') or 'Наши клиенты'), items, items))

def who_html():
    out = []
    for k, w in enumerate(HOME.get('who') or []):
        out.append('<article class="card" data-reveal style="--d:%dms"><span class="n">%s</span><h3 class="heading-6">%s</h3><ul class="checks">%s</ul>%s</article>'
                   % (k * 80, esc(w.get('label', '')), accent(w.get('title', '')),
                      ''.join('<li>{{icon:check-circle}}<span>%s</span></li>' % esc(t) for t in w.get('items') or []),
                      '<a class="link-arrow link-acc" href="%s"><span>%s</span>{{icon:arrow-right}}</a>' % (esc(href(w.get('link'), BASE + 'uslugi/')), esc(w['link_text'])) if w.get('link_text') else ''))
    return ''.join(out)

F = HOME.get('founder') or {}
def founder_html(cta):
    photo = media(F.get('photo')) or BASE + 'img/artem.webp'
    return ('<div class="founder"><div class="portrait" data-reveal><img src="%s" alt="%s" width="336" height="336" loading="lazy" decoding="async">'
            '<span class="chip"><i class="dot"></i>Основатель компании</span></div><div data-reveal style="--d:100ms"><span class="chip">%s</span>'
            '<h2 class="heading-2" style="margin-top:16px">%s</h2><p class="lead" style="margin-top:8px">%s</p><ul class="checks">%s</ul>'
            '<div class="hero-cta">%s</div></div></div>'
            % (esc(photo), esc('%s — %s' % (F.get('name', ''), F.get('role', ''))), esc(F.get('chip') or 'Кто ведёт ваш магазин'),
               esc(F.get('name', '')), esc(F.get('role', '')), ''.join('<li>{{icon:seal-check}}<span>%s</span></li>' % esc(t) for t in F.get('items') or []), cta))

def news_cards(items):
    if not items:
        return '<div class="empty">{{icon:newspaper}}<p>Скоро здесь появятся новости и статьи.</p></div>'
    out = []
    for n in items:
        cover = ('<span class="nc-img"><img src="%s" alt="" loading="lazy" decoding="async"></span>' % esc(media(n['cover']))) if n['cover'] else \
                '<span class="nc-img nc-ph">%s</span>' % ('{{icon:play}}' if n['video'] else '{{icon:newspaper}}')
        out.append('<a class="news-card" href="{{base}}novosti/%s/" data-reveal>%s<span class="nc-body"><time datetime="%s">%s</time><b>%s</b><span>%s</span></span></a>'
                   % (n['slug'], cover, esc(n['date']), ru_date(n['date']), esc(n['title']), esc(n['excerpt'])))
    return '<div class="news-grid%s">' % (' news-one' if len(out) == 1 else '') + ''.join(out) + '</div>'

def hero_title():
    t = esc(HOME.get('hero_title', ''))
    t = re.sub(r'(^|\s)(\S{1,2}) (?=\[)', lambda m: m.group(1) + m.group(2) + '&nbsp;', t)  # «на», «и», «в» не висят в конце строки
    t = t.replace('[WB]', '<span class="mk mk-wb">Wildberries</span>').replace('[OZON]', '<span class="mk mk-ozon">Ozon</span>')
    return re.sub(r'\[([^\]]+)\]', r'<span class="lead-word">\1</span>', t)

def hero_stats():
    return ''.join('<div class="num"><b>%s</b><span>%s</span></div>' % (stat_value(i['value']), esc(i.get('label', ''))) for i in STATS[:2])

def video_card():
    """Видео-визитка на первом экране. Пока видео нет — обложка «скоро» с фото основателя."""
    url, poster = VIDEO.get('url') or S.get('video_url', ''), VIDEO.get('poster') or S.get('video_poster', '')
    cap = esc(VIDEO.get('caption') or S.get('video_caption') or 'Видео-визитка основателя')
    who = esc('%s · %s' % (F.get('name', ''), 'основатель компании'))
    face = media(F.get('photo')) or BASE + 'img/artem.webp'
    bg = ('<img class="vc-poster" src="%s" alt="" decoding="async" fetchpriority="high">' % esc(media(poster))) if poster else \
         ('<span class="vc-rings" aria-hidden="true"></span><span class="vc-face"><img src="%s" alt="" width="336" height="336" decoding="async"></span>' % esc(face))
    body = '%s<span class="vplay" aria-hidden="true"><i></i>{{icon:play}}</span><span class="vcap"><b>%s</b><span>%s</span></span>' % (bg, cap, who)
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

def cta_band(title=None, text=None, button=None):
    t = TX.get('cta') or {}
    return ('<section class="sec" aria-label="Бесплатная консультация"><div class="wrap"><div class="cta-band" data-reveal>'
            '<div><h2 class="heading-3">%s</h2><p>%s</p></div>'
            '<div class="hero-cta"><a class="btn btn-primary btn-lg btn-shine" href="{{base}}kontakty/" data-lead><span>%s</span>{{icon:arrow-right}}</a></div></div></div></section>'
            % (esc(title or t.get('title') or 'Начните с бесплатной консультации'), esc(text or t.get('text') or ''), esc(button or t.get('button') or 'Записаться')))

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
        '<div style="margin-top:32px">' + cases_html(s) + '</div>'
        '<h2 class="heading-5" style="margin-top:64px">Другие услуги</h2><div class="others">' + others + '</div></div></section>' + cta_band())

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

NAV = [('uslugi', 'uslugi/', 'Услуги'), ('novosti', 'novosti/', 'Новости'), ('o-nas', 'o-nas/', 'О компании'),
       ('voprosy', 'voprosy/', 'Вопросы'), ('kontakty', 'kontakty/', 'Контакты')]
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

def page(key, title, desc, body, sticky=True, scripts=('site',), head=''):
    def a(k, url, label, li=False):
        x = '<a href="{{base}}%s"%s>%s</a>' % (url, ' aria-current="page"' if k == key else '', label)
        return '<li>%s</li>' % x if li else x
    nav = ''.join(a(*n) for n in NAV)
    out = LAYOUT
    for k, v in (('{{content}}', body), ('{{nav}}', nav), ('{{mnav}}', a('home', '', 'Главная') + nav),
                 ('{{fnav}}', a('home', '', 'Главная', True) + ''.join(a(*n, li=True) for n in NAV) + a('sait', 'sait/', 'Сайт для селлера', True)),
                 ('{{fdocs}}', ''.join('<li><a href="{{base}}dokumenty/%s/">%s</a></li>' % (d['slug'], esc(d['title'])) for d in DOCS)),
                 ('{{footer_text}}', esc(S.get('footer_text', ''))), ('{{widgets}}', widgets_html()),
                 ('{{robots}}', 'index, follow' if INDEX else 'noindex, nofollow'),
                 ('{{title}}', esc(title)), ('{{desc}}', esc(desc)), ('{{head}}', head),
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
HP = re.split(r'<!--@section ([a-z0-9-]+)-->', (SRC / 'pages' / 'home.html').read_text(encoding='utf-8'))
HOME_SEC = {HP[i]: HP[i + 1] for i in range(1, len(HP), 2)}
SECTIONS = {
    '{{bento}}': bento_html(), '{{stats}}': stats_html(), '{{tagline}}': tagline_html(), '{{cta-band}}': cta_band(),
    '{{clients}}': clients_html(), '{{news-cards}}': news_cards(NEWS[:3]), '{{news-all}}': news_cards(NEWS), '{{who-cards}}': who_html(),
    '{{founder-home}}': founder_html('<a class="btn btn-ghost" href="{{base}}o-nas/"><span>О компании</span>{{icon:arrow-right}}</a>'),
    '{{founder-about}}': founder_html('<a class="btn btn-primary btn-shine" href="{{base}}kontakty/" data-lead><span>Получить бесплатную консультацию</span>{{icon:arrow-right}}</a>'),
    '{{steps}}': steps_html(STEPS.get('items') or []), '{{site-steps}}': steps_html(STEPS.get('site') or []), '{{service-options}}': OPTIONS,
    '{{faq-all}}': faq_html(FAQ), '{{faq-home}}': faq_html([i for i in FAQ if i.get('topic') != 'site'][:6]), '{{faq-site}}': faq_html([i for i in FAQ if i.get('topic') == 'site']), '{{consents-form}}': consents('f'),
    '{{why}}': ''.join('<div class="card" data-reveal style="--d:%dms"><span class="ic">%s</span><p>%s</p></div>' % (k * 60, icon(w.get('icon')), esc(w.get('text', '')))
                       for k, w in enumerate((TX.get('o_nas') or {}).get('why') or [])),
    '{{meeting}}': ''.join('<li>%s<span>%s</span></li>' % (icon(MEET_ICONS[k % len(MEET_ICONS)]), esc(t)) for k, t in enumerate((TX.get('kontakty') or {}).get('meeting') or [])),
    '{{proj-feature}}': proj_feature_html(), '{{demos}}': demos_html(), '{{viz:sait}}': VIZ.get('sait', ''),
    '{{hero_chip}}': esc(HOME.get('hero_chip', '')), '{{hero_title}}': hero_title(), '{{hero_lead}}': esc(HOME.get('hero_lead', '')),
    '{{hero_cta}}': esc(HOME.get('hero_cta') or 'Получить бесплатную консультацию'), '{{hero-stats}}': hero_stats(), '{{video-card}}': video_card(),
    '{{who_chip}}': esc(HOME.get('who_chip', '')), '{{who_title}}': esc(HOME.get('who_title', '')),
    '{{services_chip}}': esc(HOME.get('services_chip', '')), '{{services_title}}': esc(HOME.get('services_title', '')),
    '{{news_chip}}': esc(HOME.get('news_chip', '')), '{{news_title}}': esc(HOME.get('news_title', '')),
    '{{phero-bg}}': '<div class="grid-bg" aria-hidden="true"></div><div class="glow glow-a" aria-hidden="true"></div>',
    '{{doc-links}}': ''.join('<a href="{{base}}dokumenty/%s/">%s</a>' % (d['slug'], esc(d['title'])) for d in DOCS),
}
def fill(text, crumb=None):
    for _ in range(2):  # блоки могут содержать другие блоки (например, фон в шапке услуги)
        for k, v in SECTIONS.items():
            text = text.replace(k, v)
    text = re.sub(r'\{\{t:([a-z_]+)\.([a-z_]+)\}\}', lambda m: esc(str((TX.get(m.group(1)) or {}).get(m.group(2), ''))), text)
    return text.replace('{{crumbs}}', crumbs(crumb) if crumb else '')

order = [b.get('type') if isinstance(b, dict) else b for b in HOME.get('sections') or []]
home = fill(HOME_SEC['hero'] + ''.join(HOME_SEC.get(t, '') for t in order))
parts = re.split(r'<!--@page ([a-z0-9-]+)-->', (SRC / 'pages' / 'inner.html').read_text(encoding='utf-8'))
inner = {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}
FAQ_LD = '<script type="application/ld+json">%s</script>' % json.dumps({'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
    {'@type': 'Question', 'name': str(i['q']), 'acceptedAnswer': {'@type': 'Answer', 'text': re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', answer_html(i.get('a'))))).strip()}}
    for i in FAQ]}, ensure_ascii=False).replace('</', '<\\/').replace('{{', '{\\u007b')

def news_post(n):
    if n['video']:
        top = '<div class="video-box">%s</div>' % video_html(n['video'], n['cover'])
    elif n['cover']:
        top = '<figure class="figure"><img src="%s" alt="" decoding="async"></figure>' % esc(media(n['cover']))
    else:
        top = ''
    more = [x for x in NEWS if x['slug'] != n['slug']][:3]
    return ('<section class="phero"><div class="wrap narrow">%s<time class="chip" datetime="%s">%s</time><h1 class="heading-2 grad">%s</h1>%s</div></section>'
            '<section class="sec sec-tight"><div class="wrap narrow">%s<article class="prose">%s</article>'
            '<a class="link-arrow link-acc" href="{{base}}novosti/" style="margin-top:40px"><span class="flip">{{icon:arrow-right}}</span><span>Все новости</span></a></div></section>'
            % (crumbs(('Новости', '{{base}}novosti/'), (n['title'], None)), esc(n['date']), ru_date(n['date']), esc(n['title']),
               '<p class="lead">%s</p>' % esc(n['excerpt']) if n['excerpt'] else '', top, md(n['body'])) +
            ('<section class="sec" style="padding-top:0"><div class="wrap"><h2 class="heading-5">Читайте также</h2><div style="margin-top:24px">%s</div></div></section>' % news_cards(more) if more else '') + cta_band())

def doc_page(d):
    nav = ''.join('<li><a href="{{base}}dokumenty/%s/"%s>%s</a></li>' % (o['slug'], ' aria-current="page"' if o['slug'] == d['slug'] else '', esc(o['title'])) for o in DOCS)
    return ('<section class="phero"><div class="wrap">%s<h1 class="heading-2 grad">%s</h1></div></section>'
            '<section class="sec sec-tight"><div class="wrap doc-layout"><article class="prose card doc">%s</article><aside class="doc-nav card"><b>Документы</b><ul>%s</ul></aside></div></section>'
            % (crumbs(('Документы', '{{base}}dokumenty/'), (d['title'], None)), esc(d['title']), md(d['body']), nav))

DOCS_LIST = ('<section class="phero">{{phero-bg}}<div class="wrap">%s<h1 class="heading-1 grad">Документы</h1><p class="lead">Оферта, политика обработки персональных данных и согласия.</p></div></section>'
             '<section class="sec sec-tight"><div class="wrap"><div class="doc-list">%s</div></div></section>'
             % (crumbs(('Документы', None)), ''.join('<a class="doc-item" href="{{base}}dokumenty/%s/" data-reveal><span class="ic">{{icon:file-text}}</span><b>%s</b>{{icon:arrow-right}}</a>'
                                                     % (d['slug'], esc(d['title'])) for d in DOCS)))

PAGES_OUT = [
    ('', page('home', '%s — рост продаж на Wildberries и Ozon' % COMPANY,
              'Аналитика, реклама, дизайн карточек, SEO и сопровождение селлеров Wildberries и Ozon. Начните с бесплатной консультации.', home)),
    ('uslugi/', page('uslugi', 'Услуги — %s' % COMPANY, 'Бизнес-трекер, реклама, дизайн и SEO карточек, фото и видео, работа с покупателями, подбор ниши.', fill(inner['uslugi'], ('Услуги', None)))),
    ('sait/', page('sait', 'Сайт для селлера — %s' % COMPANY, 'Свой интернет-магазин для селлера Wildberries и Ozon: админ-панель, Метрика, доставка, оплата и заказы в Телеграм.', fill(inner['sait'], ('Сайт для селлера', None)))),
    ('o-nas/', page('o-nas', 'О компании — %s' % COMPANY, (TX.get('o_nas') or {}).get('lead', ''), fill(inner['o-nas'], ('О компании', None)))),
    ('voprosy/', page('voprosy', 'Частые вопросы — %s' % COMPANY, 'Ответы о работе с Wildberries и Ozon, оплате и рекламе.', fill(inner['voprosy'], ('Вопросы', None)), head=FAQ_LD)),
    ('kontakty/', page('kontakty', 'Бесплатная консультация — %s' % COMPANY, 'Запишитесь на бесплатную онлайн-встречу с аналитиком маркетплейсов.', fill(inner['kontakty'], ('Контакты', None)), sticky=False, scripts=('voice', 'site'))),
    ('novosti/', page('novosti', 'Новости — %s' % COMPANY, (TX.get('novosti') or {}).get('lead', ''), fill(inner['novosti'], ('Новости', None)))),
    ('dokumenty/', page('dokumenty', 'Документы — %s' % COMPANY, 'Оферта, политика обработки персональных данных и согласия.', fill(DOCS_LIST), sticky=False)),
] + [('uslugi/%s/' % s['slug'], page('uslugi', '%s — %s' % (s['title'], COMPANY), s.get('short', ''), fill(service_body(s)))) for s in SERVICES if s['slug'] != 'sait'] \
  + [('novosti/%s/' % n['slug'], page('novosti', '%s — %s' % (n['title'], COMPANY), n['excerpt'] or n['title'], fill(news_post(n)))) for n in NEWS] \
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
    _f.write_text(_f.read_text(encoding='utf-8').replace('{{base}}', BASE).replace('{{site}}', SITE).replace('{{ver}}', VER), encoding='utf-8')
(OUT / 'js').mkdir()
for name in ('site', 'voice', 'brief'):
    (OUT / 'js' / (name + '.js')).write_text(tokens((SRC / 'js' / (name + '.js')).read_text(encoding='utf-8')), encoding='utf-8')
for path, text in PAGES_OUT:
    (OUT / path).mkdir(parents=True, exist_ok=True)
    (OUT / path / 'index.html').write_text(text, encoding='utf-8')
(OUT / '404.html').write_text(page('404', 'Страница не найдена — %s' % COMPANY, 'Такой страницы нет.', fill(inner['404']), sticky=False), encoding='utf-8')
brief = tokens((SRC / 'brief' / 'index.html').read_text(encoding='utf-8')).replace('{{css}}', CSS + CSS_BRIEF)
(OUT / 'brief').mkdir()
(OUT / 'brief' / 'index.html').write_text(brief, encoding='utf-8')
(OUT / 'favicon.svg').write_text(MARK.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ', 1).replace(' aria-hidden="true" focusable="false"', ''), encoding='utf-8')
(OUT / 'robots.txt').write_text('User-agent: *\n%s\n' % ('Allow: /' if INDEX else 'Disallow: /'), encoding='utf-8')
(OUT / '.nojekyll').write_text('', encoding='utf-8')
sizes = sorted(((p.stat().st_size, str(p.relative_to(OUT))) for p in OUT.rglob('index.html')), reverse=True)
print('built', VER, '→', OUT, '| страниц:', len(PAGES_OUT) + 2, '| новостей:', len(NEWS), '| документов:', len(DOCS), '| своих страниц:', len(PAGES),
      '| самая тяжёлая:', sizes[0][1], sizes[0][0] // 1024, 'КБ | CSS:', len(CSS) // 1024, 'КБ')
