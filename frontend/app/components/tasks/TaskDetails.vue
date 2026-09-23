<script setup lang="ts">
import { cardFields } from '~/types/catalog'
import type { Card } from '~/types/catalog'

defineProps<{ card: Card }>()
const { t } = useAppI18n()
</script>

<template>
  <dl data-app-panel>
    <div
      v-for="field in cardFields"
      :id="`task-${field.key}`"
      :key="field.key"
      class="grid scroll-mt-24 gap-3 border-b border-default py-6 first:pt-0 last:border-0 last:pb-0 md:grid-cols-[10rem_minmax(0,1fr)] md:gap-8"
    >
      <dt class="text-sm font-medium text-muted">
        {{ t(`fields.${field.key}`) }}
      </dt>
      <dd class="whitespace-pre-line break-words text-sm leading-7 text-default">
        {{ card[field.key] || t('task.notSpecified') }}
      </dd>
    </div>
  </dl>
</template>
