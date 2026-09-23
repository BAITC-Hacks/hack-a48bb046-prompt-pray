<script setup lang="ts">
import type { Proposal, ProposalStatus } from '~/types/catalog'

defineProps<{ proposal: Proposal, index: number, pending?: boolean, taskId?: string, editable?: boolean }>()
const status = defineModel<ProposalStatus>({ default: 'pending' })
const { t, n } = useAppI18n()
</script>

<template>
  <AppCard
    :data-proposal-id="proposal.id"
    :title="t('proposal.teamNumber', { number: n(index + 1) })"
    :class="editable && status === 'selected' ? 'ring-2 ring-primary' : 'bg-muted/20'"
  >
    <UBadge
      :color="proposal.status === 'selected' ? 'success' : proposal.status === 'rejected' ? 'error' : 'neutral'"
      variant="subtle"
    >
      {{ t(`decisions.${proposal.status}`) }}
    </UBadge>
    <template v-if="editable">
      <div class="flex flex-wrap gap-2">
        <UButton
          :label="t('decisions.select')"
          icon="i-lucide-check"
          :variant="status === 'selected' ? 'solid' : 'outline'"
          :aria-pressed="status === 'selected'"
          :disabled="pending"
          @click="status = 'selected'"
        />
        <UButton
          :label="t('decisions.reject')"
          icon="i-lucide-x"
          color="error"
          :variant="status === 'rejected' ? 'solid' : 'outline'"
          :aria-pressed="status === 'rejected'"
          :disabled="pending"
          @click="status = 'rejected'"
        />
        <UButton
          v-if="status !== 'pending'"
          :label="t('decisions.defer')"
          color="neutral"
          variant="ghost"
          :disabled="pending"
          @click="status = 'pending'"
        />
      </div>
      <p
        v-if="status !== proposal.status"
        class="text-sm text-muted"
      >
        {{ t('decisions.preview', { status: t(`decisions.${status}`) }) }}
      </p>
    </template>
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
