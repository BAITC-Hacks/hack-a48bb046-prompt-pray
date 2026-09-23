<script setup lang="ts">
import { taskFields, taskRating, readiness } from '~/utils/task-rating'

const route = useRoute()
const workspace = useTasks()
const task = computed(() => workspace.byId(String(route.params.id)))
const editMode = ref(false)
const saved = ref(false)
const titleDraft = ref('')
const answerDraft = ref<Record<string, string>>({})
const questionDraft = ref<NonNullable<typeof task.value>['questions']>([])
const displayedAnswers = computed(() => editMode.value ? answerDraft.value : task.value)
const score = computed(() => displayedAnswers.value ? taskRating(displayedAnswers.value as import('../../../shared/types/tasks').TaskAnswers) : 0)
const filledCount = computed(() => taskFields.filter(field => (displayedAnswers.value?.[field.key] || '').trim().length >= 12).length)
const level = computed(() => readiness(score.value))

function resetDraft() {
  const value = task.value
  if (value) {
    questionDraft.value = value.questions.map(question => ({ ...question }))
    titleDraft.value = value.title
    answerDraft.value = Object.fromEntries(taskFields.map(field => [field.key, value[field.key]]))
  }
}

watch(task, resetDraft, { immediate: true })

function startEditing() {
  resetDraft()
  saved.value = false
  editMode.value = true
}

function cancelEditing() {
  resetDraft()
  editMode.value = false
}

useSeoMeta({ title: computed(() => task.value?.title || 'Задача') })

function saveAnswers() {
  if (!task.value) return
  task.value.questions = questionDraft.value.map(question => ({ ...question }))
  task.value.title = titleDraft.value.trim() || 'Новая задача'
  for (const field of taskFields) task.value[field.key] = answerDraft.value[field.key] || ''
  workspace.save(task.value)
  editMode.value = false
  saved.value = true
}

async function publish() {
  if (!task.value || task.value.status === 'published') return
  const unanswered = task.value.questions.filter(question => !question.answer.trim()).length
  if (unanswered) return
  task.value.status = 'published'
  workspace.save(task.value)
  await navigateTo('/catalog')
}
</script>

