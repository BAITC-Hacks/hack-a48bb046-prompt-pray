<script setup lang="ts">
import * as z from 'zod'

const proposal = defineModel<{ team_id: string, idea: string, plan: string, prototype_url: string }>({ required: true })
defineProps<{ teamName?: string, pending: boolean, errors?: Record<string, string> }>()
const emit = defineEmits<{ submit: [] }>()
const proposalSchema = z.object({ team_id: z.uuid('Введите UUID команды'), idea: z.string().trim().min(1, 'Опишите идею').max(10000), plan: z.string().trim().min(1, 'Опишите план').max(10000), prototype_url: z.union([z.url().refine(value => /^https?:\/\//.test(value), 'Нужна HTTP(S) ссылка'), z.literal('')]) })
</script>

<template>
  <UPageCard
    title="Предложить решение"
  >
    <UForm
      :schema="proposalSchema"
      :state="proposal"
      class="space-y-4"
      @submit="emit('submit')"
    >
      <p>Отклик от команды: {{ teamName }}</p>
      <UFormField
        name="idea"
        label="Идея"
        :error="errors?.idea"
      >
        <UTextarea
          v-model="proposal.idea"
          class="w-full"
        />
      </UFormField>
      <UFormField
        name="plan"
        label="План реализации"
        :error="errors?.plan"
      >
        <UTextarea
          v-model="proposal.plan"
          class="w-full"
        />
      </UFormField>
      <UFormField
        name="prototype_url"
        label="Ссылка на прототип (необязательно)"
        :error="errors?.prototype_url"
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
</template>
