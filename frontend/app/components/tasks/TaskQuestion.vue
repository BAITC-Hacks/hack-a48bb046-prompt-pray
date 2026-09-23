<script setup lang="ts">
import type { Question } from '~/types/catalog'

const answer = defineModel<string>()
const props = defineProps<{ question: Question, pending: boolean, error?: string, index: number }>()
const emit = defineEmits<{ save: [] }>()
const saved = computed(() => !!props.question.answer && props.question.answer === answer.value)
</script>

<template>
  <UPageCard>
    <UFormField
      :label="`${index + 1}. ${question.question}`"
      :error="error"
      :name="question.id"
    >
      <UTextarea
        v-model="answer"
        class="w-full"
        :rows="3"
        :maxlength="10000"
        :disabled="pending"
        placeholder="Добавьте известные детали"
      />
    </UFormField>
    <div class="flex items-center gap-3">
      <UButton
        :disabled="pending || saved || !answer?.trim()"
        :label="saved ? 'Ответ сохранён' : 'Сохранить ответ'"
        :icon="saved ? 'i-lucide-check' : 'i-lucide-save'"
        variant="outline"
        @click="emit('save')"
      />
      <span
        v-if="!answer?.trim()"
        class="text-xs text-muted"
      >Можно заполнить позже</span>
    </div>
  </UPageCard>
</template>
