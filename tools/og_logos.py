# Запуск: python3 tools/og_logos.py — пересобирает src/img/og.png (картинка-превью ссылки) ЭТОЙ копии сайта.
# Значок берётся прямо из build.py, чтобы превью совпадало с сайтом. Логотипы OS Ecom для Артёма делаются в основном проекте.
import os, re, subprocess, tempfile, urllib.parse

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # папка этой копии сайта, не основного проекта
HERE = tempfile.mkdtemp(prefix='dm-og-')  # временные html и профиль Chrome — не в проекте
CH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

src = open(os.path.join(PROJ, 'build.py'), encoding='utf-8').read()
def const(name):
    m = re.search(r'^%s\s*=\s*\((.*?)\)\n' % name, src, re.S | re.M)
    return ''.join(re.findall(r"'([^']*)'", m.group(1)))
MARK = const('MARK')

def font_css():
    rules = []
    for sub, rng in (('cyrillic-ext', 'U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F'),
                     ('cyrillic', 'U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116'),
                     ('latin-ext', 'U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+1E00-1E9F, U+20A0-20AB, U+20AD-20C4, U+2C60-2C7F, U+A720-A7FF'),
                     ('latin', 'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD')):
        url = 'file://' + urllib.parse.quote(os.path.join(PROJ, 'src/fonts/manrope-%s.woff2' % sub))
        rules.append("@font-face{font-family:'Manrope';font-weight:400 800;src:url('%s') format('woff2');unicode-range:%s}" % (url, rng))
    return '\n'.join(rules)

LINE = 'M0 180 L80 180 L98 162 L112 180 L140 180 L156 104 L172 214 L188 150 L202 180 L240 180 C310 178 352 160 392 128 S478 66 552 30'
CSS = '''
*{margin:0;padding:0;box-sizing:border-box}
body{width:1200px;height:630px;background:#F4F3EF;color:#121C16;font-family:Manrope,system-ui,sans-serif;-webkit-font-smoothing:antialiased;position:relative;overflow:hidden}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(16,32,24,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(16,32,24,.05) 1px,transparent 1px);background-size:56px 56px;-webkit-mask-image:radial-gradient(ellipse 80% 70% at 70% 20%,#000 30%,transparent 75%)}
.g1{position:absolute;width:820px;height:560px;right:-260px;top:-260px;border-radius:50%;background:radial-gradient(closest-side,rgba(78,182,121,.32),transparent)}
.g2{position:absolute;width:640px;height:640px;left:-300px;bottom:-360px;border-radius:50%;background:radial-gradient(closest-side,rgba(201,162,87,.26),transparent)}
.card{position:absolute;inset:0;padding:60px 72px;display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:16px;font-size:28px;line-height:36px;font-weight:700}
.brand svg{width:56px;height:56px}
.chip{margin-left:auto;font-size:18px;line-height:28px;font-weight:700;color:#56625C;padding:8px 20px;border-radius:9999px;background:#FFFFFF;box-shadow:inset 0 0 0 1.5px rgba(16,32,24,.12)}
h1{margin-top:52px;max-width:760px;font-size:66px;line-height:72px;font-weight:700;letter-spacing:-.035em}
.wb{background:linear-gradient(95deg,#CB11AB,#A116BE 55%,#7B1FC4);-webkit-background-clip:text;background-clip:text;color:transparent}
.oz{color:#005BFF}
.lw{position:relative;white-space:nowrap;color:#13804A}
.lw::after{content:"";position:absolute;left:1%;right:-10px;bottom:-12px;height:6px;border-radius:9px;background:linear-gradient(90deg,rgba(78,182,121,.16),#4EB679 62%,#237A4B);transform:rotate(-2.6deg);transform-origin:left center}
.lw::before{content:"";position:absolute;right:-18px;bottom:6px;width:12px;height:12px;border-radius:50%;background:#FFFFFF;box-shadow:0 0 0 4px #4EB679,0 0 18px 6px rgba(78,182,121,.55)}
.foot{margin-top:auto;display:flex;align-items:flex-end;gap:44px}
.stat b{display:block;font-size:42px;line-height:44px;font-weight:800;letter-spacing:-.04em;color:#0F3B2A}
.stat b::after{content:"";display:block;width:32px;height:4px;margin-top:12px;border-radius:2px;background:linear-gradient(90deg,#C9A257,#E4C27D)}
.stat span{display:block;margin-top:10px;font-size:18px;line-height:24px;color:#56625C}
.cta{margin-left:auto;display:inline-flex;align-items:center;gap:12px;padding:18px 30px;border-radius:9999px;background:#4EB679;color:#0B1A12;font-size:22px;line-height:28px;font-weight:700;box-shadow:inset 0 1px 0 rgba(255,255,255,.45),0 18px 40px -16px rgba(35,122,75,.8)}
.chart{position:absolute;right:56px;top:176px;width:380px;height:163px;overflow:visible}
.chart .line{fill:none;stroke:#4EB679;stroke-width:6;stroke-linecap:round;stroke-linejoin:round}
.chart .pt{fill:#237A4B;stroke:#FFFFFF;stroke-width:4}
'''
ARROW = '<svg width="24" height="24" viewBox="0 0 256 256" fill="currentColor"><path d="M221.66,133.66l-72,72a8,8,0,0,1-11.32-11.32L196.69,136H40a8,8,0,0,1,0-16H196.69L138.34,61.66a8,8,0,0,1,11.32-11.32l72,72A8,8,0,0,1,221.66,133.66Z"/></svg>'
BODY = ('<div class="grid"></div><div class="g1"></div><div class="g2"></div>'
        '<svg class="chart" viewBox="0 0 560 240"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4EB679" stop-opacity=".3"/><stop offset="1" stop-color="#4EB679" stop-opacity="0"/></linearGradient></defs>'
        '<path d="%s L552 240 L0 240 Z" fill="url(#g)"/><path class="line" d="%s"/><circle class="pt" r="11" cx="552" cy="30"/></svg>'
        '<div class="card"><div class="brand">%s<span>Доктор Маркетплейс</span><span class="chip">Wildberries · Ozon</span></div>'
        '<h1>Выводим магазины<br>на <span class="wb">Wildberries</span> и <span class="oz">Ozon</span><br>в&nbsp;<span class="lw">лидеры ниши</span></h1>'
        '<div class="foot"><div class="stat"><b>6&nbsp;000+</b><span>кейсов</span></div><div class="stat"><b>93%%</b><span>успешных кейсов</span></div>'
        '<div class="stat"><b>5+</b><span>лет на маркетплейсах</span></div><span class="cta">Бесплатная консультация%s</span></div></div>') % (LINE, LINE, MARK.replace('aria-hidden="true" focusable="false"', ''), ARROW)

html = '<!doctype html><html><head><meta charset="utf-8"><style>%s\n%s</style></head><body>%s</body></html>' % (font_css(), CSS, BODY)
path = os.path.join(HERE, 'og.html')
open(path, 'w', encoding='utf-8').write(html)
out = os.path.join(PROJ, 'src/img/og.png')
subprocess.run([CH, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1', '--window-size=1200,630',
                '--virtual-time-budget=4000', '--user-data-dir=' + os.path.join(HERE, 'prof'), '--screenshot=' + out, 'file://' + urllib.parse.quote(path)],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print('ok', out)
