<script setup lang="ts">
import * as z from 'zod'
import type { ApiError } from '~/types/api'
import type { Draft, Question, Card } from '~/types/catalog'

definePageMeta({ middleware: 'auth' })
const api = useApi()
const app = useNuxtApp()
const route = useRoute()
const state = reactive({ description: '', title: '' })
const schema = z.object({ description: z.string().trim().min(1, 'Опишите вашу потребность').max(32000) })
const draft = ref<Draft | null>(null)
const questions = ref<Question[]>([])
const pending = ref(false)
const error = ref<ApiError | null>(null)
const answers = reactive<Record<string, string>>({})
const answerErrors = reactive<Record<string, string>>({})

async function action(work: () => Promise<void>) {
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
  questions.value = await api.request<Question[]>(`/catalog/drafts/${draft.value!.id}/questions`, { method: 'POST' })
  for (const question of questions.value) answers[question.id] = question.answer || ''
}
async function createDraft() {
  await action(async () => {
    if (!draft.value) {
      draft.value = await api.request<Draft>('/catalog/drafts', { method: 'POST', body: { description: state.description } })
      await app.runWithContext(() => navigateTo({ query: { draft: draft.value!.id } }, { replace: true }))
    }
    await loadQuestions()
  })
}
async function saveAnswer(question: Question) {
  await action(async () => {
    answerErrors[question.id] = ''
    if (!answers[question.id]?.trim()) {
      answerErrors[question.id] = 'Введите ответ'
      return
    }
    try {
      const saved = await api.request<Question>(`/catalog/questions/${question.id}`, { method: 'PATCH', body: { answer: answers[question.id] } })
      question.answer = saved.answer
    } catch (cause) {
      answerErrors[question.id] = (cause as ApiError).fields.answer || (cause as ApiError).detail
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
    questions.value = await api.request<Question[]>(`/catalog/drafts/${draft.value.id}/questions`)
    for (const question of questions.value) answers[question.id] = question.answer || ''
  })
}
</script>

<template>
  <UContainer class="max-w-3xl py-12 space-y-6">
    <UPageHeader
      title="Новая бизнес-задача"
      description="Опишите потребность. Ответы на уточняющие вопросы помогут подготовить карточку."
    />
    <TasksTaskWorkflow :step="questions.length ? 2 : 1" />
    <UAlert
      v-if="api.user.value?.role !== 'business'"
      title="Создание задач доступно бизнесу"
    />
    <template v-else>
      <UAlert
        v-if="error"
        color="error"
        :title="error.detail"
        :description="error.code"
      />
      <UForm
        :schema="schema"
        :state="state"
        class="space-y-4"
        @submit="createDraft"
      >
        <UFormField
          label="Описание потребности"
          name="description"
          :error="error?.fields.description"
        >
          <UTextarea
            v-model="state.description"
            :disabled="!!draft || pending"
            placeholder="Например: хотим сократить время обработки заявок. Сейчас менеджеры вручную переносят их из почты в таблицу."
            :rows="6"
            class="w-full"
          />
        </UFormField>
        <UButton
          v-if="!questions.length"
          type="submit"
          :loading="pending"
          :label="draft ? 'Повторить уточнение' : 'Сохранить и получить вопросы'"
        />
      </UForm>
      <TasksTaskQuestion
        v-for="(question, index) in questions"
        :key="question.id"
        v-model="answers[question.id]"
        :question="question"
        :index="index"
        :pending="pending"
        :error="answerErrors[question.id]"
        @save="saveAnswer(question)"
      />
      <UForm
        v-if="questions.length"
        :schema="z.object({ title: z.string().trim().min(1, 'Введите название').max(200) })"
        :state="state"
        class="space-y-4"
        @submit="assemble"
      >
        <UFormField
          name="title"
          label="Название задачи"
          :error="error?.fields.title"
        >
          <UInput
            v-model="state.title"
            class="w-full"
          />
        </UFormField>
        <p class="text-muted">
          Неизвестные данные можно оставить пустыми. Проверьте карточку перед публикацией.
        </p>
        <UButton
          type="submit"
          label="Собрать карточку"
          :loading="pending"
        />
      </UForm>
    </template>
  </UContainer>
</template>
