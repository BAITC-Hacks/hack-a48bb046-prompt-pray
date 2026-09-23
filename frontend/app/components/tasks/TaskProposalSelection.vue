<script setup lang="ts">
import type { Proposal, ProposalStatus, Decision } from '~/types/catalog'

const { t, n } = useAppI18n()

const selected = defineModel<string[]>('selected', { required: true })
const rejected = defineModel<string[]>('rejected', { required: true })
const comment = defineModel<string>('comment', { required: true })
const template = useTemplateMode()
template.prefill(() => {
  if (!comment.value.trim()) comment.value = template.comment
})
const props = defineProps<{ proposals: Proposal[], decision: Decision | null, pending: boolean, error?: string, taskId?: string }>()
const emit = defineEmits<{ decide: [], decideNone: [] }>()
const changed = computed(() => props.proposals.some(item => draftStatus(item.id) !== item.status)
  || comment.value.trim() !== (props.decision?.comment || ''))
function draftStatus(id: string): ProposalStatus {
  return selected.value.includes(id) ? 'selected' : rejected.value.includes(id) ? 'rejected' : 'pending'
}
function setStatus(id: string, status: ProposalStatus) {
  selected.value = [...selected.value.filter(value => value !== id), ...(status === 'selected' ? [id] : [])]
  rejected.value = [...rejected.value.filter(value => value !== id), ...(status === 'rejected' ? [id] : [])]
}
</script>

<template>
  <AppCard
    :title="t('proposal.responses')"
    :description="t('proposal.selectionHint')"
  >
    <UAlert
      :title="t(decision ? 'decisions.saved' : 'decisions.notDecided')"
      :description="decision ? t('decisions.summary', {
        selected: n(proposals.filter(item => item.status === 'selected').length),
        rejected: n(proposals.filter(item => item.status === 'rejected').length),
        pending: n(proposals.filter(item => item.status === 'pending').length)
      }) : t('decisions.manualHint')"
      color="neutral"
    />
    <AppEmptyState
      v-if="!proposals.length"
      :title="t('proposal.empty')"
      :description="t('proposal.emptyDescription')"
      icon="i-lucide-messages-square"
    />
    <TasksTaskProposalCard
      v-for="(item, index) in proposals"
      :key="item.id"
      :proposal="item"
      :task-id="taskId"
      :index="index"
      :pending="pending"
      editable
      :model-value="draftStatus(item.id)"
      @update:model-value="setStatus(item.id, $event)"
    />
    <div
      v-if="proposals.length"
      class="space-y-5 rounded-xl border border-default bg-muted/30 p-5"
    >
      <p
        role="status"
        class="flex items-center gap-2 text-sm font-semibold text-highlighted"
      >
        <UIcon
          name="i-lucide-users-round"
          class="size-5 text-primary"
          aria-hidden="true"
        />
        {{ t('interface.selected', { count: n(selected.length), total: n(proposals.length) }) }}
      </p>
      <p class="text-sm text-muted">
        {{ t(changed ? 'decisions.unsaved' : 'decisions.saveHint') }}
      </p>
      <UFormField
        :label="t('proposal.comment')"
        :error="error"
      >
        <UTextarea
          id="decision-comment"
          v-model="comment"
          :maxlength="10000"
          :rows="3"
          autoresize
          :disabled="pending"
          class="w-full"
        />
      </UFormField>
      <div class="flex flex-wrap gap-3">
        <UButton
          icon="i-lucide-check"
          size="lg"
          :label="t('decisions.save')"
          :loading="pending"
          :disabled="!changed"
          @click="emit('decide')"
        />
        <UButton
          :label="t('proposal.confirmNone')"
          color="neutral"
          variant="outline"
          :disabled="pending"
          @click="emit('decideNone')"
        />
      </div>
      <p class="text-xs text-muted">
        {{ t('decisions.noneHint') }}
      </p>
    </div>
  </AppCard>
</template>
