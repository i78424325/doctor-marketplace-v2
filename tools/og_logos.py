# Запуск: python3 tools/og_logos.py — пересобирает src/img/og.png и логотипы в «для Артёма».
# Генератор og.png (превью ссылки) и PNG-логотипов OS Ecom для Артёма.
# Логотипы берутся прямо из build.py сайта, чтобы картинки совпадали с сайтом один в один.
import os, re, subprocess, sys, urllib.parse

PROJ = '/Users/sotnik/Desktop/Доктор Маркетплейс'
import tempfile
HERE = tempfile.mkdtemp(prefix='dm-og-')  # временные html и профиль Chrome — не в проекте
CH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
OUT_DIR = os.path.join(PROJ, 'для Артёма')

src = open(os.path.join(PROJ, 'build.py'), encoding='utf-8').read()
def const(name):
    m = re.search(r'^%s\s*=\s*\((.*?)\)\n' % name, src, re.S | re.M)
    return ''.join(re.findall(r"'([^']*)'", m.group(1)))
MARK, OSECOM = const('MARK'), const('OSECOM')

def font_css():
    rules = []
    for sub, rng in (('cyrillic-ext', 'U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F'),
                     ('cyrillic', 'U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116'),
                     ('latin-ext', 'U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+1E00-1E9F, U+20A0-20AB, U+20AD-20C4, U+2C60-2C7F, U+A720-A7FF'),
                     ('latin', 'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD')):
        url = 'file://' + urllib.parse.quote(os.path.join(PROJ, 'src/fonts/manrope-%s.woff2' % sub))
        rules.append("@font-face{font-family:'Manrope';font-weight:400 700;src:url('%s') format('woff2');unicode-range:%s}" % (url, rng))
    return '\n'.join(rules)

BASE = '<!doctype html><html><head><meta charset="utf-8"><style>%s\n*{margin:0;padding:0;box-sizing:border-box}html,body{background:transparent}body{font-family:Manrope,system-ui,sans-serif;-webkit-font-smoothing:antialiased}%s</style></head><body>%s</body></html>'

LINE = 'M0 180 L80 180 L98 162 L112 180 L140 180 L156 104 L172 214 L188 150 L202 180 L240 180 C310 178 352 160 392 128 S478 66 552 30'
OG_CSS = '''
body{width:1200px;height:630px;background:#000;color:#F4F6F5;position:relative;overflow:hidden}
.glow{position:absolute;width:760px;height:420px;right:-180px;bottom:-120px;border-radius:50%;background:#3EF0A6;opacity:.16;filter:blur(120px)}
.card{position:absolute;inset:0;padding:64px 72px;display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:16px;font-size:28px;line-height:36px;font-weight:600}
.brand svg{width:56px;height:56px}
.chip{margin-left:auto;font-size:18px;line-height:28px;font-weight:600;color:#A3ABA8;padding:8px 20px;border-radius:9999px;box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.14)}
h1{margin-top:56px;max-width:780px;font-size:64px;line-height:68px;font-weight:600;letter-spacing:-.02em;background:linear-gradient(90deg,#FFFFFF,#9B9B9B);-webkit-background-clip:text;background-clip:text;color:transparent}
.mk{position:relative;white-space:nowrap}
.mk::after{content:"";position:absolute;left:-4px;right:-4px;bottom:.06em;height:.34em;border-radius:8px;opacity:.6;z-index:-1}
.wb::after{background:#CB11AB}.oz::after{background:#005BFF}
h1 span.t{position:relative;z-index:1}
.foot{margin-top:auto;display:flex;align-items:flex-end;gap:40px}
.stat b{display:block;font-size:40px;line-height:40px;font-weight:700;color:#3EF0A6}
.stat span{display:block;margin-top:8px;font-size:18px;line-height:24px;color:#A3ABA8}
.cta{margin-left:auto;display:inline-flex;align-items:center;gap:12px;padding:16px 28px;border-radius:9999px;background:#3EF0A6;color:#03130C;font-size:22px;line-height:28px;font-weight:600;box-shadow:0 0 48px rgba(62,240,166,.45)}
.chart{position:absolute;right:48px;top:172px;width:400px;height:171px;overflow:visible}
.chart .line{fill:none;stroke:#3EF0A6;stroke-width:5;stroke-linecap:round;stroke-linejoin:round;filter:drop-shadow(0 0 10px rgba(62,240,166,.7))}
.chart .pt{fill:#3EF0A6;filter:drop-shadow(0 0 12px #3EF0A6)}
'''
ARROW = '<svg width="24" height="24" viewBox="0 0 256 256" fill="currentColor"><path d="M221.66,133.66l-72,72a8,8,0,0,1-11.32-11.32L196.69,136H40a8,8,0,0,1,0-16H196.69L138.34,61.66a8,8,0,0,1,11.32-11.32l72,72A8,8,0,0,1,221.66,133.66Z"/></svg>'
OG_BODY = ('<div class="glow"></div>'
           '<svg class="chart" viewBox="0 0 560 240"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3EF0A6" stop-opacity=".28"/><stop offset="1" stop-color="#3EF0A6" stop-opacity="0"/></linearGradient></defs>'
           '<path d="%s L552 240 L0 240 Z" fill="url(#g)"/><path class="line" d="%s"/><circle class="pt" r="9" cx="552" cy="30"/></svg>'
           '<div class="card"><div class="brand">%s<span>Доктор Маркетплейс</span><span class="chip">Wildberries · Ozon</span></div>'
           '<h1>Выводим магазины<br>на <span class="mk wb">Wildberries</span> и <span class="mk oz">Ozon</span><br>в лидеры&nbsp;ниши</h1>'
           '<div class="foot"><div class="stat"><b>6&nbsp;000+</b><span>кейсов</span></div><div class="stat"><b>93%%</b><span>успешных кейсов</span></div>'
           '<div class="stat"><b>5+</b><span>лет на маркетплейсах</span></div><span class="cta">Бесплатная консультация%s</span></div></div>') % (LINE, LINE, MARK.replace('aria-hidden="true" focusable="false"', ''), ARROW)

