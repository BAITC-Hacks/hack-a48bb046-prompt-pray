<script setup lang="ts">
import type { ApiError } from '~/types/api'
import type { CatalogPage } from '~/types/catalog'

const api = useApi()
const page = ref(1)
const limit = 12
const result = ref<CatalogPage | null>(null)
const error = ref<ApiError | null>(null)
const pending = ref(false)
async function load() {
  pending.value = true
  error.value = null
  try {
    result.value = await api.request<CatalogPage>('/catalog', { query: { limit, offset: (page.value - 1) * limit } })
  } catch (cause) {
    error.value = cause as ApiError
  } finally {
    pending.value = false
  }
}
await load()
watch(page, load)
</script>

<template>
  <UContainer class="py-12 space-y-6">
    <UPageHeader
      title="Каталог бизнес-задач"
      description="Задачи отсортированы по рейтингу готовности: от высокого к низкому. Откликнуться можно и на задачи с низким рейтингом."
    />
    <UButton
      to="/tasks/new"
      label="Создать задачу"
    />
    <UAlert
      v-if="error"
      color="error"
      :title="error.detail"
      :description="error.code"
    />
    <UButton
      v-if="error"
      label="Повторить"
      @click="load"
    />
    <p
      v-if="pending"
      role="status"
    >
      Загрузка…
    </p>
    <p v-else-if="!result?.total && !error">
      Опубликованных задач пока нет.
    </p>
    <UPageGrid v-if="result">
      <UPageCard
        v-for="entry in result.items"
        :key="entry.task_id"
        :title="entry.task.title"
        :description="entry.task.context || 'Контекст ещё не заполнен'"
        :to="`/tasks/${entry.task_id}`"
      >
        <UBadge
          :label="`${entry.task.rating?.total ?? 0} / 100 · ${entry.task.rating?.readiness || 'черновик'}`"
          variant="subtle"
        />
      </UPageCard>
    </UPageGrid>
    <UPagination
      v-if="result && result.total > limit"
      v-model:page="page"
      :total="result.total"
      :items-per-page="limit"
      :disabled="pending"
    />
  </UContainer>
</template>
