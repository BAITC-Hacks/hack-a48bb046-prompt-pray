<script setup lang="ts">
import { cardFields } from '~/types/catalog'
import type { Card } from '~/types/catalog'

const { t, n } = useAppI18n()

const props = defineProps<{ rating: Card['rating'], compact?: boolean }>()
const score = computed(() => props.rating?.total ?? 0)
// Compatibility with the API until T-16 supplies readiness_code.
const readinessCode = computed(() => props.rating?.readiness_code || (score.value >= 90 ? 'priority' : score.value >= 70 ? 'ready' : score.value >= 40 ? 'working' : 'draft'))
const readinessLabel = computed(() => t(`rating.${readinessCode.value}`))
const color = computed(() => score.value >= 90 ? 'success' : score.value >= 70 ? 'primary' : score.value >= 40 ? 'warning' : 'neutral')
</script>

<template>
  <UBadge
    v-if="compact"
    :color="color"
    variant="subtle"
    :label="`${n(score)} / ${n(100)} · ${readinessLabel}`"
  />
  <AppCard
    v-else
    variant="soft"
    :aria-label="t('rating.title')"
  >
    <h2 class="text-sm font-semibold text-highlighted">
      {{ t('rating.title') }}
    </h2>
    <div class="flex items-center justify-between gap-4">
      <span class="text-3xl font-semibold tabular-nums">{{ n(score) }} <span class="text-base font-normal text-muted">/ {{ n(100) }}</span></span>
      <UBadge
        :color="color"
        variant="subtle"
        :label="readinessLabel"
      />
    </div>
    <UProgress
      :model-value="score"
      :max="100"
      :color="color"
      :aria-label="t('rating.label')"
    />
    <details class="text-sm">
      <summary class="cursor-pointer text-muted">
        {{ t('rating.breakdown') }}
      </summary>
      <dl class="mt-4 space-y-3">
        <div
          v-for="field in cardFields"
          :key="field.key"
          class="flex justify-between gap-4 text-sm"
        >
          <dt class="text-muted">
            {{ t(`fields.${field.key}`) }}
          </dt>
          <dd class="shrink-0 font-medium tabular-nums">
            {{ n(rating?.[field.key] ?? 0) }} / {{ n(field.points) }}
          </dd>
        </div>
      </dl>
    </details>
  </AppCard>
</template>
