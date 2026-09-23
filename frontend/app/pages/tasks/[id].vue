<script setup lang="ts">
import * as z from 'zod'
import type { ApiError, User } from '~/types/api'
import { cardFields } from '~/types/catalog'
import type { Card, Proposal, Decision } from '~/types/catalog'

const api = useApi()
const route = useRoute()
const path = `/catalog/tasks/${route.params.id}`
const card = ref<Card | null>(null)
const error = ref<ApiError | null>(null)
const pending = ref(false)
const notice = ref('')
const form = reactive<Record<string, string>>({ title: '' })
const proposals = ref<Proposal[]>([])
const selected = ref<string[]>([])
const comment = ref('')
const proposal = reactive({ team_id: '', idea: '', plan: '', prototype_url: '' })
const owner = computed(() => !!card.value && api.user.value?.id === card.value.business_id)
const proposalSchema = z.object({ team_id: z.uuid('Введите UUID команды'), idea: z.string().trim().min(1, 'Опишите идею').max(10000), plan: z.string().trim().min(1, 'Опишите план').max(10000), prototype_url: z.union([z.url().refine(value => /^https?:\/\//.test(value), 'Нужна HTTP(S) ссылка'), z.literal('')]) })

function fillForm() {
  if (!card.value) return
  form.title = card.value.title
  for (const field of cardFields) form[field.key] = card.value[field.key] || ''
}
async function action(work: () => Promise<void>) {
  error.value = null
  notice.value = ''
  pending.value = true
  try {
    await work()
  } catch (cause) {
    error.value = cause as ApiError
  } finally {
    pending.value = false
  }
}
async function save() {
  const body: Record<string, unknown> = {}
  if (form.title !== card.value?.title) body.title = form.title
  for (const field of cardFields) {
    const value = form[field.key]?.trim() || null
    if (value !== card.value?.[field.key]) body[field.key] = value
  }
  card.value = await api.request<Card>(path, { method: 'PATCH', body })
  fillForm()
}
async function publish() {
  await action(async () => {
    await save()
    card.value = await api.request<Card>(`${path}/confirm`, { method: 'POST', body: { confirmed: true } })
    await api.request(`${path}/publish`, { method: 'POST' })
    notice.value = 'Карточка подтверждена и опубликована в каталоге'
  })
}
async function sendProposal() {
  await action(async () => {
    await api.request(`${path}/proposals`, { method: 'POST', body: { ...proposal, prototype_url: proposal.prototype_url || null } })
    notice.value = 'Отклик отправлен. Решение принимает бизнес.'
    proposal.idea = ''
    proposal.plan = ''
    proposal.prototype_url = ''
  })
}
async function decide() {
  await action(async () => {
    await api.request<Decision>(`${path}/decisions`, { method: 'POST', body: { selected_proposal_ids: selected.value, comment: comment.value.trim() || null } })
    notice.value = selected.value.length ? `Решение сохранено: выбрано команд — ${selected.value.length}` : 'Решение сохранено: не выбрана ни одна команда'
  })
}
await action(async () => {
  if (!api.user.value) {
    try {
      api.user.value = await api.request<User>('/users/me')
    } catch {
      // Public task remains available to guests.
    }
  }
  card.value = await api.request<Card>(path)
  proposal.team_id = api.user.value?.id || ''
  fillForm()
  if (owner.value) {
    proposals.value = await api.request<Proposal[]>(`${path}/proposals`)
    const decisions = await api.request<Decision[]>(`${path}/decisions`)
    const last = decisions[0]
    if (last) {
      selected.value = last.selected_proposal_ids
      comment.value = last.comment || ''
    }
  }
})
</script>

<template>
  <UContainer class="max-w-4xl py-12 space-y-6">
    <UButton
      to="/catalog"
      label="В каталог"
      variant="link"
    />
    <UAlert
      v-if="error"
      color="error"
      :title="error.detail"
      :description="error.code"
    />
    <UAlert
      v-if="notice"
      color="success"
      :title="notice"
    />
    <template v-if="card">
      <UPageHeader :title="card.title" />
      <UPageCard
        :title="`${card.rating?.total ?? 0} / 100 · ${card.rating?.readiness || 'черновик'}`"
        description="Рейтинг показывает полноту описания и влияет на порядок в каталоге."
      >
        <UProgress
          :model-value="card.rating?.total ?? 0"
          :max="100"
        />
        <div
          v-for="field in cardFields"
          :key="field.key"
          class="flex justify-between gap-4"
        >
          <span>{{ field.label }}</span><span>{{ card.rating?.[field.key] ?? 0 }} / {{ field.points }}</span>
        </div>
      </UPageCard>
      <UForm
        v-if="owner"
        :state="form"
        :schema="z.object({ title: z.string().trim().min(1, 'Введите название').max(200) })"
        class="space-y-4"
        @submit="action(async () => { await save(); notice = 'Карточка сохранена, рейтинг пересчитан' })"
      >
        <UFormField
          name="title"
          label="Название"
          :error="error?.fields.title"
        >
          <UInput
            v-model="form.title"
            class="w-full"
          />
        </UFormField>
        <UFormField
          v-for="field in cardFields"
          :key="field.key"
          :name="field.key"
          :label="field.label"
          :error="error?.fields[field.key]"
        >
          <UTextarea
            v-model="form[field.key]"
            :maxlength="10000"
            class="w-full"
            :rows="3"
          />
        </UFormField>
        <div class="flex gap-3">
          <UButton
            type="submit"
            label="Сохранить и пересчитать рейтинг"
            :loading="pending"
          />
          <UButton
            label="Подтверждаю — опубликовать"
            variant="outline"
            :disabled="pending || !form.title?.trim()"
            @click="publish"
          />
        </div>
        <p class="text-muted">
          Подтверждая, вы разрешаете публикацию описания, материалов и контактов в открытом каталоге.
        </p>
      </UForm>
      <template v-else>
        <UPageCard
          v-for="field in cardFields"
          :key="field.key"
          :title="field.label"
          :description="card[field.key] || 'Пока не указано'"
        />
      </template>
      <UPageCard
        v-if="api.user.value?.role === 'student'"
        title="Предложить решение"
      >
        <UForm
          :schema="proposalSchema"
          :state="proposal"
          class="space-y-4"
          @submit="sendProposal"
        >
          <p>Отклик от команды: {{ api.user.value?.username }}</p>
          <UFormField
            name="idea"
            label="Идея"
            :error="error?.fields.idea"
          >
            <UTextarea
              v-model="proposal.idea"
              class="w-full"
            />
          </UFormField>
          <UFormField
            name="plan"
            label="План реализации"
            :error="error?.fields.plan"
          >
            <UTextarea
              v-model="proposal.plan"
              class="w-full"
            />
          </UFormField>
          <UFormField
            name="prototype_url"
            label="Ссылка на прототип (необязательно)"
            :error="error?.fields.prototype_url"
          >
            <UInput
              v-model="proposal.prototype_url"
              class="w-full"
            />
          </UFormField>
          <UButton
            type="submit"
            label="Отправить отклик"
            :loading="pending"
          />
        </UForm>
      </UPageCard>
      <UButton
        v-if="!api.user.value"
        :to="{ path: '/login', query: { redirect: route.fullPath } }"
        label="Войти, чтобы откликнуться"
      />
      <UPageCard
        v-if="owner"
        title="Отклики команд"
        description="Выберите одну, несколько или ни одной команды. Решение принимаете только вы."
      >
        <p v-if="!proposals.length">
          Откликов пока нет.
        </p>
        <UPageCard
          v-for="item in proposals"
          :key="item.id"
          :title="`Отклик команды №${proposals.indexOf(item) + 1}`"
        >
          <UCheckbox
            :model-value="selected.includes(item.id)"
            label="Выбрать эту команду"
            @update:model-value="value => selected = value ? [...selected, item.id] : selected.filter(id => id !== item.id)"
          />
          <p><strong>Идея:</strong> {{ item.idea }}</p>
          <p><strong>План:</strong> {{ item.plan }}</p>
          <ULink
            v-if="item.prototype_url"
            :to="item.prototype_url"
            target="_blank"
            rel="noopener noreferrer"
          >Открыть прототип</ULink>
        </UPageCard>
        <UFormField
          label="Комментарий к решению"
          :error="error?.fields.comment"
        >
          <UTextarea
            v-model="comment"
            :maxlength="10000"
            class="w-full"
          />
        </UFormField>
        <UButton
          :label="selected.length ? `Подтвердить выбор (${selected.length})` : 'Подтвердить: никого не выбирать'"
          :loading="pending"
          @click="decide"
        />
      </UPageCard>
    </template>
  </UContainer>
</template>
