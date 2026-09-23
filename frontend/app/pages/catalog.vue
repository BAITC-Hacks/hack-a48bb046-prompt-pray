<script setup lang="ts">
import type { CatalogPage } from '~/types/catalog'

const { t, n } = useAppI18n()

useSeoMeta({ title: () => t('catalog.meta'), description: () => t('catalog.description') })
const api = useApi()
const { errorMessage } = useApiMessages()
const page = ref(1)
const profile = useState('catalog-team-profile', () => ({ skills: '', interests: '' }))
const personalized = ref(false)
const applied = ref({ skills: '', interests: '' })
function applyProfile() {
  personalized.value = true
  applied.value = { ...profile.value }
  page.value = 1
}
function resetSort() {
  personalized.value = false
  applied.value = { skills: '', interests: '' }
  page.value = 1
}
const limit = 12
const { data: result, error, status, refresh } = useLazyAsyncData(
  'business-task-catalog',
  () => api.request<CatalogPage>('/catalog', { query: { limit, offset: (page.value - 1) * limit, ...applied.value } }),
  { watch: [page, applied], server: false }
)
const pending = computed(() => status.value === 'pending')
</script>

<template>
  <UContainer
    data-app-page
    class="space-y-8"
  >
    <AppPageHeading
      :title="t('catalog.title')"
      :description="t('catalog.description')"
      :eyebrow="t('catalog.headline')"
      icon="i-lucide-layout-grid"
    >
      <UButton
        to="/tasks/new"
        :label="t('navigation.createTask')"
        icon="i-lucide-plus"
        size="lg"
      />
    </AppPageHeading>

    <form
      class="space-y-4 rounded-xl border border-default p-5"
      @submit.prevent="applyProfile"
    >
      <p class="font-medium">
        {{ t('ai.forYou') }}
      </p>
      <div class="grid gap-4 sm:grid-cols-2">
        <UFormField :label="t('ai.skills')">
          <UInput
            v-model="profile.skills"
            :maxlength="500"
            class="w-full"
          />
        </UFormField>
        <UFormField :label="t('ai.interests')">
          <UInput
            v-model="profile.interests"
            :maxlength="500"
            class="w-full"
          />
        </UFormField>
      </div>
      <p class="text-xs text-muted">
        {{ t('ai.matchHint') }}
      </p>
      <div class="flex gap-3">
        <UButton
          type="submit"
          :label="t('ai.forYou')"
          :disabled="pending || !(profile.skills.trim() || profile.interests.trim())"
        />
        <UButton
          :label="t('catalog.sort')"
          variant="outline"
          @click="resetSort"
        />
      </div>
    </form>

    <div class="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-default bg-muted/40 px-5 py-4">
      <div class="flex items-center gap-2 text-sm font-medium">
        <UIcon
          name="i-lucide-arrow-down-wide-narrow"
          class="size-4 text-muted"
          aria-hidden="true"
        />
        {{ personalized ? t('ai.forYou') : t('catalog.sort') }}
      </div>
      <span
        v-if="result && !pending && !error"
        class="text-sm text-muted"
        role="status"
      >{{ t('catalog.count', { count: n(result.total) }, result.total) }}</span>
    </div>

    <div
      v-if="pending"
      role="status"
      :aria-label="t('catalog.loading')"
      class="space-y-4"
    >
      <span class="sr-only">{{ t('catalog.loading') }}</span>
      <UPageGrid aria-hidden="true">
        <UCard
          v-for="item in 6"
          :key="item"
        >
          <div class="space-y-4">
            <USkeleton class="h-5 w-32" />
            <USkeleton class="h-7 w-3/4" />
            <USkeleton class="h-16 w-full" />
            <USkeleton class="h-5 w-40" />
          </div>
        </UCard>
      </UPageGrid>
    </div>
    <AppEmptyState
      v-else-if="error"
      :title="t('catalog.unavailable')"
      :description="errorMessage(error)"
      icon="i-lucide-cloud-off"
    >
      <UButton
        :label="t('catalog.retry')"
        icon="i-lucide-refresh-cw"
        @click="refresh()"
      />
    </AppEmptyState>
    <AppEmptyState
      v-else-if="!result?.total"
      :title="t('catalog.emptyTitle')"
      :description="t('catalog.emptyDescription')"
    >
      <UButton
        to="/tasks/new"
        :label="t('navigation.createTask')"
        icon="i-lucide-plus"
      />
    </AppEmptyState>
    <UPageGrid
      v-else
      data-app-reveal
    >
      <CatalogTaskCard
        v-for="entry in result.items"
        :key="entry.task_id"
        :entry="entry"
      />
    </UPageGrid>
    <p class="text-xs leading-6 text-muted">
      {{ t('catalog.ratingHint') }}
    </p>
    <div
      v-if="result && result.total > limit"
      class="flex justify-center border-t border-default pt-6"
    >
      <UPagination
        v-model:page="page"
        :total="result.total"
        :items-per-page="limit"
        :disabled="pending"
      />
    </div>
  </UContainer>
</template>
