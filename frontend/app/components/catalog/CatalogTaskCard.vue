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
    <UBadge
      color="neutral"
      variant="subtle"
    >
      {{ t(`topics.${entry.task.topic || 'unspecified'}`) }}
    </UBadge>
    <p
      v-if="(entry.task.rating?.total ?? 0) < 40"
      class="text-sm font-medium text-primary"
    >
      {{ t('catalogFilters.lowRatingOpen') }}
    </p>
    <h2 class="mt-7 line-clamp-2 text-xl font-semibold leading-snug tracking-tight text-highlighted">
      {{ entry.task.title }}
    </h2>
    <p class="mt-3 line-clamp-3 text-sm leading-7 text-muted">
      {{ entry.task.context || t('catalog.noContext') }}
    </p>
    <div
      v-if="entry.task.expected_result"
      class="rounded-xl bg-muted/50 p-4"
    >
      <p class="mb-1 text-xs font-medium text-highlighted">
        {{ t('fields.expected_result') }}
      </p>
      <p class="line-clamp-2 text-sm leading-6 text-muted">
        {{ entry.task.expected_result }}
      </p>
    </div>
    <template #footer>
      <span class="flex items-center justify-between gap-3 border-t border-default pt-4 text-sm font-medium text-primary">
        {{ t('interface.openTask') }}
        <UIcon
          name="i-lucide-arrow-right"
          class="size-4 shrink-0"
          aria-hidden="true"
        />
      </span>
    </template>
  </AppCard>
</template>