LIGHT = (OSECOM.replace('fill="#141414" stroke="#FFFFFF" stroke-opacity=".18"', 'fill="#FFFFFF" stroke="#0B0F0D" stroke-opacity=".16"')
               .replace('#F4F6F5', '#0B0F0D').replace('#A3ABA8', '#5C6461').replace('#3EF0A6', '#0FB57A'))
ICON = re.sub(r'viewBox="0 0 140 40"', 'viewBox="0 0 40 40"', re.sub(r'<text.*?</text>', '', OSECOM))
LOGO_CSS = 'body{width:%dpx;height:%dpx;display:grid;place-items:center}svg{width:%dpx;height:%dpx;display:block}'

def shoot(name, html, w, h, out, transparent, scale=1):
    path = os.path.join(HERE, name + '.html')
    open(path, 'w', encoding='utf-8').write(html)
    args = [CH, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=%s' % scale,
            '--window-size=%d,%d' % (w, h), '--virtual-time-budget=4000', '--user-data-dir=' + os.path.join(HERE, 'prof'),
            '--screenshot=' + out]
    if transparent:
        args.append('--default-background-color=00000000')
    subprocess.run(args + ['file://' + urllib.parse.quote(path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('ok', out)

os.makedirs(OUT_DIR, exist_ok=True)
css = font_css()
shoot('og', BASE % (css, OG_CSS, OG_BODY), 1200, 630, os.path.join(PROJ, 'src/img/og.png'), False)
shoot('logo-dark', BASE % (css, LOGO_CSS % (1400, 400, 1400, 400), OSECOM), 1400, 400, os.path.join(OUT_DIR, 'OS Ecom — логотип для тёмного фона.png'), True)
shoot('logo-light', BASE % (css, LOGO_CSS % (1400, 400, 1400, 400), LIGHT), 1400, 400, os.path.join(OUT_DIR, 'OS Ecom — логотип для светлого фона.png'), True)
shoot('icon', BASE % (css, LOGO_CSS % (512, 512, 512, 512), ICON), 512, 512, os.path.join(OUT_DIR, 'OS Ecom — значок 512×512.png'), True)
