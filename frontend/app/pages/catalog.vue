<script setup lang="ts">
import { taskRating, readiness } from '~/utils/task-rating'

useSeoMeta({ title: 'Каталог задач', description: 'Проекты для студенческих команд' })
const workspace = useTasks()
const search = ref('')
const sort = ref<'rating' | 'newest'>('rating')
const page = ref(1)
const pageSize = 6
const matching = computed(() => {
  const query = search.value.trim().toLocaleLowerCase('ru')
  return workspace.tasks.value
    .filter(task => task.status === 'published')
    .filter(task => !query || `${task.title} ${task.brief} ${task.business}`.toLocaleLowerCase('ru').includes(query))
    .sort((left, right) => sort.value === 'rating'
      ? taskRating(right) - taskRating(left) || right.createdAt.localeCompare(left.createdAt)
      : right.createdAt.localeCompare(left.createdAt))
})
const count = computed(() => matching.value.length)
const visible = computed(() => matching.value.slice((page.value - 1) * pageSize, page.value * pageSize))
watch([search, sort], () => page.value = 1)
watch(count, (value) => {
  page.value = Math.min(page.value, Math.max(1, Math.ceil(value / pageSize)))
})
</script>

<template>
  <UContainer class="py-12 sm:py-16">
    <header class="flex flex-col sm:flex-row sm:items-end justify-between gap-6 mb-8">
      <div>
        <UBadge
          label="Открытый каталог"
          color="primary"
          variant="subtle"
          class="mb-4"
        />
        <h1 class="text-4xl sm:text-5xl font-bold tracking-tight">
          Задачи для проектов
        </h1>
        <p class="text-muted text-lg mt-3 max-w-2xl">
          Ищите задачу, предлагайте свой план и договоритесь с бизнесом о следующем шаге.
        </p>
      </div>
      <UButton
        label="Предложить свою задачу"
        icon="i-lucide-plus"
        to="/tasks/new"
        size="lg"
      />
    </header>
    <UAlert
      color="warning"
      variant="subtle"
      icon="i-lucide-flask-conical"
      title="Демонстрационный каталог"
      description="Пока виден только в вашем браузере. Примеры и изменения не опубликованы в общем каталоге."
      class="mb-7"
    />
    <div class="grid sm:grid-cols-[1fr_15rem] gap-3 mb-6">
      <UInput
        v-model="search"
        icon="i-lucide-search"
        placeholder="Поиск по названию и описанию"
        aria-label="Поиск задач"
      />
      <USelect
        v-model="sort"
        :items="[{ label: 'Сначала высокий рейтинг', value: 'rating' }, { label: 'Сначала новые', value: 'newest' }]"
        aria-label="Сортировка каталога"
      />
    </div>
    <p
      class="text-sm text-muted mb-4"
      aria-live="polite"
    >
      {{ count }} {{ count === 1 ? 'задача' : 'задач' }}
    </p>
    <div
      v-if="visible.length"
      class="grid md:grid-cols-2 xl:grid-cols-3 gap-5"
    >
      <UCard
        v-for="task in visible"
        :key="task.id"
        class="flex flex-col h-full"
      >
        <div class="flex justify-between items-center gap-3 mb-4">
          <UBadge
            :label="readiness(taskRating(task)).label"
            :color="readiness(taskRating(task)).color"
            variant="subtle"
          />
          <span class="text-sm font-semibold tabular-nums">{{ taskRating(task) }}<span class="text-muted font-normal">/100</span></span>
        </div>
        <h2 class="text-lg font-semibold leading-snug">
          {{ task.title }}
        </h2>
        <p class="text-sm text-muted mt-3 line-clamp-3">
          {{ task.brief }}
        </p>
        <p
          v-if="task.business"
          class="mt-4 text-sm"
        >
          <span class="font-medium">Цель:</span> <span class="text-muted">{{ task.business }}</span>
        </p>
        <div class="mt-auto pt-5 flex items-center justify-between gap-3">
          <span class="text-xs text-muted">{{ task.proposals.length }} {{ task.proposals.length === 1 ? 'отклик' : 'откликов' }}</span>
          <UButton
            label="Подробнее"
            trailing-icon="i-lucide-arrow-right"
            color="neutral"
            variant="outline"
            :to="`/tasks/${task.id}`"
          />
        </div>
      </UCard>
    </div>
    <UEmpty
      v-else
      icon="i-lucide-search-x"
      title="Ничего не найдено"
      description="Попробуйте другой запрос или создайте новую задачу."
    >
      <template #actions>
        <UButton
          label="Создать задачу"
          to="/tasks/new"
        />
      </template>
    </UEmpty>
    <div
      v-if="count > pageSize"
      class="mt-8 flex justify-center"
    >
      <UPagination
        v-model:page="page"
        :total="count"
        :items-per-page="pageSize"
        aria-label="Страницы каталога"
      />
    </div>
  </UContainer>
</template>
