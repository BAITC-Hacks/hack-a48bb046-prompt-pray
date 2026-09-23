<script setup lang="ts">
import type { Question } from '~/types/catalog'

const { t } = useAppI18n()

const answer = defineModel<string>()
const props = defineProps<{ question: Question, pending: boolean, error?: string, index: number }>()
const emit = defineEmits<{ save: [] }>()
const saved = computed(() => !!props.question.answer && props.question.answer === answer.value)
</script>

<template>
  <section data-question-card>
    <span
      data-question-number
      aria-hidden="true"
    >{{ String(index + 1).padStart(2, '0') }}</span>
    <div class="min-w-0 space-y-3">
      <UFormField
        :label="question.question"
        :error="error"
        :name="question.id"
      >
        <UTextarea
          :id="`answer-${question.id}`"
          v-model="answer"
          class="w-full"
          :rows="3"
          :maxlength="10000"
          :disabled="pending"
          variant="soft"
          :ui="{ base: 'rounded-xl p-4 leading-relaxed' }"
          :placeholder="t('task.answerPlaceholder')"
        />
      </UFormField>
      <div class="flex items-center gap-3">
        <UButton
          :disabled="pending || saved || !answer?.trim()"
          :label="saved ? t('task.saved') : t('task.save')"
          :icon="saved ? 'i-lucide-check' : undefined"
          color="neutral"
          variant="ghost"
          size="sm"
          @click="emit('save')"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
[data-question-card] {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr);
  gap: 1rem;
  padding: 1.75rem 0;
  border-top: 1px solid var(--ui-border);
}
[data-question-number] { padding-top: 0.125rem; color: var(--ui-text-dimmed); font-size: 0.75rem; font-variant-numeric: tabular-nums; }
</style>
