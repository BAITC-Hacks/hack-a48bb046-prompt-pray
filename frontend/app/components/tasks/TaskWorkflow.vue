<script setup lang="ts">
defineProps<{ step: number }>()
const steps = ['Описание', 'Уточнение', 'Проверка и публикация']
</script>

<template>
  <ol
    aria-label="Этапы создания задачи"
    class="grid grid-cols-3 gap-3"
  >
    <li
      v-for="(label, index) in steps"
      :key="label"
      :aria-current="step === index + 1 ? 'step' : undefined"
      class="border-t-2 pt-3 text-sm"
      :class="index + 1 <= step ? 'border-primary text-primary' : 'border-default text-muted'"
    >
      <span class="mb-1 block text-xs font-semibold tabular-nums">0{{ index + 1 }}</span>
      {{ label }}
    </li>
  </ol>
</template>