<template>
  <UContainer
    v-if="task"
    class="py-10 sm:py-14 max-w-5xl"
  >
    <div class="flex flex-wrap items-center gap-3 mb-5">
      <UBadge
        :label="task.status === 'published' ? 'Опубликована · демонстрация' : 'Черновик · демонстрация'"
        :color="task.status === 'published' ? 'success' : 'warning'"
        variant="subtle"
      />
      <ULink
        to="/account"
        class="text-sm text-muted hover:text-default"
      >Все мои задачи</ULink>
    </div>
    <UAlert
      color="warning"
      variant="subtle"
      title="Демонстрационный режим"
      description="Карточка и рейтинг хранятся в браузере и пока недоступны другим пользователям."
      class="mb-6"
    />
    <div class="grid lg:grid-cols-[1fr_19rem] gap-8 items-start">
      <main class="min-w-0">
        <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
          <div>
            <p class="text-sm text-muted">
              {{ task.status === 'published' ? 'Задача в каталоге этого браузера' : 'Шаг 2 из 3 · ответы и карточка' }}
            </p>
            <h1 class="text-3xl sm:text-4xl font-bold tracking-tight mt-2">
              {{ task.title }}
            </h1>
          </div>
          <UButton
            v-if="!editMode"
            label="Редактировать"
            icon="i-lucide-pencil"
            color="neutral"
            variant="outline"
            @click="startEditing"
          />
        </div>
        <p class="text-muted mb-8">
          {{ task.brief }}
        </p>

        <UCard
          v-if="task.questions.length"
          class="mb-8"
        >
          <template #header>
            <div class="flex items-start gap-3">
              <UIcon
                name="i-lucide-message-circle-question"
                class="text-primary size-5 mt-1"
              />
              <div>
                <h2 class="font-semibold">
                  Уточните детали
                </h2>
                <p class="text-sm text-muted mt-1">
                  Вопросы подобраны по вашему описанию. Напишите ответы, которых пока не хватает.
                </p>
              </div>
            </div>
          </template>
          <div class="space-y-5">
            <UFormField
              v-for="question in questionDraft"
              :key="question.id"
              :label="question.question"
              :name="`question-${question.id}`"
              required
            >
              <UTextarea
                v-model="question.answer"
                :rows="3"
                autoresize
                maxlength="1200"
                placeholder="Ваш ответ…"
                class="w-full"
                :disabled="!editMode"
              />
            </UFormField>
            <UAlert
              color="neutral"
              variant="subtle"
              title="Подсказка сформирована из описания"
              description="В этой демонстрации вопросы подбираются по словам в тексте. AI-сервис для реальных уточнений пока не подключён."
            />
          </div>
        </UCard>

        <section aria-labelledby="card-title">
          <div class="flex flex-wrap justify-between items-center gap-3 mb-4">
            <div>
              <h2
                id="card-title"
                class="text-xl font-semibold"
              >
                Карточка задачи
              </h2>
              <p class="text-sm text-muted mt-1">
                Хорошо описанные задачи помогают командам быстрее предложить решение.
              </p>
            </div>
            <span class="text-xs text-muted">{{ editMode ? 'Режим редактирования' : 'Предпросмотр' }}</span>
          </div>
          <UCard>
            <UFormField
              label="Название проекта"
              name="title"
              class="mb-6"
            >
              <UInput
                v-if="editMode"
                v-model="titleDraft"
                maxlength="120"
                class="w-full"
              />
              <p
                v-else
                class="font-medium text-lg"
              >
                {{ task.title }}
              </p>
            </UFormField>
            <div class="divide-y divide-default">
              <div
                v-for="field in taskFields"
                :key="field.key"
                class="py-5 first:pt-0 last:pb-0"
              >
                <div class="flex justify-between items-start gap-4 mb-2">
                  <h3 class="font-medium">
                    {{ field.label }}
                  </h3>
                  <UBadge
                    :label="`${field.points} б.`"
                    color="neutral"
                    variant="subtle"
                    size="sm"
                  />
                </div>
                <UFormField
                  :name="field.key"
                  :description="field.description"
                >
                  <UTextarea
                    v-if="editMode"
                    v-model="answerDraft[field.key]"
                    :rows="3"
                    autoresize
                    maxlength="2400"
                    class="w-full"
                    :placeholder="field.description"
                  />
                  <p
                    v-else
                    class="text-sm"
                    :class="task[field.key].trim().length >= 12 ? 'text-default' : 'text-muted italic'"
                  >
                    {{ task[field.key] || 'Пока не заполнено' }}
                  </p>
                </UFormField>
              </div>
            </div>
            <template #footer>
              <div class="flex flex-wrap gap-3 justify-between items-center">
                <span
                  v-if="saved"
                  role="status"
                  class="text-sm text-success"
                >Изменения сохранены. Рейтинг обновлён.</span>
                <span
                  v-else
                  class="text-sm text-muted"
                >{{ editMode ? 'Заполните поля и сохраните.' : 'Рейтинг автоматически пересчитывается при сохранении.' }}</span>
                <div
                  v-if="editMode"
                  class="flex gap-2"
                >
                  <UButton
                    label="Отмена"
                    color="neutral"
                    variant="ghost"
                    @click="cancelEditing"
                  />
                  <UButton
                    label="Сохранить"
                    icon="i-lucide-save"
                    @click="saveAnswers"
                  />
                </div>
              </div>
            </template>
          </UCard>
        </section>
      </main>

      <aside class="lg:sticky lg:top-24 space-y-4">
        <UCard>
          <template #header>
            <h2 class="font-semibold">
              Полнота карточки
            </h2>
          </template>
          <div class="flex items-baseline gap-2 mb-3">
            <span class="text-5xl font-bold tabular-nums">{{ score }}</span>
            <span class="text-muted">/ 100</span>
          </div>
          <UProgress
            :model-value="score"
            :max="100"
            :color="level.color"
            aria-label="Рейтинг полноты задачи"
          />
          <UBadge
            :label="level.label"
            :color="level.color"
            variant="subtle"
            class="mt-4"
          />
          <p class="text-sm text-muted mt-3">
            {{ filledCount }} из 7 критериев заполнено
          </p>
          <div class="mt-5 space-y-2">
            <div
              v-for="field in taskFields"
              :key="field.key"
              class="flex justify-between gap-3 text-xs"
            >
              <span class="truncate text-muted">{{ field.label }}</span>
              <span>{{ (displayedAnswers?.[field.key] || '').trim().length >= 12 ? field.points : 0 }}/{{ field.points }}</span>
            </div>
          </div>
          <USeparator class="my-5" />
          <div class="space-y-2">
            <UButton
              v-if="editMode"
              label="Сохранить изменения"
              icon="i-lucide-save"
              block
              @click="saveAnswers"
            />
            <UButton
              v-else-if="task.status === 'draft'"
              label="Подтвердить и опубликовать"
              icon="i-lucide-send"
              block
              :disabled="task.questions.some(question => !question.answer.trim())"
              @click="publish"
            />
            <UButton
              v-else
              label="Посмотреть отклики"
              icon="i-lucide-messages-square"
              block
              :to="`/tasks/${task.id}/proposals`"
            />
            <p
              v-if="task.status === 'draft' && task.questions.some(question => !question.answer.trim())"
              class="text-xs text-muted text-center"
            >
              Сначала ответьте на все три уточняющих вопроса.
            </p>
          </div>
        </UCard>
        <UButton
          label="← В каталог"
          to="/catalog"
          color="neutral"
          variant="ghost"
        />
      </aside>
    </div>
  </UContainer>
  <UContainer
    v-else
    class="py-24 max-w-xl"
  >
    <UEmpty
      icon="i-lucide-file-question"
      title="Задача не найдена"
      description="Она могла быть удалена или сохранена в другом браузере."
    >
      <template #actions>
        <UButton
          label="Открыть каталог"
          to="/catalog"
        />
      </template>
    </UEmpty>
  </UContainer>
</template>
