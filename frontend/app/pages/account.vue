<script setup lang="ts">
import type { ApiError } from '~/types/api'
import type { Draft } from '~/types/catalog'

const { t } = useAppI18n()

definePageMeta({ middleware: 'auth' })
useSeoMeta({ title: () => t('account.title') })
const api = useApi()
const { errorMessage } = useApiMessages()
const isBusiness = computed(() => api.user.value?.role === 'business')
const initials = computed(() => (api.user.value?.username || 'U').slice(0, 2).toUpperCase())
const drafts = ref<Draft[]>([])
const error = ref<ApiError | null>(null)
const logoutError = ref<ApiError | null>(null)
const pending = ref(false)
const loaded = ref(false)
const loggingOut = ref(false)
const search = ref('')
const filter = ref('all')
const unfinished = computed(() => drafts.value.filter(draft => !draft.card_id))
const filters = computed(() => [
  { label: 'Все задачи', value: 'all', count: drafts.value.length, icon: 'i-lucide-layers' },
  { label: 'Черновики', value: 'drafts', count: unfinished.value.length, icon: 'i-lucide-file-pen-line' },
  { label: 'Карточки', value: 'cards', count: drafts.value.length - unfinished.value.length, icon: 'i-lucide-files' }
])
const filteredDrafts = computed(() => drafts.value.filter((draft) => {
  const matchesStatus = filter.value === 'all' || (filter.value === 'cards' ? !!draft.card_id : !draft.card_id)
  return matchesStatus && draft.description.toLocaleLowerCase().includes(search.value.trim().toLocaleLowerCase())
}))
const nextDraft = computed(() => unfinished.value[0])
function draftLink(draft: Draft) {
  return draft.card_id ? `/tasks/${draft.card_id}` : `/tasks/new?draft=${encodeURIComponent(draft.id)}`
}
function resetFilters() {
  search.value = ''
  filter.value = 'all'
}
async function loadDrafts() {
  if (pending.value) return
  pending.value = true
  error.value = null
  try {
    drafts.value = await api.request<Draft[]>('/catalog/drafts')
    loaded.value = true
  } catch (cause) {
    error.value = cause as ApiError
  } finally {
    pending.value = false
  }
}
onMounted(() => {
  if (isBusiness.value) void loadDrafts()
})
async function logout() {
  loggingOut.value = true
  logoutError.value = null
  try {
    await api.request('/auth/logout', { method: 'POST' })
    await navigateTo('/login')
  } catch (cause) {
    logoutError.value = cause as ApiError
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-muted/35">
    <UContainer class="py-8 lg:py-12">
      <div class="mb-8 flex flex-wrap items-end justify-between gap-5">
        <div>
          <p class="mb-2 text-xs font-semibold tracking-widest text-primary uppercase">
            Моё пространство
          </p>
          <h1 class="text-3xl font-semibold tracking-tight text-highlighted lg:text-4xl">
            {{ t('account.title') }}
          </h1>
          <p class="mt-3 text-muted">
            {{ isBusiness ? 'От идеи до команды — ваши задачи собраны здесь.' : 'Реальные задачи бизнеса. Возможности для вашей команды.' }}
          </p>
        </div>
        <UButton
          :to="isBusiness ? '/tasks/new' : '/catalog'"
          :icon="isBusiness ? 'i-lucide-plus' : 'i-lucide-search'"
          :label="isBusiness ? t('navigation.createTask') : 'Найти задачу'"
          size="lg"
          class="rounded-xl"
        />
      </div>
      <div class="grid items-start gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside
          class="space-y-4 lg:sticky lg:top-24"
          aria-label="Профиль и навигация"
        >
          <div class="overflow-hidden rounded-2xl border border-default bg-default">
            <div class="h-16 bg-gradient-to-br from-primary/25 via-primary/10 to-default" />
            <div class="px-5 pb-5">
              <div class="-mt-7 mb-4 flex size-14 items-center justify-center rounded-2xl border-4 border-default bg-primary text-lg font-bold text-inverted">
                {{ initials }}
              </div>
              <p class="font-semibold break-words text-highlighted">
                {{ api.user.value?.username }}
              </p>
              <p class="mt-1 text-xs break-all text-muted">
                {{ api.user.value?.email }}
              </p>
              <UBadge
                :icon="isBusiness ? 'i-lucide-building-2' : 'i-lucide-graduation-cap'"
                color="neutral"
                variant="soft"
                class="mt-4"
              >
                {{ isBusiness ? t('auth.business') : t('auth.student') }}
              </UBadge>
            </div>
            <nav
              class="space-y-1 border-t border-default p-3"
              aria-:label="t('account.title')"
            >
              <NuxtLink
                to="/account"
                aria-current="page"
                class="flex items-center gap-3 rounded-xl bg-primary/10 px-3 py-3 text-sm font-medium text-primary focus-visible:outline-2 focus-visible:outline-primary"
              >
                <UIcon
                  name="i-lucide-layout-dashboard"
                  class="size-4"
                />Обзор<UIcon
                  name="i-lucide-chevron-right"
                  class="ml-auto size-4"
                />
              </NuxtLink>
              <NuxtLink
                to="/catalog"
                class="flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-muted transition-colors hover:bg-muted hover:text-highlighted focus-visible:outline-2 focus-visible:outline-primary"
              >
                <UIcon
                  name="i-lucide-compass"
                  class="size-4"
                />{{ t('navigation.catalog') }}<UIcon
                  name="i-lucide-arrow-up-right"
                  class="ml-auto size-4"
                />
              </NuxtLink>
            </nav>
          </div>
          <UButton
            label="Выйти из аккаунта"
            icon="i-lucide-log-out"
            color="neutral"
            variant="ghost"
            :loading="loggingOut"
            class="w-full justify-start rounded-xl px-4"
            @click="logout"
          />
          <UAlert
            v-if="logoutError"
            color="error"
            :title="errorMessage(logoutError)"
          />
        </aside>
        <div class="min-w-0 space-y-6">
          <section
            class="relative overflow-hidden rounded-2xl border border-primary/20 bg-primary/5 p-6 sm:p-8"
            aria-labelledby="next-step-title"
          >
            <div
              class="pointer-events-none absolute -top-16 -right-12 size-56 rounded-full border-[32px] border-primary/5"
              aria-hidden="true"
            />
            <div class="relative max-w-xl">
              <p class="mb-3 flex items-center gap-2 text-xs font-semibold tracking-wide text-primary uppercase">
                <UIcon
                  name="i-lucide-sparkles"
                  class="size-4"
                />{{ isBusiness ? 'Следующий шаг' : 'Начните с интересной задачи' }}
              </p>
              <h2
                id="next-step-title"
                class="text-2xl font-semibold tracking-tight text-highlighted"
              >
                {{ isBusiness ? (nextDraft ? 'Хорошей идее нужны детали' : 'Ваша задача. Свежий взгляд команды.') : 'Превратите знания в реальный опыт' }}
              </h2>
              <p class="mt-3 text-sm leading-6 text-muted">
                {{ isBusiness ? (nextDraft ? 'У вас есть незавершённый черновик. Ответьте на вопросы AI и подготовьте понятную карточку для команд.' : 'Опишите потребность своими словами. AI поможет уточнить детали, а вы проверите карточку перед публикацией.') : 'Выберите задачу в каталоге, обсудите её с командой и предложите бизнесу свою идею и план решения.' }}
              </p>
              <UButton
                :to="isBusiness ? (nextDraft ? draftLink(nextDraft) : '/tasks/new') : '/catalog'"
                :label="isBusiness ? (nextDraft ? 'Продолжить черновик' : 'Описать идею') : 'Перейти в каталог'"
                trailing-icon="i-lucide-arrow-right"
                color="neutral"
                variant="outline"
                class="mt-5 rounded-lg bg-default"
              />
            </div>
          </section>
          <template v-if="isBusiness">
            <div
              class="grid grid-cols-3 gap-3 sm:gap-4"
              aria-label="Обзор задач"
            >
              <button
                v-for="item in filters"
                :key="item.value"
                type="button"
                :aria-pressed="filter === item.value"
                class="rounded-2xl border bg-default p-4 text-left transition-colors hover:border-primary/50 focus-visible:outline-2 focus-visible:outline-primary sm:p-5"
                :class="filter === item.value ? 'border-primary/50' : 'border-default'"
                @click="filter = item.value"
              >
                <div class="mb-4 flex items-center justify-between gap-2">
                  <UIcon
                    :name="item.icon"
                    class="size-5 text-primary"
                  /><UIcon
                    name="i-lucide-arrow-up-right"
                    class="size-4 text-dimmed"
                  />
                </div>
                <span class="block text-3xl font-semibold tracking-tight text-highlighted">{{ loaded ? item.count : '—' }}</span>
                <span class="mt-1 block text-xs text-muted sm:text-sm">{{ item.label }}</span>
              </button>
            </div>
            <section
              class="overflow-hidden rounded-2xl border border-default bg-default"
              aria-labelledby="tasks-title"
              :aria-busy="pending"
            >
              <div class="flex items-center justify-between gap-4 px-5 pt-6 sm:px-6">
                <div>
                  <h2
                    id="tasks-title"
                    class="text-lg font-semibold text-highlighted"
                  >
                    {{ t('account.tasks') }}
                  </h2><p class="mt-1 text-sm text-muted">
                    Продолжайте работу и просматривайте отклики.
                  </p>
                </div>
                <UButton
                  icon="i-lucide-refresh-cw"
                  aria-label="Обновить список задач"
                  title="Обновить список"
                  color="neutral"
                  variant="ghost"
                  :loading="pending"
                  @click="loadDrafts"
                />
              </div>
              <div class="flex flex-wrap items-center justify-between gap-4 border-b border-default p-5 sm:px-6">
                <div
                  class="flex flex-wrap gap-1"
                  role="group"
                  aria-label="Фильтр задач"
                >
                  <UButton
                    v-for="item in filters"
                    :key="item.value"
                    :label="item.label"
                    :color="filter === item.value ? 'primary' : 'neutral'"
                    :variant="filter === item.value ? 'soft' : 'ghost'"
                    :aria-pressed="filter === item.value"
                    class="rounded-lg"
                    @click="filter = item.value"
                  />
                </div>
                <UInput
                  v-model="search"
                  icon="i-lucide-search"
                  placeholder="Найти задачу…"
                  aria-label="Поиск по описанию задачи"
                  class="w-full sm:w-56"
                />
              </div>
              <div
                v-if="error"
                class="p-5"
              >
                <UAlert
                  color="error"
                  title="Не удалось обновить задачи"
                  :description="error.detail"
                  icon="i-lucide-circle-alert"
                />
                <UButton
                  label="Попробовать снова"
                  color="neutral"
                  variant="outline"
                  class="mt-3"
                  :loading="pending"
                  @click="loadDrafts"
                />
              </div>
              <div
                v-if="!loaded && (pending || !error)"
                class="space-y-5 p-6"
                role="status"
              >
                <span class="sr-only">Загрузка задач…</span>
                <div
                  v-for="item in 3"
                  :key="item"
                  class="space-y-3"
                  aria-hidden="true"
                >
                  <USkeleton class="h-5 w-24" /><USkeleton class="h-5 w-3/4" /><USkeleton class="h-4 w-1/2" />
                </div>
              </div>
              <div
                v-else-if="loaded && !drafts.length"
                class="px-6 py-12 text-center"
              >
                <div class="mx-auto mb-5 flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <UIcon
                    name="i-lucide-file-plus-2"
                    class="size-7"
                  />
                </div>
                <h3 class="text-lg font-semibold text-highlighted">
                  Здесь начнётся ваша первая задача
                </h3>
                <p class="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted">
                  Идеальное описание не нужно. Начните с того, что хотите улучшить в своём бизнесе.
                </p>
                <UButton
                  to="/tasks/new"
                  label="Создать первую задачу"
                  icon="i-lucide-plus"
                  class="mt-5 rounded-lg"
                />
              </div>
              <div
                v-else-if="loaded && !filteredDrafts.length"
                class="px-6 py-12 text-center"
              >
                <UIcon
                  name="i-lucide-search-x"
                  class="mb-3 size-8 text-dimmed"
                />
                <h3 class="font-semibold text-highlighted">
                  Задачи не найдены
                </h3>
                <p class="mt-2 text-sm text-muted">
                  Измените запрос или выберите другой статус.
                </p>
                <UButton
                  label="Сбросить фильтры"
                  variant="soft"
                  class="mt-4"
                  @click="resetFilters"
                />
              </div>
              <ul
                v-else-if="loaded"
                class="divide-y divide-default"
              >
                <li
                  v-for="draft in filteredDrafts"
                  :key="draft.id"
                >
                  <NuxtLink
                    :to="draftLink(draft)"
                    class="group flex items-center gap-4 p-5 transition-colors hover:bg-muted/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary sm:px-6"
                  >
                    <div class="hidden size-11 shrink-0 items-center justify-center rounded-xl bg-muted text-muted sm:flex"><UIcon
                      :name="draft.card_id ? 'i-lucide-file-check-2' : 'i-lucide-file-pen-line'"
                      class="size-5"
                    /></div>
                    <div class="min-w-0 flex-1">
                      <UBadge
                        :color="draft.card_id ? 'primary' : 'neutral'"
                        variant="soft"
                        size="sm"
                      >{{ draft.card_id ? 'Карточка создана' : 'Черновик' }}</UBadge>
                      <h3 class="mt-2 line-clamp-2 text-sm leading-6 font-medium break-words text-highlighted">{{ draft.description || 'Задача без описания' }}</h3>
                      <p class="mt-2 text-xs text-muted">{{ draft.card_id ? t('account.openCard') : t('account.continue') }}</p>
                    </div>
                    <UIcon
                      name="i-lucide-arrow-right"
                      class="size-5 shrink-0 text-dimmed transition-colors group-hover:text-primary"
                    />
                  </NuxtLink>
                </li>
              </ul>
              <p
                v-if="loaded && drafts.length"
                class="border-t border-default px-6 py-3 text-xs text-muted"
                role="status"
              >
                Показано {{ filteredDrafts.length }} из {{ drafts.length }}
              </p>
            </section>
          </template>
          <section
            class="rounded-2xl border border-default bg-default p-6"
            :aria-label="isBusiness ? 'Как улучшить задачу' : 'Как начать работу'"
          >
            <h2 class="flex items-center gap-2 font-semibold text-highlighted">
              <UIcon
                :name="isBusiness ? 'i-lucide-chart-no-axes-combined' : 'i-lucide-route'"
                class="size-5 text-primary"
              />{{ isBusiness ? 'Больше ясности — выше рейтинг' : 'От задачи до сотрудничества' }}
            </h2>
            <p class="mt-2 text-sm leading-6 text-muted">
              {{ isBusiness ? 'Добавьте контекст, материалы и критерии успеха. Полнота описания повышает рейтинг и позицию в каталоге.' : 'Откликнуться можно на любую задачу, независимо от её рейтинга.' }}
            </p>
            <ol class="mt-6 grid gap-5 sm:grid-cols-3">
              <li
                v-for="(step, index) in (isBusiness ? ['Опишите потребность', 'Уточните детали с AI', 'Проверьте и опубликуйте'] : ['Выберите задачу', 'Предложите идею и план', 'Дождитесь решения бизнеса'])"
                :key="step"
                class="flex items-center gap-3 text-sm text-highlighted"
              >
                <span class="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted">{{ index + 1 }}</span>{{ step }}
              </li>
            </ol>
            <p class="mt-6 border-t border-default pt-4 text-xs leading-5 text-muted">
              {{ isBusiness ? 'Даже задача с низким рейтингом доступна командам. Вы сами решаете, с кем работать.' : 'Бизнес сравнивает предложения и выбирает команду вручную. Автоматического назначения нет.' }}
            </p>
          </section>
        </div>
      </div>
    </UContainer>
  </div>
</template>
