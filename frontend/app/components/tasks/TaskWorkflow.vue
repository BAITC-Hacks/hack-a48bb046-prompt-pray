<script setup lang="ts">
const { t } = useAppI18n()
defineProps<{ step: number }>()
const steps = computed(() => [t('workflow.describe'), t('workflow.clarify'), t('workflow.publish')])
</script>

<template>
  <ol
    :aria-label="t('workflow.label')"
    class="grid grid-cols-3 gap-3"
  >
    <li
      v-for="(label, index) in steps"
      :key="index"
      :aria-current="step === index + 1 ? 'step' : undefined"
      class="border-t-2 pt-3 text-sm"
      :class="index + 1 <= step ? 'border-primary text-primary' : 'border-default text-muted'"
    >
      <span class="mb-1 block text-xs font-semibold tabular-nums">0{{ index + 1 }}</span>
      {{ label }}
    </li>
  </ol>
</template>
