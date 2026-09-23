<script setup lang="ts">
import type { ApiError } from '~/types/api'

interface Leaderboard {
  businesses: { id: string, coins: number, reputation: number, is_you: boolean }[]
  teams: { id: string, proposals: number, selected_tasks: number }[]
}
const { t } = useAppI18n()
const api = useApi()
const { errorMessage } = useApiMessages()
const data = ref<Leaderboard | null>(null)
const error = ref<ApiError | null>(null)
const pending = ref(false)
async function load() {
  pending.value = true
  error.value = null
  try {
    data.value = await api.request<Leaderboard>('/catalog/gamification/leaderboard')
  } catch (cause) {
    error.value = cause as ApiError
  } finally {
    pending.value = false
  }
}
onMounted(load)
</script>

<template>
  <section
    class="rounded-2xl border border-default bg-default p-6"
    :aria-busy="pending"
  >
    <h2 class="text-xl font-semibold text-highlighted">
      {{ t('rewards.leaderboard') }}
    </h2>
    <p class="mt-2 text-sm text-muted">
      {{ t('rewards.scope') }}
    </p>
    <p
      v-if="pending"
      class="mt-4"
      role="status"
    >
      {{ t('rewards.loading') }}
    </p>
    <div
      v-else-if="error"
      class="mt-4"
      role="alert"
    >
      <p>{{ errorMessage(error) }}</p>
      <UButton
        :label="t('rewards.retry')"
        @click="load"
      />
    </div>
    <div
      v-else-if="data"
      class="mt-5 grid gap-6 xl:grid-cols-2"
    >
      <div>
        <h3 class="font-semibold">
          {{ t('rewards.businesses') }}
        </h3>
        <p class="mt-1 text-xs text-muted">
          {{ t('rewards.businessMetric') }}
        </p>
        <p
          v-if="!data.businesses.length"
          class="mt-3 text-sm text-muted"
        >
          {{ t('rewards.noParticipants') }}
        </p>
        <ol
          v-else
          class="mt-3 space-y-3"
        >
          <li
            v-for="(entry, index) in data.businesses"
            :key="entry.id"
            class="rounded-lg bg-muted/30 p-3 text-sm"
          >
            <p>{{ index + 1 }}. {{ t('rewards.business') }} #{{ entry.id.slice(0, 8) }} <strong v-if="entry.is_you">({{ t('rewards.you') }})</strong></p>
            <p>{{ t('rewards.reputation') }}: {{ entry.reputation }} · {{ t('rewards.coins') }}: {{ entry.coins }}</p>
          </li>
        </ol>
      </div>
      <div>
        <h3 class="font-semibold">
          {{ t('rewards.teams') }}
        </h3>
        <p class="mt-1 text-xs text-muted">
          {{ t('rewards.teamMetric') }}
        </p>
        <p
          v-if="!data.teams.length"
          class="mt-3 text-sm text-muted"
        >
          {{ t('rewards.noParticipants') }}
        </p>
        <ol
          v-else
          class="mt-3 space-y-3"
        >
          <li
            v-for="(entry, index) in data.teams"
            :key="entry.id"
            class="rounded-lg bg-muted/30 p-3 text-sm"
          >
            <p>{{ index + 1 }}. {{ t('rewards.team') }} #{{ entry.id.slice(0, 8) }}</p>
            <p>{{ t('rewards.selectedTasks') }}: {{ entry.selected_tasks }} · {{ t('rewards.proposals') }}: {{ entry.proposals }}</p>
          </li>
        </ol>
      </div>
    </div>
  </section>
</template>
