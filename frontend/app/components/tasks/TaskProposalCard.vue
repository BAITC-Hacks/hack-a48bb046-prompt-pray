<script setup lang="ts">
import type { Proposal } from '~/types/catalog'

defineProps<{ proposal: Proposal, index: number, pending: boolean }>()
const selected = defineModel<boolean>({ required: true })
const { t, n } = useAppI18n()
</script>

<template>
  <AppCard :title="t('proposal.teamNumber', { number: n(index + 1) })">
    <UCheckbox
      v-model="selected"
      :disabled="pending"
      :label="t('proposal.select')"
    />
    <p class="whitespace-pre-line break-words">
      <strong>{{ t('proposal.idea') }}:</strong> {{ proposal.idea }}
    </p>
    <p class="whitespace-pre-line break-words">
      <strong>{{ t('proposal.plan') }}:</strong> {{ proposal.plan }}
    </p>
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
