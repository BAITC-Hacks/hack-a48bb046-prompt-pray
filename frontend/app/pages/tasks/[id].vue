<script setup lang="ts">
import * as z from 'zod'
import type { ApiError, User } from '~/types/api'
import { cardFields } from '~/types/catalog'
import type { Card, CatalogEntry, Proposal, Decision } from '~/types/catalog'

const { t, n } = useAppI18n()

const api = useApi()
const rewards = useRewardFeedback()
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
const rejected = ref<string[]>([])
const decision = ref<Decision | null>(null)
const comment = ref('')
const proposal = ref({ team_id: '', idea: '', plan: '', prototype_url: '' })
const owner = computed(() => !!card.value && api.user.value?.id === card.value.business_id)
const filledCount = computed(() => cardFields.filter(field => form.value[field.key]?.trim()).length)
const hasChanges = computed(() => !!card.value && (
  form.value.title !== card.value.title
  || cardFields.some(field => (form.value[field.key]?.trim() || null) !== card.value?.[field.key])
))

function fillForm() {
  if (!card.value) return
  form.value.title = card.value.title
  form.value.topic = card.value.topic || 'unspecified'
  for (const field of cardFields) form.value[field.key] = card.value[field.key] || ''
}
async function action(work: () => Promise<void>) {
  if (pending.value) return
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
  const topic = form.value.topic === 'unspecified' ? null : form.value.topic
  if (topic !== (card.value?.topic ?? null)) body.topic = topic
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
  await action(() => rewards.track(async () => {
    await save()
    card.value = await api.request<Card>(`${path}/confirm`, {
      method: 'POST', body: { confirmed: true, expected_version: card.value!.version }
    })
    const entry = await api.request<CatalogEntry>(`${path}/publish`, {
      method: 'POST', body: { expected_version: card.value.version }
    })
    card.value = entry.task
    notice.value = 'task.published'
  }))
}
async function sendProposal() {
  await action(() => rewards.track(async () => {
    const submitted = await api.request<Proposal>(`${path}/proposals`, { method: 'POST', body: { ...proposal.value, prototype_url: proposal.value.prototype_url || null } })
    proposals.value.push(submitted)
    notice.value = 'task.proposalSent'
    proposal.value.idea = ''
    proposal.value.plan = ''
    proposal.value.prototype_url = ''
  }))
}
async function decide(nobody = false) {
  await action(() => rewards.track(async () => {
    const saved = await api.request<Decision>(`${path}/decisions`, { method: 'POST', body: {
      selected_proposal_ids: nobody ? [] : selected.value,
      rejected_proposal_ids: nobody ? proposals.value.map(item => item.id) : rejected.value,
      comment: comment.value.trim() || null
    } })
    decision.value = saved
    selected.value = saved.selected_proposal_ids
    rejected.value = saved.rejected_proposal_ids
    comment.value = saved.comment || ''
    proposals.value = proposals.value.map(item => ({ ...item, status: selected.value.includes(item.id)
      ? 'selected'
      : rejected.value.includes(item.id) ? 'rejected' : 'pending' }))
    decisionCount.value = selected.value.length
    notice.value = decisionCount.value ? 'task.decisionSaved' : nobody ? 'task.decisionNone' : 'decisions.saved'
  }))
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
  if (owner.value || api.user.value?.role === 'student') {
    proposals.value = await api.request<Proposal[]>(`${path}/proposals`)
  }
  if (owner.value) {
    const decisions = await api.request<Decision[]>(`${path}/decisions`)
    const last = decisions[0]
    if (last) {
      decision.value = last
      selected.value = last.selected_proposal_ids
      rejected.value = last.rejected_proposal_ids
      comment.value = last.comment || ''
    }
  }
})
</script>

