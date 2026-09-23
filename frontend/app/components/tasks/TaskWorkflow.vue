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
      class="flex flex-col gap-3 rounded-xl p-2 text-xs sm:flex-row sm:items-center sm:p-3 sm:text-sm"
      :class="index + 1 === step ? 'bg-primary/5 text-primary' : index + 1 < step ? 'text-primary' : 'text-muted'"
    >
      <span
        class="flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold tabular-nums"
        :class="index + 1 === step ? 'bg-primary text-inverted' : index + 1 < step ? 'bg-primary/10 text-primary' : 'bg-muted text-muted'"
      >
        <UIcon
          v-if="index + 1 < step"
          name="i-lucide-check"
          class="size-4"
        />
        <template v-else>0{{ index + 1 }}</template>
      </span>
      <span class="font-medium">{{ label }}</span>
    </li>
  </ol>
</template>
