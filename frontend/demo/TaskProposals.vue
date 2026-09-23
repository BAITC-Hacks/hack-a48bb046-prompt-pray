<script setup lang="ts">
import type * as z from 'zod'
import { proposalSchema as schema, isWebUrl } from '~/utils/task-validation'
import type { FormSubmitEvent } from '@nuxt/ui'

useSeoMeta({ title: 'Командные предложения' })
const route = useRoute()
const workspace = useTasks()
const task = computed(() => workspace.byId(String(route.params.id)))
const pending = ref(false)
const error = ref('')
const saved = ref(false)
type Schema = z.output<typeof schema>
const formState = reactive<Schema>({ team: '', idea: '', plan: '', link: '' })

function toggleSelected(id: string) {
  if (!task.value) return
  const selected = task.value.selectedProposalIds
  task.value.selectedProposalIds = selected.includes(id)
    ? selected.filter(value => value !== id)
    : [...selected, id]
  workspace.save(task.value)
  saved.value = true
}

async function onSubmit({ data }: FormSubmitEvent<Schema>) {
  if (!task.value) return
  pending.value = true
  error.value = ''
  try {
    workspace.addProposal(task.value, data)
    formState.team = ''
    formState.idea = ''
    formState.plan = ''
    formState.link = ''
  } catch {
    error.value = 'Не удалось сохранить отклик в браузере.'
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <UContainer
    v-if="task"
    class="py-12 max-w-5xl"
  >
    <UBadge
      label="Демонстрационные отклики · этот браузер"
      color="warning"
      variant="subtle"
      class="mb-5"
    />
    <p class="text-sm text-muted">
      Предложения к задаче
    </p>
    <h1 class="text-3xl sm:text-4xl font-bold tracking-tight mt-2">
      {{ task.title }}
    </h1>
    <p class="mt-3 text-muted max-w-3xl">
      {{ task.brief }}
    </p>
    <div class="grid lg:grid-cols-[minmax(0,1fr)_20rem] gap-8 mt-9 items-start">
      <section aria-labelledby="proposals-title">
        <div class="flex flex-wrap justify-between items-center gap-3 mb-5">
          <div>
            <h2
              id="proposals-title"
              class="text-xl font-semibold"
            >
              Предложения команд
            </h2>
            <p class="text-sm text-muted mt-1">
              Выбор остаётся за представителем бизнеса. Можно выбрать любое число команд или никого.
            </p>
          </div>
          <UBadge
            :label="`${task.selectedProposalIds.length} выбрано`"
            :color="task.selectedProposalIds.length ? 'success' : 'neutral'"
            variant="subtle"
          />
        </div>
        <UCard
          v-for="proposal in task.proposals"
          :key="proposal.id"
          class="mb-4"
        >
          <template #header>
            <div class="flex justify-between items-center gap-3">
              <h3 class="font-semibold">
                {{ proposal.team }}
              </h3>
              <UBadge
                v-if="task.selectedProposalIds.includes(proposal.id)"
                label="Выбрана бизнесом"
                color="success"
                variant="subtle"
              />
            </div>
          </template>
          <div class="space-y-4">
            <div>
              <h4 class="text-sm font-medium">
                Идея
              </h4><p class="text-sm text-muted mt-1">
                {{ proposal.idea }}
              </p>
            </div>
            <div>
              <h4 class="text-sm font-medium">
                План
              </h4><p class="text-sm text-muted mt-1">
                {{ proposal.plan }}
              </p>
            </div>
            <ULink
              v-if="isWebUrl(proposal.link)"
              :to="proposal.link"
              target="_blank"
              rel="noopener noreferrer"
              class="text-sm text-primary"
            >Посмотреть материалы ↗</ULink>
          </div>
          <template #footer>
            <UButton
              :label="task.selectedProposalIds.includes(proposal.id) ? 'Отменить выбор' : 'Выбрать команду'"
              :icon="task.selectedProposalIds.includes(proposal.id) ? 'i-lucide-circle-minus' : 'i-lucide-check'"
              :color="task.selectedProposalIds.includes(proposal.id) ? 'neutral' : 'primary'"
              :variant="task.selectedProposalIds.includes(proposal.id) ? 'outline' : 'solid'"
              @click="toggleSelected(proposal.id)"
            />
          </template>
        </UCard>
        <UEmpty
          v-if="!task.proposals.length"
          icon="i-lucide-messages-square"
          title="Пока нет предложений"
          description="Появятся, когда команды отправят свои идеи."
        />
        <p
          v-if="saved"
          role="status"
          class="text-sm text-success mt-4"
        >
          Решение сохранено в этом браузере.
        </p>
      </section>
      <UCard v-if="task.status === 'published'">
        <template #header>
          <h2 class="font-semibold">
            Предложить свой план
          </h2>
        </template>
        <p class="text-sm text-muted mb-5">
          Команда может отправить идею, план и ссылку на прототип.
        </p>
        <UForm
          :schema="schema"
          :state="formState"
          class="space-y-4"
          @submit="onSubmit"
        >
          <UFormField
            label="Название команды"
            name="team"
            required
          >
            <UInput
              v-model="formState.team"
              class="w-full"
              placeholder="Команда проекта"
            />
          </UFormField>
          <UFormField
            label="Идея"
            name="idea"
            required
          >
            <UTextarea
              v-model="formState.idea"
              :rows="3"
              maxlength="1600"
              class="w-full"
            />
          </UFormField>
          <UFormField
            label="План работы"
            name="plan"
            required
          >
            <UTextarea
              v-model="formState.plan"
              :rows="4"
              maxlength="2400"
              class="w-full"
            />
          </UFormField>
          <UFormField
            label="Ссылка на прототип"
            name="link"
            description="Необязательно"
          >
            <UInput
              v-model="formState.link"
              type="url"
              class="w-full"
              placeholder="https://…"
            />
          </UFormField>
          <UAlert
            v-if="error"
            color="error"
            :title="error"
          />
          <UButton
            type="submit"
            label="Отправить предложение"
            icon="i-lucide-send"
            block
            :loading="pending"
          />
        </UForm>
      </UCard>
    </div>
  </UContainer>
  <UContainer
    v-else
    class="py-24 max-w-xl"
  >
    <UEmpty
      icon="i-lucide-file-question"
      title="Задача не найдена"
      description="Откройте каталог, чтобы выбрать задачу."
    />
    <UButton
      class="mt-5"
      label="К каталогу"
      to="/catalog"
    />
  </UContainer>
</template>