<template>
  <UContainer
    data-app-page
    class="space-y-8"
  >
    <UButton
      to="/catalog"
      :label="t('task.back')"
      icon="i-lucide-arrow-left"
      color="neutral"
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
      <AppPageHeading
        :title="owner && !card.confirmed_at ? t('workflow.publish') : card.title"
        :eyebrow="owner ? t('review.eyebrow') : t('task.title')"
        icon="i-lucide-file-text"
      >
        <TasksTaskRating
          :rating="card.rating"
          compact
        />
      </AppPageHeading>
      <UBadge
        color="neutral"
        variant="subtle"
      >
        {{ t(`topics.${card.topic || 'unspecified'}`) }}
      </UBadge>
      <UAlert
        v-if="!owner && (card.rating?.total ?? 0) < 40"
        color="info"
        icon="i-lucide-message-circle"
        :title="t('catalogFilters.lowRatingOpen')"
        :description="t('catalogFilters.lowRatingHint')"
      />
      <div
        v-if="owner && !card.confirmed_at"
        class="rounded-2xl border border-default bg-default p-5 sm:p-6"
      >
        <TasksTaskWorkflow :step="3" />
      </div>
      <p
        v-if="owner"
        class="max-w-3xl text-sm leading-7 text-muted"
      >
        {{ t('review.intro') }}
      </p>
      <div class="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <aside class="space-y-4 lg:sticky lg:top-24 lg:col-start-2 lg:row-start-1">
          <TasksTaskRating :rating="card.rating" />
          <p
            v-if="owner && hasChanges"
            class="flex items-start gap-2 px-1 text-xs leading-5 text-muted"
            role="status"
          >
            <UIcon
              name="i-lucide-refresh-cw"
              class="mt-0.5 size-4 shrink-0"
            />
            {{ t('review.ratingHint') }}
          </p>
          <nav
            :aria-label="t('task.title')"
            class="hidden rounded-2xl border border-default bg-default p-3 lg:block"
          >
            <a
              v-for="field in cardFields"
              :key="field.key"
              :href="`#task-${field.key}`"
              class="flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-sm text-muted transition-colors hover:bg-muted hover:text-highlighted focus-visible:outline-2 focus-visible:outline-primary"
            >
              {{ t(`fields.${field.key}`) }}
              <UIcon
                :name="owner ? form[field.key]?.trim() ? 'i-lucide-circle-check' : 'i-lucide-circle-dashed' : 'i-lucide-chevron-right'"
                class="size-3.5 shrink-0"
                :class="owner && form[field.key]?.trim() ? 'text-primary' : ''"
                aria-hidden="true"
              />
            </a>
          </nav>
          <TasksTaskAiAdvice
            v-if="owner"
            :key="card.version"
            :endpoint="`${path}/rating-advice`"
            :label="t('ai.rating')"
          />
          <p class="px-1 text-xs leading-6 text-muted">
            {{ t('catalog.ratingHint') }}
          </p>
        </aside>
        <div class="min-w-0 space-y-8 lg:col-start-1 lg:row-start-1">
          <UForm
            v-if="owner"
            ref="cardForm"
            :state="form"
            :schema="z.object({ title: z.string({ error: t('validation.required') }).trim().min(1, t('validation.title')).max(200, t('validation.max', { max: 200 })) })"
            class="overflow-hidden rounded-2xl border border-default bg-default"
            @submit="action(async () => { await save(); notice = 'task.cardSaved' })"
          >
            <div class="space-y-5 border-b border-default p-6 sm:px-8">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div class="flex items-center gap-3">
                  <span class="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <UIcon
                      name="i-lucide-file-check-2"
                      class="size-5"
                    />
                  </span>
                  <div>
                    <h2 class="font-semibold text-highlighted">
                      {{ t('review.cardTitle') }}
                    </h2>
                    <p class="mt-1 text-xs text-muted">
                      {{ t('review.filled', { count: filledCount, total: cardFields.length }) }}
                    </p>
                  </div>
                </div>
                <UBadge
                  :icon="hasChanges ? 'i-lucide-pencil' : 'i-lucide-cloud-check'"
                  color="neutral"
                  variant="soft"
                  role="status"
                >
                  {{ hasChanges ? t('review.unsaved') : t('task.saved') }}
                </UBadge>
              </div>
            </div>
            <div class="p-6 sm:p-8">
              <fieldset
                :disabled="pending"
                class="space-y-7"
              >
                <TasksTaskCardFields
                  v-model="form"
                  :errors="fieldErrors(error)"
                />
              </fieldset>
            </div>
            <div class="space-y-4 border-t border-default bg-muted/35 p-6 sm:p-8">
              <div class="flex items-start gap-3">
                <UIcon
                  name="i-lucide-globe"
                  class="mt-1 size-5 shrink-0 text-primary"
                />
                <div>
                  <h3 class="font-semibold text-highlighted">
                    {{ t('review.publishTitle') }}
                  </h3>
                  <p class="mt-1 text-sm leading-6 text-muted">
                    {{ t('review.publishHint') }}
                  </p>
                </div>
              </div>
              <div class="flex flex-wrap gap-3">
                <UButton
                  type="submit"
                  :label="t('task.saveRating')"
                  icon="i-lucide-save"
                  size="lg"
                  color="neutral"
                  variant="outline"
                  :loading="pending"
                  :disabled="conflict"
                />
                <UButton
                  :label="t('task.publish')"
                  icon="i-lucide-send"
                  size="lg"
                  :loading="pending"
                  :disabled="pending || conflict || !form.title?.trim() || form.title.trim().length > 200"
                  @click="publish"
                />
              </div>
              <p class="text-xs leading-6 text-muted">
                {{ t('task.consent') }}
              </p>
            </div>
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
          <AppCard
            v-if="api.user.value?.role === 'student' && proposals.length"
            :title="t('decisions.myProposals')"
          >
            <p class="text-sm text-muted">
              {{ t('decisions.studentHint') }}
            </p>
            <TasksTaskProposalCard
              v-for="(item, index) in proposals"
              :key="item.id"
              :proposal="item"
              :index="index"
            />
          </AppCard>
          <TasksTaskProposalSelection
            v-if="owner"
            v-model:selected="selected"
            v-model:rejected="rejected"
            v-model:comment="comment"
            :proposals="proposals"
            :decision="decision"
            :task-id="card.id"
            :pending="pending"
            :error="fieldErrors(error).comment"
            @decide="decide()"
            @decide-none="decide(true)"
          />
        </div>
      </div>
    </template>
  </UContainer>
</template>
