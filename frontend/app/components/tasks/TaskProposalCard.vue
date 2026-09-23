<script setup lang="ts">
import type { Proposal } from '~/types/catalog'

defineProps<{ proposal: Proposal, index: number, pending: boolean, taskId?: string }>()
const selected = defineModel<boolean>({ required: true })
const { t, n } = useAppI18n()
</script>

<template>
  <AppCard
    :title="t('proposal.teamNumber', { number: n(index + 1) })"
    :class="selected ? 'ring-2 ring-primary' : 'bg-muted/20'"
  >
    <UCheckbox
      v-model="selected"
      :disabled="pending"
      :label="t('proposal.select')"
    />
    <p class="whitespace-pre-line break-words text-sm leading-7">
      <strong>{{ t('proposal.idea') }}:</strong> {{ proposal.idea }}
    </p>
    <p class="whitespace-pre-line break-words text-sm leading-7">
      <strong>{{ t('proposal.plan') }}:</strong> {{ proposal.plan }}
    </p>
    <TasksTaskAiAdvice
      v-if="taskId"
      :endpoint="`/catalog/tasks/${taskId}/proposals/${proposal.id}/analysis`"
      :label="t('ai.proposal')"
    />
    <template
      v-if="proposal.prototype_url"
      #footer
    >
      <ULink
        :to="proposal.prototype_url"
        target="_blank"
        rel="noopener noreferrer"
      >{{ t('proposal.openPrototype') }}</ULink>
    </template>
  </AppCard>
</template>
