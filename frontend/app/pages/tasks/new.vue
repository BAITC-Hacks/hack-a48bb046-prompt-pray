<script setup lang="ts">
import * as z from 'zod'
import type { ApiError } from '~/types/api'
import type { Draft, DraftLocale, Question, Card } from '~/types/catalog'

const { t, locale } = useAppI18n()

definePageMeta({ middleware: 'auth' })
useSeoMeta({ title: () => t('task.newTitle'), description: () => t('task.newDescription') })
const api = useApi()
const { errorMessage, fieldErrors } = useApiMessages()
const canCreateTask = computed(() => api.user.value?.role === 'business')
const app = useNuxtApp()
const route = useRoute()
const state = reactive({ description: '', title: '', locale: locale.value as DraftLocale })
const languages = [{ label: 'Русский', value: 'ru' }, { label: 'Қазақша', value: 'kk' }, { label: 'English', value: 'en' }]
const schema = computed(() => z.object({ description: z.string({ error: t('validation.required') }).trim().min(1, t('validation.description')).max(32000, t('validation.max', { max: 32000 })) }))
const draftForm = useTemplateRef('draftForm')
const titleForm = useTemplateRef('titleForm')
useLocalizedForm(() => draftForm.value)
useLocalizedForm(() => titleForm.value)
const draft = ref<Draft | null>(null)
const questions = ref<Question[]>([])
const pending = ref(false)
const generatingQuestions = ref(false)
const error = ref<ApiError | null>(null)
const answers = reactive<Record<string, string>>({})
const answerErrors = reactive<Record<string, string | ApiError>>({})

async function action(work: () => Promise<void>) {
  if (pending.value) return
  pending.value = true
  error.value = null
  try {
    await work()
  } catch (cause) {
    error.value = cause as ApiError
  } finally {
    pending.value = false
  }
}
async function loadQuestions() {
  generatingQuestions.value = true
  try {
    questions.value = await api.request<Question[]>(`/catalog/drafts/${draft.value!.id}/questions`, { method: 'POST' })
    for (const question of questions.value) answers[question.id] ??= question.answer || ''
  } finally {
    generatingQuestions.value = false
  }
}
async function createDraft() {
  if (!canCreateTask.value) return
  await action(async () => {
    if (!draft.value) {
      draft.value = await api.request<Draft>('/catalog/drafts', {
        method: 'POST', body: { description: state.description, locale: state.locale }
      })
      await app.runWithContext(() => navigateTo({ query: { draft: draft.value!.id } }, { replace: true }))
    }
    await loadQuestions()
  })
}
async function saveAnswer(question: Question) {
  await action(async () => {
    answerErrors[question.id] = ''
    if (!answers[question.id]?.trim()) {
      answerErrors[question.id] = 'validation.answer'
      return
    }
    try {
      const saved = await api.request<Question>(`/catalog/questions/${question.id}`, { method: 'PATCH', body: { answer: answers[question.id] } })
      question.answer = saved.answer
    } catch (cause) {
      answerErrors[question.id] = cause as ApiError
      throw cause
    }
  })
}
async function assemble() {
  await action(async () => {
    for (const question of questions.value) {
      if (answers[question.id]?.trim() && answers[question.id] !== question.answer) {
        await api.request(`/catalog/questions/${question.id}`, { method: 'PATCH', body: { answer: answers[question.id] } })
      }
    }
    const card = await api.request<Card>(`/catalog/drafts/${draft.value!.id}/card`, { method: 'POST', body: { title: state.title } })
    await app.runWithContext(() => navigateTo(`/tasks/${card.id}`))
  })
}
if (typeof route.query.draft === 'string') {
  await action(async () => {
    draft.value = await api.request<Draft>(`/catalog/drafts/${route.query.draft}`)
    if (draft.value.card_id) {
      await app.runWithContext(() => navigateTo(`/tasks/${draft.value!.card_id}`, { replace: true }))
      return
    }
    state.description = draft.value.description
    state.locale = draft.value.locale
    questions.value = await api.request<Question[]>(`/catalog/drafts/${draft.value.id}/questions`)
    for (const question of questions.value) answers[question.id] = question.answer || ''
  })
}
</script>

<template>
  <UContainer class="max-w-3xl py-12 space-y-6">
    <UPageHeader
      :title="t('task.newTitle')"
      :description="t('task.newDescription')"
    />
    <TasksTaskWorkflow :step="questions.length ? 2 : 1" />
    <UAlert
      v-if="error"
      color="error"
      :title="errorMessage(error)"
    />
    <UAlert
      v-if="generatingQuestions"
      :title="t('task.generating')"
      :description="t('task.generatingHint')"
      icon="i-lucide-loader-circle"
      role="status"
    />
    <UForm
      ref="draftForm"
      :schema="schema"
      :state="state"
      class="space-y-4 rounded-2xl border border-default bg-default p-6"
      @submit="createDraft"
    >
      <UFormField
        :label="t('task.questionLanguage')"
        name="locale"
        :description="t('task.languageHint')"
        :error="fieldErrors(error).locale"
      >
        <USelect
          v-model="state.locale"
          :items="languages"
          :disabled="!!draft || pending"
          class="w-full"
        />
      </UFormField>
      <UFormField
        :label="t('task.problem')"
        name="description"
        :error="fieldErrors(error).description"
      >
        <UTextarea
          v-model="state.description"
          :disabled="!!draft || pending"
          :placeholder="t('task.placeholder')"
          :rows="6"
          :maxlength="32000"
          :ui="{ base: 'min-h-40 p-4 leading-relaxed' }"
          class="w-full"
        />
      </UFormField>
      <UAlert
        v-if="!canCreateTask"
        :title="t('task.businessAccount')"
        :description="t('task.studentHint')"
        color="neutral"
        variant="soft"
      />
      <UButton
        v-if="!questions.length"
        type="submit"
        :loading="pending"
        :disabled="!canCreateTask"
        :label="draft ? t('task.retry') : t('task.getQuestions')"
      />
    </UForm>
    <template v-if="canCreateTask">
      <TasksTaskQuestion
        v-for="(question, index) in questions"
        :key="question.id"
        v-model="answers[question.id]"
        :question="question"
        :index="index"
        :pending="pending"
        :error="answerErrors[question.id] ? typeof answerErrors[question.id] === 'string' ? t(String(answerErrors[question.id])) : errorMessage(answerErrors[question.id]) : undefined"
        @save="saveAnswer(question)"
      />
      <UForm
        v-if="questions.length"
        ref="titleForm"
        :schema="z.object({ title: z.string({ error: t('validation.required') }).trim().min(1, t('validation.title')).max(200, t('validation.max', { max: 200 })) })"
        :state="state"
        class="space-y-4"
        @submit="assemble"
      >
        <UFormField
          name="title"
          :label="t('task.title')"
          :error="fieldErrors(error).title"
        >
          <UInput
            v-model="state.title"
            class="w-full"
          />
        </UFormField>
        <p class="text-muted">
          {{ t('task.unknownHint') }}
        </p>
        <UButton
          type="submit"
          :label="t('task.assemble')"
          :loading="pending"
        />
      </UForm>
    </template>
  </UContainer>
</template>
