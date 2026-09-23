<script setup lang="ts">
import * as z from 'zod'
import type { ApiError } from '~/types/api'
import type { Draft, Question, Card } from '~/types/catalog'

const { t } = useAppI18n()

definePageMeta({ middleware: 'auth' })
useSeoMeta({ title: () => t('task.newTitle'), description: () => t('task.newDescription') })
const api = useApi()
const { errorMessage, fieldErrors } = useApiMessages()
const canCreateTask = computed(() => api.user.value?.role === 'business')
const app = useNuxtApp()
const route = useRoute()
const state = reactive({ description: '', title: '' })
const schema = computed(() => z.object({ description: z.string({ error: t('validation.required') }).trim().min(1, t('validation.description')).max(32000, t('validation.max', { max: 32000 })) }))
const draftForm = useTemplateRef('draftForm')
const titleForm = useTemplateRef('titleForm')
useLocalizedForm(() => draftForm.value)
useLocalizedForm(() => titleForm.value)
const draft = ref<Draft | null>(null)
const questions = ref<Question[]>([])
const pending = ref(false)
const generatingQuestions = ref(false)
const assemblingCard = ref(false)
const error = ref<ApiError | null>(null)
const answers = reactive<Record<string, string>>({})
const answeredCount = computed(() => questions.value.filter(question => answers[question.id]?.trim()).length)
const savedCount = computed(() => questions.value.filter(question => question.answer && question.answer === answers[question.id]).length)
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
        method: 'POST', body: { description: state.description }
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
    assemblingCard.value = true
    try {
      for (const question of questions.value) {
        if (answers[question.id]?.trim() && answers[question.id] !== question.answer) {
          await api.request(`/catalog/questions/${question.id}`, { method: 'PATCH', body: { answer: answers[question.id] } })
        }
      }
      const card = await api.request<Card>(`/catalog/drafts/${draft.value!.id}/card`, { method: 'POST', body: { title: state.title } })
      await app.runWithContext(() => navigateTo(`/tasks/${card.id}`))
    } finally {
      assemblingCard.value = false
    }
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
  <div class="min-h-screen bg-muted/35">
    <UContainer class="py-6 lg:py-10">
      <UButton
        to="/account"
        :label="t('navigation.account')"
        icon="i-lucide-arrow-left"
        color="neutral"
        variant="link"
        class="mb-6 px-0"
      />
      <header
        data-reveal
        class="mb-8 flex flex-wrap items-start justify-between gap-4"
      >
        <div class="max-w-2xl">
          <p class="mb-2 text-xs font-semibold tracking-widest text-primary uppercase">
            {{ t('creation.eyebrow') }}
          </p>
          <h1 class="text-3xl font-semibold tracking-tight text-highlighted lg:text-4xl">
            {{ t('task.newTitle') }}
          </h1>
          <p class="mt-3 text-base leading-7 text-muted">
            {{ t('task.newDescription') }}
          </p>
        </div>
        <UBadge
          v-if="draft"
          icon="i-lucide-cloud-check"
          color="neutral"
          variant="soft"
          class="rounded-full px-3 py-2"
        >
          {{ t('creation.draftSaved') }}
        </UBadge>
      </header>
      <div
        data-reveal
        style="--reveal-delay: 60ms"
        class="mb-8 rounded-2xl border border-default bg-default p-5 sm:p-6"
      >
        <TasksTaskWorkflow :step="questions.length ? 2 : 1" />
      </div>
      <div class="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div class="min-w-0 space-y-6">
          <UAlert
            v-if="error"
            color="error"
            :title="errorMessage(error)"
            icon="i-lucide-circle-alert"
          />
          <TasksTaskAiLoading
            v-if="generatingQuestions"
            :title="t('task.generating')"
            :description="t('task.generatingHint')"
          />
          <UForm
            ref="draftForm"
            data-reveal
            style="--reveal-delay: 120ms"
            :schema="schema"
            :state="state"
            class="overflow-hidden rounded-2xl border border-default bg-default"
            @submit="createDraft"
          >
            <div class="flex items-center gap-3 border-b border-default px-6 py-5">
              <span class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><UIcon
                :name="draft ? 'i-lucide-file-check-2' : 'i-lucide-pencil-line'"
                class="size-5"
              /></span>
              <div>
                <h2 class="font-semibold text-highlighted">
                  {{ t('creation.descriptionTitle') }}
                </h2><p class="mt-1 text-xs text-muted">
                  {{ t('creation.descriptionHint') }}
                </p>
              </div>
            </div>
            <div class="space-y-6 p-6 sm:p-7">
              <details
                v-if="questions.length"
                class="rounded-xl border border-default bg-muted/30 p-4"
              >
                <summary class="cursor-pointer text-sm font-medium text-highlighted focus-visible:outline-2 focus-visible:outline-primary">
                  {{ t('creation.originalDescription') }}
                </summary>
                <p class="mt-3 text-sm leading-7 whitespace-pre-wrap break-words text-muted">
                  {{ state.description }}
                </p>
              </details>
              <UFormField
                v-else
                :label="t('task.problem')"
                name="description"
                :error="fieldErrors(error).description"
                required
              >
                <UTextarea
                  id="draft-description"
                  v-model="state.description"
                  :disabled="!!draft || pending"
                  :placeholder="t('task.placeholder')"
                  :rows="8"
                  :maxlength="32000"
                  :ui="{ base: 'rounded-xl p-4 text-base leading-7' }"
                  class="w-full"
                />
                <div class="mt-2 flex justify-between gap-4 text-xs text-muted">
                  <span>{{ t('creation.writeNaturally') }}</span><span class="shrink-0 tabular-nums">{{ state.description.length }} / 32 000</span>
                </div>
              </UFormField>
              <p class="flex items-center gap-2 text-xs text-muted">
                <UIcon
                  name="i-lucide-languages"
                  class="size-4"
                />{{ t('task.autoLanguage') }}
              </p>
              <UAlert
                v-if="!canCreateTask"
                :title="t('task.businessAccount')"
                :description="t('task.studentHint')"
                color="neutral"
                variant="soft"
              />
              <div
                v-if="!questions.length"
                class="flex flex-wrap items-center justify-between gap-4 border-t border-default pt-5"
              >
                <p class="flex items-center gap-2 text-xs text-muted">
                  <UIcon
                    name="i-lucide-lock-keyhole"
                    class="size-4"
                  />{{ t('creation.privateHint') }}
                </p>
                <UButton
                  type="submit"
                  :loading="pending"
                  :disabled="!canCreateTask"
                  :label="draft ? t('task.retry') : t('task.getQuestions')"
                  trailing-icon="i-lucide-arrow-right"
                  size="lg"
                  class="rounded-xl"
                />
              </div>
            </div>
          </UForm>
          <template v-if="canCreateTask && questions.length">
            <section
              data-reveal
              class="rounded-2xl border border-default bg-default p-6 sm:p-7"
              aria-labelledby="questions-heading"
            >
              <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p class="mb-2 text-xs font-semibold tracking-wide text-primary uppercase">
                    <UIcon
                      name="i-lucide-sparkles"
                      class="mr-1 size-4 align-middle"
                    />
                    {{ t('creation.aiAssistant') }}
                  </p><h2
                    id="questions-heading"
                    class="text-xl font-semibold text-highlighted"
                  >
                    {{ t('creation.questionsTitle') }}
                  </h2>
                </div>
                <UBadge
                  color="neutral"
                  variant="soft"
                >
                  {{ t('creation.answered', { count: answeredCount, total: questions.length }) }}
                </UBadge>
              </div>
              <p class="mb-4 text-sm leading-6 text-muted">
                {{ t('task.unknownHint') }}
              </p>
              <UProgress
                :model-value="answeredCount"
                :max="questions.length"
                :aria-label="t('creation.questionsTitle')"
                size="xs"
                class="mb-3"
              />
              <TasksTaskQuestion
                v-for="(question, index) in questions"
                :key="question.id"
                v-model="answers[question.id]"
                data-ai-question
                :style="{ '--reveal-delay': `${Math.min(index, 5) * 90 + 100}ms` }"
                :question="question"
                :index="index"
                :pending="pending"
                :error="answerErrors[question.id] ? typeof answerErrors[question.id] === 'string' ? t(String(answerErrors[question.id])) : errorMessage(answerErrors[question.id]) : undefined"
                @save="saveAnswer(question)"
              />
              <p
                class="border-t border-default pt-4 text-xs leading-5 text-muted"
                role="status"
              >
                {{ t('creation.savedAnswers', { count: savedCount, total: questions.length }) }}
              </p>
            </section>
            <UForm
              ref="titleForm"
              data-reveal
              style="--reveal-delay: 180ms"
              :schema="z.object({ title: z.string({ error: t('validation.required') }).trim().min(1, t('validation.title')).max(200, t('validation.max', { max: 200 })) })"
              :state="state"
              class="space-y-5 rounded-2xl border border-primary/25 bg-primary/5 p-6 sm:p-7"
              @submit="assemble"
            >
              <div>
                <h2 class="text-xl font-semibold text-highlighted">
                  {{ t('creation.finishTitle') }}
                </h2><p class="mt-2 text-sm leading-6 text-muted">
                  {{ t('creation.finishHint') }}
                </p>
              </div>
              <UFormField
                name="title"
                :label="t('task.title')"
                :error="fieldErrors(error).title"
                required
              >
                <UInput
                  id="draft-title"
                  v-model="state.title"
                  :disabled="pending"
                  :maxlength="200"
                  :placeholder="t('creation.titlePlaceholder')"
                  size="lg"
                  class="w-full"
                />
              </UFormField>
              <div class="flex flex-wrap items-center justify-between gap-4 border-t border-primary/15 pt-5">
                <p class="max-w-sm text-xs leading-5 text-muted">
                  {{ t('creation.reviewHint') }}
                </p>
                <UButton
                  type="submit"
                  :label="t('task.assemble')"
                  :loading="pending"
                  icon="i-lucide-sparkles"
                  size="lg"
                  class="rounded-xl"
                />
              </div>
              <TasksTaskAiLoading
                v-if="assemblingCard"
                :title="t('creation.assembling')"
                :description="t('creation.reviewHint')"
              />
            </UForm>
          </template>
        </div>
        <aside
          data-reveal
          style="--reveal-delay: 180ms"
          class="space-y-5 lg:sticky lg:top-24"
          :aria-label="t('creation.guideTitle')"
        >
          <section class="relative overflow-hidden rounded-2xl border border-primary/20 bg-primary/5 p-6">
            <UIcon
              name="i-lucide-lightbulb"
              class="mb-4 size-6 text-primary"
            />
            <h2 class="text-lg font-semibold text-highlighted">
              {{ t('creation.guideTitle') }}
            </h2>
            <p class="mt-2 text-sm leading-6 text-muted">
              {{ t('creation.guideHint') }}
            </p>
            <ul class="mt-5 space-y-5">
              <li
                v-for="(item, index) in ['context', 'result', 'materials']"
                :key="item"
                class="flex gap-3"
              >
                <span class="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">{{ index + 1 }}</span>
                <div>
                  <h3 class="text-sm font-medium text-highlighted">
                    {{ t(`creation.${item}Title`) }}
                  </h3><p class="mt-1 text-xs leading-5 text-muted">
                    {{ t(`creation.${item}Hint`) }}
                  </p>
                </div>
              </li>
            </ul>
          </section>
          <section class="rounded-2xl border border-default bg-default p-6">
            <div class="mb-3 flex size-9 items-center justify-center rounded-xl bg-muted">
              <UIcon
                name="i-lucide-shield-check"
                class="size-5 text-muted"
              />
            </div>
            <h2 class="text-sm font-semibold text-highlighted">
              {{ t('creation.controlTitle') }}
            </h2>
            <p class="mt-2 text-xs leading-6 text-muted">
              {{ t('creation.controlHint') }}
            </p>
            <UButton
              to="/account"
              :label="t('navigation.account')"
              trailing-icon="i-lucide-arrow-up-right"
              variant="link"
              color="neutral"
              class="mt-3 px-0"
            />
          </section>
        </aside>
      </div>
    </UContainer>
  </div>
</template>

<style scoped>
[data-reveal], [data-ai-question] {
  animation: task-reveal 480ms cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: var(--reveal-delay, 0ms);
}
[data-ai-question]:focus-within {
  animation: none;
}
@keyframes task-reveal {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
@media (prefers-reduced-motion: reduce) {
  [data-reveal], [data-ai-question] { animation: none; }
}
</style>
