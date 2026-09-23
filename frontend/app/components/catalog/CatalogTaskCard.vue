<script setup lang="ts">
import type { CatalogEntry } from '~/types/catalog'

defineProps<{ entry: CatalogEntry }>()
</script>

<template>
  <UPageCard
    :title="entry.task.title"
    :to="`/tasks/${entry.task_id}`"
    class="h-full transition-shadow hover:shadow-md"
    :ui="{ title: 'line-clamp-2', description: 'line-clamp-3' }"
    :description="entry.task.context || 'Контекст ещё не заполнен. Детали можно обсудить с бизнесом.'"
  >
    <template #leading>
      <TasksTaskRating
        :rating="entry.task.rating"
        compact
      />
    </template>
    <template #footer>
      <span class="inline-flex items-center gap-2 text-sm font-medium text-primary">
        Подробнее о задаче <UIcon
          name="i-lucide-arrow-up-right"
          class="size-4"
          aria-hidden="true"
        />
      </span>
    </template>
  </UPageCard>
</template>
