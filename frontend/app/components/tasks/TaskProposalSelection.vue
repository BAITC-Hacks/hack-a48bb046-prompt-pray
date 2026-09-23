<script setup lang="ts">
import type { Proposal } from '~/types/catalog'

const { t, n } = useAppI18n()

const selected = defineModel<string[]>('selected', { required: true })
const comment = defineModel<string>('comment', { required: true })
const template = useTemplateMode()
template.prefill(() => {
  if (!comment.value.trim()) comment.value = template.comment
})
defineProps<{ proposals: Proposal[], pending: boolean, error?: string, taskId?: string }>()
const emit = defineEmits<{ decide: [] }>()
</script>

<template>
  <AppCard
    :title="t('proposal.responses')"
    :description="t('proposal.selectionHint')"
  >
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
      :model-value="selected.includes(item.id)"
      @update:model-value="value => selected = value ? [...selected, item.id] : selected.filter(id => id !== item.id)"
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
      <UButton
        icon="i-lucide-check"
        size="lg"
        :label="selected.length ? t('proposal.confirm', { count: n(selected.length) }) : t('proposal.confirmNone')"
        :loading="pending"
        @click="emit('decide')"
      />
    </div>
  </AppCard>
</template>
