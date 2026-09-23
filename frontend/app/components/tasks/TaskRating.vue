<script setup lang="ts">
import { cardFields } from '~/types/catalog'
import type { Card } from '~/types/catalog'

const props = defineProps<{ rating: Card['rating'], compact?: boolean }>()
const score = computed(() => props.rating?.total ?? 0)
const color = computed(() => score.value >= 90 ? 'success' : score.value >= 70 ? 'primary' : score.value >= 40 ? 'warning' : 'neutral')
</script>

<template>
  <UBadge
    v-if="compact"
    :color="color"
    variant="subtle"
    :label="`${score} / 100 · ${rating?.readiness || 'черновик'}`"
  />
  <UPageCard
    v-else
    title="Готовность задачи"
    description="Чем полнее описание, тем выше позиция в каталоге. Отклики доступны при любом рейтинге."
  >
    <div class="flex items-center justify-between gap-4">
      <span class="text-3xl font-semibold tabular-nums">{{ score }} <span class="text-base font-normal text-muted">/ 100</span></span>
      <UBadge
        :color="color"
        variant="subtle"
        :label="rating?.readiness || 'черновик'"
      />
    </div>
    <UProgress
      :model-value="score"
      :max="100"
      :color="color"
      aria-label="Полнота описания задачи"
    />
    <dl class="space-y-3">
      <div
        v-for="field in cardFields"
        :key="field.key"
        class="flex justify-between gap-4 text-sm"
      >
        <dt class="text-muted">
          {{ field.label }}
        </dt>
        <dd class="shrink-0 font-medium tabular-nums">
          {{ rating?.[field.key] ?? 0 }} / {{ field.points }}
        </dd>
      </div>
    </dl>
  </UPageCard>
</template>
