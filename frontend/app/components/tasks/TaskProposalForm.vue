<script setup lang="ts">
import * as z from 'zod'

const { t } = useAppI18n()

const proposal = defineModel<{ team_id: string, idea: string, plan: string, prototype_url: string }>({ required: true })
const template = useTemplateMode()
template.prefill(() => {
  for (const key of ['idea', 'plan', 'prototype_url'] as const) {
    if (!proposal.value[key].trim()) proposal.value[key] = template.proposal[key]
  }
})
defineProps<{ teamName?: string, pending: boolean, errors?: Record<string, string> }>()
const emit = defineEmits<{ submit: [] }>()
const proposalSchema = computed(() => z.object({
  team_id: z.uuid(t('validation.team')),
  idea: z.string({ error: t('validation.required') }).trim().min(1, t('validation.idea')).max(10000, t('validation.max', { max: 10000 })),
  plan: z.string({ error: t('validation.required') }).trim().min(1, t('validation.plan')).max(10000, t('validation.max', { max: 10000 })),
  prototype_url: z.string({ error: t('validation.required') }).refine(value => !value || (/^https?:\/\//.test(value) && z.url().safeParse(value).success), t('validation.url'))
}))
const proposalForm = useTemplateRef('proposalForm')
useLocalizedForm(() => proposalForm.value)
</script>

<template>
  <AppCard
    :title="t('proposal.title')"
  >
    <UForm
      ref="proposalForm"
      :schema="proposalSchema"
      :state="proposal"
      class="space-y-6"
      @submit="emit('submit')"
    >
      <p class="rounded-xl bg-muted/50 px-4 py-3 text-sm font-medium text-muted">
        {{ t('proposal.team', { name: teamName || '' }) }}
      </p>
      <UFormField
        name="idea"
        :label="t('proposal.idea')"
        :error="errors?.idea"
      >
        <UTextarea
          id="proposal-idea"
          v-model="proposal.idea"
          :rows="4"
          autoresize
          size="lg"
          class="w-full"
        />
      </UFormField>
      <UFormField
        name="plan"
        :label="t('proposal.plan')"
        :error="errors?.plan"
      >
        <UTextarea
          id="proposal-plan"
          v-model="proposal.plan"
          :rows="4"
          autoresize
          size="lg"
          class="w-full"
        />
      </UFormField>
      <UFormField
        name="prototype_url"
        :label="t('proposal.prototype')"
        :error="errors?.prototype_url"
      >
        <UInput
          id="proposal-prototype"
          v-model="proposal.prototype_url"
          icon="i-lucide-link"
          placeholder="https://"
          size="lg"
          class="w-full"
        />
      </UFormField>
      <UButton
        type="submit"
        icon="i-lucide-send"
        size="lg"
        :label="t('proposal.send')"
        :loading="pending"
      />
    </UForm>
  </AppCard>
</template>
