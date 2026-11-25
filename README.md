# Сайт «Доктор Маркетплейс»

- `content/` — всё, что правится в админке (`/admin`): контакты, тексты, цены, кейсы, новости, документы, страницы-конструктор.
- `src/` — шаблоны, стили, скрипты, иконки, картинки, сама админка (`src/admin`).
- `build.py` — сборка: `python3 build.py` → готовый сайт в `site/` (не хранится в репозитории).
- `.github/workflows/pages.yml` — после каждого изменения сайт собирается и публикуется на GitHub Pages.

Свой домен: `SITE_BASE=/ SITE_URL=https://домен python3 build.py`, в `src/admin/config.yml` поменять `repo`, `site_url`, `display_url`.
