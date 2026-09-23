<script setup lang="ts">
import type { ApiError } from '~/types/api'

interface Reward {
  id: string
  task_id: string
  title: string
  kind: string
  detail: string
  coins: number
  reputation: number
}
interface Day { date: string, visited: boolean, active: boolean, coins: number, reputation: number, events: Reward[] }
interface Progress { month: string, coins: number, reputation: number, active_days: number, current_streak: number, best_streak: number, action_current_streak: number, action_best_streak: number, days: Day[] }

const { t, locale } = useAppI18n()
const api = useApi()
const isBusiness = computed(() => api.user.value?.role === 'business')
const { errorMessage } = useApiMessages()
const month = ref(new Date().toISOString().slice(0, 7))
const selected = ref('')
const data = ref<Progress | null>(null)
const pending = ref(false)
const error = ref<ApiError | null>(null)
const monthDate = computed(() => new Date(`${month.value}-01T00:00:00Z`))
const monthLabel = computed(() => new Intl.DateTimeFormat(locale.value, { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(monthDate.value))
const offset = computed(() => (monthDate.value.getUTCDay() + 6) % 7)
const weekdays = computed(() => Array.from({ length: 7 }, (_, i) => new Intl.DateTimeFormat(locale.value, { weekday: 'short', timeZone: 'UTC' }).format(new Date(Date.UTC(2024, 0, i + 1)))))
const events = computed(() => data.value?.days.find(day => day.date === selected.value)?.events || [])
let requestId = 0
async function load() {
  const id = ++requestId
  pending.value = true
  error.value = null
  data.value = null
  try {
    // A failed visit ping must not hide the wallet and reward history.
    await api.request('/catalog/gamification/check-in', { method: 'POST' }).catch(() => undefined)
    const result = await api.request<Progress>('/catalog/gamification', { query: { month: month.value } })
    if (id !== requestId) return
    data.value = result
    selected.value = [...result.days].reverse().find(day => day.visited || day.events.length)?.date || `${month.value}-01`
  } catch (cause) {
    if (id === requestId) error.value = cause as ApiError
  } finally {
    if (id === requestId) pending.value = false
  }
}
function move(delta: number) {
  const date = new Date(monthDate.value)
  date.setUTCMonth(date.getUTCMonth() + delta)
  if (date.getUTCFullYear() < 1000 || date.getUTCFullYear() > 9999) return
  month.value = date.toISOString().slice(0, 7)
  void load()
}
onMounted(load)
</script>

<template>
  <section
    class="rounded-2xl border border-default bg-default p-6"
    :aria-label="t('rewards.title')"
    :aria-busy="pending"
  >
    <h2 class="text-xl font-semibold text-highlighted">
      {{ t('rewards.title') }}
    </h2>
    <p class="mt-2 text-sm text-muted">
      {{ t(isBusiness ? 'rewards.rules' : 'rewards.studentRules') }}
    </p>
    <p class="mt-2 text-sm font-medium text-primary">
      {{ t('rewards.separate') }}
    </p>
    <div
      class="mt-5 flex flex-wrap gap-6"
      aria-live="polite"
    >
      <p>
        <UIcon
          name="i-lucide-coins"
          class="mr-2 text-warning"
        />{{ t('rewards.coins') }}: <strong>{{ data?.coins ?? '—' }}</strong>
      </p>
      <p v-if="isBusiness">
        <UIcon
          name="i-lucide-medal"
          class="mr-2 text-primary"
        />{{ t('rewards.reputation') }}: <strong>{{ data?.reputation ?? '—' }}</strong>
      </p>
      <p>{{ t('rewards.days') }}: <strong>{{ data?.active_days ?? '—' }}</strong></p>
      <p>
        <UIcon
          name="i-lucide-flame"
          class="mr-2 text-warning"
        />{{ t('rewards.streak') }}: <strong>{{ data?.current_streak ?? '—' }}</strong>
      </p>
      <p>{{ t('rewards.best') }}: <strong>{{ data?.best_streak ?? '—' }}</strong></p>
    </div>
    <div class="mt-4 rounded-xl bg-primary/5 p-4 text-sm" aria-live="polite">
      <p class="font-semibold text-primary">
        <UIcon name="i-lucide-zap" class="mr-1" />
        {{ t('rewards.actionStreak') }}: {{ data?.action_current_streak ?? '—' }}
        · {{ t('rewards.best') }}: {{ data?.action_best_streak ?? '—' }}
      </p>
      <p class="mt-1 text-muted">{{ t('rewards.actionHint') }}</p>
    </div>
    <div class="mt-6 flex items-center justify-between gap-3">
      <UButton
        icon="i-lucide-chevron-left"
        color="neutral"
        variant="ghost"
        :aria-label="t('rewards.previous')"
        @click="move(-1)"
      />
      <h3 class="font-semibold capitalize">
        {{ monthLabel }}
      </h3>
      <UButton
        icon="i-lucide-chevron-right"
        color="neutral"
        variant="ghost"
        :aria-label="t('rewards.next')"
        @click="move(1)"
      />
    </div>
    <p class="mb-3 text-xs text-muted">
      {{ t('rewards.utc') }}
    </p>
    <p
      v-if="pending"
      role="status"
    >
      {{ t('rewards.loading') }}
    </p>
    <div
      v-else-if="error"
      role="alert"
    >
      <p>{{ errorMessage(error) }}</p>
      <UButton
        class="mt-2"
        :label="t('rewards.retry')"
        @click="load"
      />
    </div>
    <template v-else-if="data">
      <div class="grid grid-cols-7 gap-2">
        <span
          v-for="weekday in weekdays"
          :key="weekday"
          class="text-center text-xs text-muted"
        >{{ weekday }}</span>
        <span
          v-for="blank in offset"
          :key="`blank-${blank}`"
          aria-hidden="true"
        />
        <button
          v-for="day in data.days"
          :key="day.date"
          type="button"
          class="min-h-14 rounded-lg border p-2 text-center text-sm focus-visible:outline-2 focus-visible:outline-primary"
          :class="[day.visited ? 'bg-warning/10 text-warning' : 'bg-muted/30', selected === day.date ? 'border-primary' : 'border-transparent']"
          :aria-pressed="selected === day.date"
          :aria-label="`${day.date}: ${day.visited ? t('rewards.visited') : ''} ${t('rewards.coins')} ${day.coins}`"
          @click="selected = day.date"
        >
          {{ Number(day.date.slice(-2)) }}
          <UIcon
            v-if="day.visited"
            name="i-lucide-flame"
            class="ml-1"
          />
          <span
            v-if="day.coins"
            class="block text-xs font-semibold"
          >+{{ day.coins }}</span>
        </button>
      </div>
      <div
        class="mt-5 border-t border-default pt-4"
        aria-live="polite"
      >
        <p class="text-sm font-semibold">
          {{ selected }}
        </p>
        <p
          v-if="!events.length"
          class="mt-2 text-sm text-muted"
        >
          {{ t('rewards.empty') }}
        </p>
        <ul
          v-else
          class="mt-3 space-y-3"
        >
          <li
            v-for="event in events"
            :key="event.id"
            class="text-sm"
          >
            <NuxtLink
              :to="`/tasks/${event.task_id}`"
              class="font-medium text-primary underline"
            >{{ event.title }}</NuxtLink>
            <p>
              {{ t(`rewards.${event.kind}`) }}<template v-if="event.detail">
                : {{ t(`fields.${event.detail}`) }}
              </template>
              · +{{ event.coins }} {{ t('rewards.coins') }}
              <span v-if="event.reputation"> · +{{ event.reputation }} {{ t('rewards.reputation') }}</span>
            </p>
          </li>
        </ul>
      </div>
    </template>
  </section>
</template>
