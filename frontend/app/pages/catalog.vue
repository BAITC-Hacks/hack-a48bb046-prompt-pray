<script setup lang="ts">
import type { ApiError } from '~/types/api'
import type { CatalogPage } from '~/types/catalog'

useSeoMeta({ title: 'Каталог бизнес-задач — AI Sana' })
const api = useApi()
const page = ref(1)
const limit = 12
const { data: result, error, status, refresh } = await useAsyncData(
  'business-task-catalog',
  () => api.request<CatalogPage>('/catalog', { query: { limit, offset: (page.value - 1) * limit } }),
  { watch: [page] }
)
const pending = computed(() => status.value === 'pending')
const errorMessage = computed(() => (error.value as unknown as ApiError | null)?.detail || 'Не удалось загрузить задачи. Попробуйте ещё раз.')
</script>

<template>
  <UContainer class="space-y-8 py-12">
    <UPageHeader
      title="Найдите задачу для своей команды"
      description="Реальные потребности бизнеса, с которых начинается ваш следующий проект."
    >
      <template #headline>
        <span class="text-sm font-medium text-primary">Каталог бизнес-задач</span>
      </template>
      <template #links>
        <UButton
          to="/tasks/new"
          label="Создать задачу"
          icon="i-lucide-plus"
          size="lg"
        />
      </template>
    </UPageHeader>

    <div class="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-default bg-muted/40 p-4">
      <div class="flex items-center gap-2 text-sm font-medium">
        <UIcon
          name="i-lucide-arrow-down-wide-narrow"
          class="size-5 text-primary"
          aria-hidden="true"
        />
        Сначала самые подготовленные
      </div>
      <span
        v-if="result && !pending && !error"
        class="text-sm text-muted"
        role="status"
      >Всего задач: {{ result.total }}</span>
    </div>
    <p class="text-sm text-muted">
      Рейтинг отражает полноту описания. Вы можете откликнуться на любую задачу — команду выбирает бизнес.
    </p>

    <div
      v-if="pending"
      role="status"
      aria-label="Загрузка задач"
      class="space-y-4"
    >
      <span class="sr-only">Загрузка задач…</span>
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
      title="Каталог временно недоступен"
      :description="errorMessage"
      icon="i-lucide-cloud-off"
    >
      <UButton
        label="Повторить загрузку"
        icon="i-lucide-refresh-cw"
        @click="refresh()"
      />
    </AppEmptyState>
    <AppEmptyState
      v-else-if="!result?.total"
      title="Первая задача может быть вашей"
      description="Опишите потребность бизнеса. Мы поможем уточнить детали и подготовить карточку для команд."
    >
      <UButton
        to="/tasks/new"
        label="Создать задачу"
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
