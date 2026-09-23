<script setup lang="ts">
import type { CatalogEntry } from '~/types/catalog'

const { t } = useAppI18n()

defineProps<{ entry: CatalogEntry }>()
</script>

<template>
  <AppCard
    :to="`/tasks/${entry.task_id}`"
  >
    <div class="flex items-center justify-between gap-4">
      <TasksTaskRating
        :rating="entry.task.rating"
        compact
      />
      <UIcon
        name="i-lucide-arrow-up-right"
        class="size-5 shrink-0 text-dimmed transition-colors group-hover:text-primary"
        aria-hidden="true"
      />
    </div>
    <h2 class="mt-7 line-clamp-2 text-xl font-semibold leading-snug tracking-tight text-highlighted">
      {{ entry.task.title }}
    </h2>
    <p class="mt-3 line-clamp-3 text-sm leading-7 text-muted">
      {{ entry.task.context || t('catalog.noContext') }}
    </p>
  </AppCard>
</template>
