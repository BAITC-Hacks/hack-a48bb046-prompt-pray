# frontend — фронтенд на Nuxt 4

Клиентская часть: **Nuxt 4 + Nuxt UI 4 + Nuxt Content 3 + Tailwind CSS 4 + TypeScript**.
Внутри лендинг, страница тарифов, документация, блог, changelog и страницы входа/регистрации.
Основан на официальном [Nuxt SaaS Template](https://github.com/nuxt-ui-templates/saas).

Парный проект — [`../backend`](../backend/README.md) (FastAPI, вход через API Gateway на `:8000`).

> **Gateway и авторизация подключены:** вход, регистрация, восстановление сессии и выход
> работают через backend. `useApi()` передаёт access-токен и обновляет его при 401.
> Refresh-токен хранится в httpOnly-cookie через Nitro. Использование API — в разделе
> [Рабочие страницы](#рабочие-страницы) и [интеграция с бэкендом](#интеграция-с-бэкендом).

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
| `NUXT_PUBLIC_API_BASE` | URL gateway с версией API; по умолчанию `http://localhost:8000/api/v1` |

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

Перед переустановкой зависимостей или `nuxt prepare` остановите dev-сервер. Затем снова
запустите `pnpm dev`: работающий Vite может сохранить ссылки на предыдущую сборку Nuxt
и выдать `Failed to resolve import "#app-manifest"`. Если перезапуск не помог, остановите
сервер, выполните `pnpm exec nuxt cleanup`, затем `pnpm install --frozen-lockfile` и `pnpm dev`.
Используйте один dev-сервер на эту папку проекта.

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

## Рабочие страницы

- `/` — русская главная AI Sana и переходы в каталог или создание задачи.
- `/tasks/new` → `/tasks/:id` — черновик, три уточняющих вопроса, редактируемая карточка,
  расчёт рейтинга 0–100 и ручное подтверждение публикации.
- `/catalog` — поиск и сортировка по рейтингу или дате, все статусы готовности и просмотр карточки.
- `/tasks/:id/proposals` — форма идеи, плана и ссылки для команды; представитель бизнеса
  вручную выбирает одно, несколько предложений или оставляет все без выбора.
- `/account` — профиль, список собственных задач и быстрые переходы для редактирования.

Эти экраны сейчас работают в демонстрационном режиме: два примера показывают возможности
каталога, новые карточки, ответы и отклики сохраняются в браузере. Данные не видны другим
пользователям и не отправляются на сервер. Уточняющие вопросы подбираются по словам описания;
AI для задач ещё не подключён. Конкретный статус и источник данных показаны на экране.
Записи будут заменены запросами `useApi()` к backend после готовности сервиса каталога.

Рейтинг рассчитывается по семи критериям из [правил продукта](../AGENTS.md#формула-рейтинга-карточки-0100).
Поле даёт баллы, когда в нём не менее 12 символов. Низкий рейтинг не исключает задачу из каталога.

## Интеграция с бэкендом

Бэкенд отдаёт всё через один вход — API Gateway: `http://localhost:8000/api/v1/…`.
Эндпоинты авторизации (`auth_service`): `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`,
`GET /users/me`. Вход возвращает пару токенов (`access_token`, `refresh_token`), остальные запросы идут
с заголовком `Authorization: Bearer <access_token>`. Формат ошибок: `{"detail": "...", "code": "..."}`.

### Подключение gateway (T-9)

1. Задайте `NUXT_PUBLIC_API_BASE` в `.env` (пример в `.env.example`). Для production
   передайте переменную окружения при запуске сервера Nuxt. Адрес должен быть доступен
   и браузеру, и серверу Nuxt при SSR.
2. Браузер обращается напрямую к gateway. В `backend/.env` задайте
   `BACKEND_CORS_ORIGINS=http://localhost:3000` (для production — точный HTTPS origin сайта).
   Origin не содержит пути или завершающего `/`. Gateway уже разрешает localhost:3000
   в dev по умолчанию; при другом порте или использовании `127.0.0.1` добавьте этот origin.
3. Вызывайте `useApi()` внутри setup/composable; возвращаемую функцию можно использовать
   в обработчиках событий. Пути начинаются с `/`, без `/api/v1` и без полного URL.
   `body`, `query`, `headers`, `signal` и остальные опции `$fetch` поддерживаются.

```ts
const api = useApi()
const toast = useToast()

async function checkConnection() {
  try {
    const user = await api<{ id: string, email: string }>('/users/me')
    console.log(user)
  } catch (error) {
    if (error instanceof ApiError) {
      toast.add({ title: error.code, description: error.message, color: 'error' })
      console.log(error.toJSON()) // { detail, code }; status доступен отдельно
    }
  }
}
```

Без токена `/users/me` возвращает `401`; клиент пробует восстановить сессию через Nitro.
При отсутствии refresh-cookie ошибка остаётся `401` с `code: 'unauthorized'`.
Access-токен читается при каждом запросе из `useState<string | null>('auth:access-token')`;
он хранится в состоянии Nuxt, изолированном между SSR-запросами, без localStorage.
После входа `useSession()` заполняет это состояние. Refresh-токен сюда класть нельзя.

`ApiError` сохраняет backend `{detail, code}` и HTTP-статус. Для FastAPI `422` массив
`detail` с `loc`, `msg`, `type` сохраняется для привязки ошибок к полям, добавляется
`code: 'validation_error'`. Ошибка сети получает `network_error`, нестандартный HTTP-ответ —
`http_error`. Общие автоматические повторы отключены; при 401 разрешён один refresh
и один повтор исходного запроса. Таймаут по умолчанию — 15 секунд
(для долгих AI-запросов передайте свой `timeout`).

### Авторизация (T-10)

- `/signup` отправляет `username`, `email`, `password`, затем выполняет вход и открывает
  `/account`. `/login` открывает исходный защищённый маршрут из безопасного `redirect`.
  Валидация повторяет backend: username 3–50 символов `[A-Za-z0-9_.-]`, пароль минимум
  8 символов и максимум 72 UTF-8 байта. Ошибки backend показываются в форме.
- `useSession()` вызывает `/api/session/login|register|refresh|logout`. Nitro обращается
  к gateway и возвращает браузеру только access-токен. Cookie `ai_sana_refresh` имеет
  `HttpOnly`, `SameSite=Lax`, `Path=/`, срок 7 дней и `Secure` в production (нужен HTTPS).
  Если срок refresh изменится на backend, синхронизируйте срок cookie в Nitro.
- Cookie передаётся при SSR; новая cookie после refresh возвращается в ответе страницы.
  Пароли и refresh-токены не сохраняются в localStorage и не выводятся в консоль.
  Session-роуты требуют `X-Requested-With: AI-Sana` и отклоняют cross-site запросы.
- `useApi()` при 401 обновляет токен и повторяет запрос ровно один раз. Одновременные
  запросы используют один refresh в рамках приложения/SSR-запроса. Ошибки входа
  `/auth/*` не запускают refresh; login/register вызывайте через `useSession()`.
- Для приватных страниц добавляйте `definePageMeta({ middleware: 'auth' })` и запрещайте
  кеширование/пререндер, как для `/account` в `nuxt.config.ts`. Middleware проверяет
  `/users/me`, при отсутствии сессии направляет на `/login`, при сбое сервиса отдаёт 503.
- Выход удаляет cookie и состояние frontend. Backend пока не имеет endpoint отзыва
  токенов: ранее выданные JWT действуют до истечения своего срока.
- Ролей business/student в текущем API нет; выбор роли и OAuth в интерфейсе не предлагаются.

#### Проверка авторизации

Запустите backend через `start.bat` и frontend через `pnpm dev`, зарегистрируйтесь,
обновите `/account`, выйдите и снова откройте `/account`: должен произойти переход на вход.
Для frontend на `127.0.0.1:3000` добавьте этот origin в `BACKEND_CORS_ORIGINS` gateway.

`pnpm test:auth` проверяет реальные Nitro/gateway, cookie, SSR, ошибки, выход и повторы
в composables. Запускайте с **отдельной тестовой БД**: тест создаёт пользователей.
Задайте `AUTH_TEST_JWT_SECRET` равным тестовому `JWT_SECRET_KEY` backend — он нужен
для выпуска заведомо истёкшего access-токена. Не используйте production-ключ.
Адреса можно переопределить через `AUTH_TEST_FRONTEND` (по умолчанию `http://127.0.0.1:3000`)
и `AUTH_TEST_GATEWAY` (`http://127.0.0.1:8000/api/v1`).

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
