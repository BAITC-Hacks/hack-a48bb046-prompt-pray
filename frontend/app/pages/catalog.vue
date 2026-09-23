<script setup lang="ts">
import type { CatalogPage } from '~/types/catalog'

const { t, n } = useAppI18n()

useSeoMeta({ title: () => t('catalog.meta'), description: () => t('catalog.description') })
const api = useApi()
const { errorMessage } = useApiMessages()
const page = ref(1)
const limit = 12
const { data: result, error, status, refresh } = await useAsyncData(
  'business-task-catalog',
  () => api.request<CatalogPage>('/catalog', { query: { limit, offset: (page.value - 1) * limit } }),
  { watch: [page] }
)
const pending = computed(() => status.value === 'pending')
</script>

<template>
  <UContainer class="space-y-8 py-12 sm:py-16">
    <UPageHeader
      :title="t('catalog.title')"
      :description="t('catalog.description')"
    >
      <template #headline>
        <span class="text-sm font-medium text-primary">{{ t('catalog.headline') }}</span>
      </template>
      <template #links>
        <UButton
          to="/tasks/new"
          :label="t('navigation.createTask')"
          icon="i-lucide-plus"
          size="lg"
        />
      </template>
    </UPageHeader>

    <div class="flex flex-wrap items-center justify-between gap-4 border-b border-default pb-4">
      <div class="flex items-center gap-2 text-sm font-medium">
        <UIcon
          name="i-lucide-arrow-down-wide-narrow"
          class="size-4 text-muted"
          aria-hidden="true"
        />
        {{ t('catalog.sort') }}
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
    <UPageGrid v-else>
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
