# frontend — фронтенд на Nuxt 4

Клиентская часть: **Nuxt 4 + Nuxt UI 4 + Nuxt Content 3 + Tailwind CSS 4 + TypeScript**.
Внутри лендинг, страница тарифов, документация, блог, changelog и страницы входа/регистрации.
Основан на официальном [Nuxt SaaS Template](https://github.com/nuxt-ui-templates/saas).

Парный проект — [`../backend`](../backend/README.md) (FastAPI, вход через API Gateway на `:8000`).

> **Важно: сейчас фронтенд с бэкендом не связан.** Страницы `login` и `signup` — заглушки:
> форма валидируется через `zod`, но `onSubmit` только пишет в консоль, а кнопки Google/GitHub
> показывают toast. Запросов к API в коде нет. Как подключить бэкенд — в разделе
> [Интеграция с бэкендом](#интеграция-с-бэкендом).

## Требования

| Что     | Версия                                                   |
|---------|----------------------------------------------------------|
| Node.js | 22 (на ней работает CI, `.github/workflows/ci.yml`)      |
| pnpm    | 12.4.1 (закреплён в `packageManager` в `package.json`)   |

Используйте **только pnpm**: `pnpm-lock.yaml` в git, а `pnpm-workspace.yaml` задаёт `allowBuilds`
(какие зависимости вправе запускать скрипты сборки) и `overrides`. `npm install` / `yarn` создадут
чужой lock-файл — не коммитьте его.

## Быстрый старт

```bash
pnpm install        # заодно выполнит `nuxt prepare` (postinstall) и сгенерирует .nuxt/
pnpm dev            # http://localhost:3000
```

| Команда          | Что делает                                                        |
|------------------|-------------------------------------------------------------------|
| `pnpm dev`       | dev-сервер с hot reload                                           |
| `pnpm build`     | production-сборка в `.output/`                                    |
| `pnpm preview`   | локальный запуск production-сборки                                |
| `pnpm lint`      | ESLint (включая правила Tailwind — неизвестные классы это ошибка) |
| `pnpm typecheck` | `nuxt typecheck` (vue-tsc)                                        |

CI запускает `lint` и `typecheck` на каждый push. Перед коммитом прогоните обе команды локально:
упавший CI блокирует слияние.

## Переменные окружения

`cp .env.example .env` (`.env` в git не попадает).

| Переменная             | Назначение                                                        |
|------------------------|-------------------------------------------------------------------|
| `NUXT_PUBLIC_SITE_URL` | публичный URL сайта; нужен `nuxt-og-image` при `nuxt generate`    |

Правило Nuxt: переменная `NUXT_PUBLIC_*` попадает в клиентский бандл и **видна всем**.
Секреты (ключи, пароли) с этим префиксом класть нельзя. Приватные значения — `NUXT_*` без `PUBLIC`,
они доступны только на сервере (Nitro) через `useRuntimeConfig()`.

## Структура

```
frontend/
├── app/                         исходники приложения (srcDir Nuxt 4)
│   ├── app.vue                    корень: UApp, навигация и поиск по документации
│   ├── app.config.ts              тема Nuxt UI (primary: blue, neutral: slate)
│   ├── error.vue                  страница ошибки
│   ├── assets/css/main.css        Tailwind + Nuxt UI, палитра и тёмная тема
│   ├── layouts/                   default, docs, auth
│   ├── pages/                     маршруты (file-based routing)
│   │   ├── index.vue, pricing.vue, login.vue, signup.vue
│   │   ├── blog.vue + blog/       список и статья ([slug].vue)
│   │   ├── changelog/index.vue
│   │   └── docs/[...slug].vue     документация из content/1.docs
│   ├── components/                AppHeader/Footer/Logo, фоны, OgImage/, content/ (MDC-компоненты)
│   ├── utils/links.ts             ссылки главной навигации (auto-import)
│   └── types/index.d.ts           общие типы (BlogPost)
├── content/                     контент в Markdown/YAML (Nuxt Content)
├── content.config.ts            коллекции контента и их zod-схемы
├── public/                      статика как есть (favicon.ico)
├── nuxt.config.ts               модули, prerender, routeRules, ESLint
├── eslint.config.mjs            ESLint + better-tailwindcss
└── .github/workflows/ci.yml     lint + typecheck
```

Не правьте и не коммитьте `.nuxt/`, `.output/`, `.data/`, `node_modules/` — это артефакты сборки (они в `.gitignore`).
Если IDE ругается на неизвестные auto-import'ы или типы — выполните `pnpm postinstall` (`nuxt prepare`).

## Контент

Тексты сайта живут в `content/`, а не в компонентах. Схема каждой коллекции описана в `content.config.ts`
через `zod`; при несоответствии front-matter схеме Nuxt Content сообщит об этом при сборке.

| Раздел          | Файлы                                | Страница                         |
|-----------------|--------------------------------------|----------------------------------|
| Главная         | `content/0.index.yml`                | `pages/index.vue`                |
| Документация    | `content/1.docs/**`                  | `pages/docs/[...slug].vue`       |
| Тарифы          | `content/2.pricing.yml`              | `pages/pricing.vue`              |
| Блог            | `content/3.blog/*.md`, `3.blog.yml`  | `pages/blog*`                    |
| Changelog       | `content/4.changelog/*.md`           | `pages/changelog/index.vue`      |

Числовой префикс в имени файла (`1.`, `2.`…) задаёт порядок в навигации и не попадает в URL.
Чтобы добавить статью блога, создайте `content/3.blog/N.<slug>.md` с полями из схемы `blog` в `content.config.ts`.

## Соглашения

- **TypeScript везде**: `<script setup lang="ts">`, типы общих сущностей — в `app/types/`.
- **Стили — только классы Tailwind и компоненты Nuxt UI** (`UButton`, `UPageCard`, `UAuthForm`…).
  Кастомный CSS — в `assets/css/main.css`. Линтер помечает неизвестные Tailwind-классы как ошибку;
  для осознанных исключений список `ignore` в `eslint.config.mjs`.
- **Иконки** — через Iconify, коллекции `lucide` и `simple-icons` уже подключены (`i-lucide-book`, `i-simple-icons-github`).
- **Формы** — `zod` + `UForm` / `UAuthForm`, как в `pages/login.vue`.
- **Стиль кода** задаёт `@nuxt/eslint` (stylistic): без trailing comma, скобки в стиле `1tbs`, отступы — `.editorconfig`.
- Компоненты — `PascalCase`, auto-import из `app/components`; composables и утилиты — из `app/composables`, `app/utils`.

## Интеграция с бэкендом

Бэкенд отдаёт всё через один вход — API Gateway: `http://localhost:8000/api/v1/…`.
Эндпоинты авторизации (`auth_service`): `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`,
`GET /users/me`. Вход возвращает пару токенов (`access_token`, `refresh_token`), остальные запросы идут
с заголовком `Authorization: Bearer <access_token>`. Формат ошибок: `{"detail": "...", "code": "..."}`.

Рекомендуемый порядок подключения (пока не сделан):

1. **Адрес API — в `runtimeConfig`**, а не в коде: `runtimeConfig.public.apiBase`, значение из
   `NUXT_PUBLIC_API_BASE` (добавьте в `.env.example`). Адрес не секрет, поэтому `public` допустим.
2. **CORS.** Либо проксируйте `/api/**` через Nitro (`routeRules` с `proxy` на gateway) — тогда браузер
   ходит на тот же origin и CORS не нужен; либо укажите origin фронтенда в `BACKEND_CORS_ORIGINS`
   бэкенда (для dev — `http://localhost:3000`). В production `BACKEND_CORS_ORIGINS` обязателен.
3. **Единая обёртка над запросами** (`app/composables/useApi.ts` на базе `$fetch`): подстановка
   `Authorization`, единая обработка ошибок `{detail, code}`, один повтор через `/auth/refresh` при 401.
4. **Хранение токенов.** Не кладите refresh-токен в `localStorage` (доступен любому XSS). Предпочтительно
   `httpOnly`-cookie, которую выставляет серверная часть Nuxt (Nitro-роут между браузером и gateway).
5. **Защита страниц** — route middleware в `app/middleware/`, а не проверки внутри страниц.
6. В `pages/login.vue` и `pages/signup.vue` заменить `console.log` в `onSubmit` на вызов обёртки и
   показывать ошибки бэкенда через `useToast()` / ошибки полей формы.

Типы ответов бэкенда держите в `app/types/` в соответствии со схемами `auth_service/app/schemas/`;
при изменении API правьте обе стороны в одном согласованном наборе изменений.

## Что убрать из демо-материалов

Фронтенд создан из Nuxt SaaS Template и содержит демо-материалы, которые не относятся к продукту:

- `content/3.blog/`, `content/4.changelog/`, `content/1.docs/` — примеры текстов; замените или удалите
  вместе со страницами и записями в `app/utils/links.ts`;
- `app/components/TemplateMenu.vue` — меню-переключатель между официальными Nuxt-шаблонами;
- в `app/app.vue`: `titleTemplate: '%s - Nuxt SaaS template'` и `lang: 'en'`;
- `LICENSE` — лицензия исходного Nuxt SaaS Template (MIT); при смене лицензии сохраните уведомление об авторстве оригинала;
- `renovate.json` — конфиг бота обновлений, оставьте, только если Renovate подключён к репозиторию.

## Production

`pnpm build` → `.output/` (Node-сервер Nitro; для статического хостинга — `nuxt generate`).
Перед выкладкой задайте `NUXT_PUBLIC_SITE_URL`. Главная страница пререндерится, остальные ссылки
подхватываются краулером (`nitro.prerender.crawlLinks`); `/docs` редиректит на `/docs/getting-started`.

## Работа с git

Общие правила команды (ветки, коммиты, что нельзя коммитить) — в [`AI.md`](../AI.md#git-работаем-через-ветки).
Для фронтенда дополнительно: в коммит идёт `pnpm-lock.yaml` вместе с `package.json`, но не `.nuxt/`, `.output/`, `.data/`, `.env`.
