# Перевод картинок сайта в WebP: меньше вес — быстрее открывается на телефоне.
# Запуск: "/Users/sotnik/Desktop/Авито бот/.venv/bin/python" tools/images.py  (нужен Pillow с WebP)
from pathlib import Path
from PIL import Image

IMG = Path(__file__).resolve().parent.parent / 'src' / 'img'

def save(src, out, size=None, q=78):
    im = Image.open(src).convert('RGB')
    if size:
        im.thumbnail(size, Image.LANCZOS)
    im.save(out, 'WEBP', quality=q, method=6)
    print('%-28s %6d → %6d байт  %s' % (out.name, src.stat().st_size, out.stat().st_size, im.size))

for f in sorted((IMG / 'shots').glob('*.jpg')):
    save(f, f.with_suffix('.webp'), (480, 960), 74)
save(IMG / 'artem.jpg', IMG / 'artem.webp', (336, 336), 82)
save(IMG / 'artem.jpg', IMG / 'artem-96.webp', (96, 96), 82)
