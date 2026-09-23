<script setup lang="ts">
import type { Proposal } from '~/types/catalog'

const { t, n } = useAppI18n()

const selected = defineModel<string[]>('selected', { required: true })
const comment = defineModel<string>('comment', { required: true })
defineProps<{ proposals: Proposal[], pending: boolean, error?: string }>()
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
      :index="index"
      :pending="pending"
      :model-value="selected.includes(item.id)"
      @update:model-value="value => selected = value ? [...selected, item.id] : selected.filter(id => id !== item.id)"
    />
    <UFormField
      :label="t('proposal.comment')"
      :error="error"
    >
      <UTextarea
        id="decision-comment"
        v-model="comment"
        :maxlength="10000"
        class="w-full"
      />
    </UFormField>
    <UButton
      :label="selected.length ? t('proposal.confirm', { count: n(selected.length) }) : t('proposal.confirmNone')"
      :loading="pending"
      @click="emit('decide')"
    />
  </AppCard>
</template>
