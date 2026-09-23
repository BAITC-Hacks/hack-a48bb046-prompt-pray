<script setup lang="ts">
import * as z from 'zod'
import type { ApiError, User } from '~/types/api'
import { cardFields } from '~/types/catalog'
import type { Card, CatalogEntry, Proposal, Decision } from '~/types/catalog'

const { t, n } = useAppI18n()

const api = useApi()
const { errorMessage, fieldErrors } = useApiMessages()
const route = useRoute()
const path = `/catalog/tasks/${route.params.id}`
const card = ref<Card | null>(null)
const error = ref<ApiError | null>(null)
const pending = ref(false)
const notice = ref('')
const decisionCount = ref(0)
const noticeMessage = computed(() => notice.value ? t(notice.value, { count: n(decisionCount.value) }, decisionCount.value) : '')
const cardForm = useTemplateRef('cardForm')
useLocalizedForm(() => cardForm.value)
useSeoMeta({ title: () => card.value?.title || t('task.title') })
const form = ref<Record<string, string>>({ title: '' })
const conflict = ref(false)
const localCopy = ref<Record<string, string> | null>(null)
const proposals = ref<Proposal[]>([])
const selected = ref<string[]>([])
const comment = ref('')
const proposal = ref({ team_id: '', idea: '', plan: '', prototype_url: '' })
const owner = computed(() => !!card.value && api.user.value?.id === card.value.business_id)

function fillForm() {
  if (!card.value) return
  form.value.title = card.value.title
  for (const field of cardFields) form.value[field.key] = card.value[field.key] || ''
}
async function action(work: () => Promise<void>) {
  error.value = null
  notice.value = ''
  pending.value = true
  try {
    await work()
  } catch (cause) {
    error.value = cause as ApiError
    if (error.value.code === 'catalog_version_conflict') {
      conflict.value = true
      localCopy.value = { ...form.value }
    }
  } finally {
    pending.value = false
  }
}
async function save() {
  const body: Record<string, unknown> = {}
  if (form.value.title !== card.value?.title) body.title = form.value.title
  for (const field of cardFields) {
    const value = form.value[field.key]?.trim() || null
    if (value !== card.value?.[field.key]) body[field.key] = value
  }
  if (Object.keys(body).length) card.value = await api.request<Card>(path, {
    method: 'PATCH', body: { ...body, expected_version: card.value!.version }
  })
  fillForm()
}
async function reloadLatest() {
  await action(async () => {
    const latest = await api.request<Card>(path)
    localCopy.value = { ...form.value }
    card.value = latest
    fillForm()
    conflict.value = false
    notice.value = 'task.latestLoaded'
  })
}
function restoreLocalText() {
  if (localCopy.value) form.value = { ...localCopy.value }
  notice.value = 'task.textRestored'
}
async function publish() {
  await action(async () => {
    await save()
    card.value = await api.request<Card>(`${path}/confirm`, {
      method: 'POST', body: { confirmed: true, expected_version: card.value!.version }
    })
    const entry = await api.request<CatalogEntry>(`${path}/publish`, {
      method: 'POST', body: { expected_version: card.value.version }
    })
    card.value = entry.task
    notice.value = 'task.published'
  })
}
async function sendProposal() {
  await action(async () => {
    await api.request(`${path}/proposals`, { method: 'POST', body: { ...proposal.value, prototype_url: proposal.value.prototype_url || null } })
    notice.value = 'task.proposalSent'
    proposal.value.idea = ''
    proposal.value.plan = ''
    proposal.value.prototype_url = ''
  })
}
async function decide() {
  await action(async () => {
    await api.request<Decision>(`${path}/decisions`, { method: 'POST', body: { selected_proposal_ids: selected.value, comment: comment.value.trim() || null } })
    decisionCount.value = selected.value.length
    notice.value = decisionCount.value ? 'task.decisionSaved' : 'task.decisionNone'
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
  proposal.value.team_id = api.user.value?.id || ''
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
      :label="t('task.back')"
      variant="link"
    />
    <UAlert
      v-if="error"
      color="error"
      :title="errorMessage(error)"
    />
    <UAlert
      v-if="notice"
      color="success"
      :title="noticeMessage"
    />
    <UAlert
      v-if="conflict"
      color="warning"
      :title="t('task.versionConflict')"
      :description="t('task.versionConflictHint')"
    >
      <template #actions>
        <UButton
          :label="t('task.loadLatest')"
          :loading="pending"
          @click="reloadLatest"
        />
      </template>
    </UAlert>
    <UCard v-if="localCopy">
      <h2 class="font-semibold mb-4">
        {{ t('task.localCopy') }}
      </h2>
      <p class="whitespace-pre-wrap break-words mb-4">
        {{ localCopy.title }}
      </p>
      <dl class="space-y-3">
        <template
          v-for="field in cardFields"
          :key="field.key"
        >
          <dt class="font-medium">
            {{ t(`fields.${field.key}`) }}
          </dt>
          <dd class="whitespace-pre-wrap break-words">
            {{ localCopy[field.key] || t('task.notSpecified') }}
          </dd>
        </template>
      </dl>
      <UButton
        v-if="!conflict"
        class="mt-4"
        :label="t('task.restoreText')"
        :disabled="pending"
        @click="restoreLocalText"
      />
    </UCard>
    <template v-if="card">
      <UPageHeader :title="card.title" />
      <TasksTaskWorkflow
        v-if="owner && !card.confirmed_at"
        :step="3"
      />
      <TasksTaskRating :rating="card.rating" />
      <UForm
        v-if="owner"
        ref="cardForm"
        :state="form"
        :schema="z.object({ title: z.string({ error: t('validation.required') }).trim().min(1, t('validation.title')).max(200, t('validation.max', { max: 200 })) })"
        class="space-y-4"
        @submit="action(async () => { await save(); notice = 'task.cardSaved' })"
      >
        <TasksTaskCardFields
          v-model="form"
          :errors="fieldErrors(error)"
        />
        <div class="flex flex-wrap gap-3">
          <UButton
            type="submit"
            :label="t('task.saveRating')"
            :loading="pending"
            :disabled="conflict"
          />
          <UButton
            :label="t('task.publish')"
            variant="outline"
            :disabled="pending || conflict || !form.title?.trim()"
            @click="publish"
          />
        </div>
        <p class="text-muted">
          {{ t('task.consent') }}
        </p>
      </UForm>
      <TasksTaskDetails
        v-else
        :card="card"
      />
      <TasksTaskProposalForm
        v-if="api.user.value?.role === 'student'"
        v-model="proposal"
        :team-name="api.user.value?.username"
        :pending="pending"
        :errors="fieldErrors(error)"
        @submit="sendProposal"
      />
      <UButton
        v-if="!api.user.value"
        :to="{ path: '/login', query: { redirect: route.fullPath } }"
        :label="t('task.loginProposal')"
      />
      <TasksTaskProposalSelection
        v-if="owner"
        v-model:selected="selected"
        v-model:comment="comment"
        :proposals="proposals"
        :pending="pending"
        :error="fieldErrors(error).comment"
        @decide="decide"
      />
    </template>
  </UContainer>
</template>
