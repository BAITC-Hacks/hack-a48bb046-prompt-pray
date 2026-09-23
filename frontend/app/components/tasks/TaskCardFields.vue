<script setup lang="ts">
import { cardFields, taskTopics } from '~/types/catalog'

const { t } = useAppI18n()
const topicOptions = computed(() => ['unspecified', ...taskTopics].map(value => ({ value, label: t(`topics.${value}`) })))

const model = defineModel<Record<string, string>>({ required: true })
const template = useTemplateMode()
template.prefill(() => {
  for (const [key, value] of Object.entries(template.card)) {
    if (!model.value[key]?.trim()) model.value[key] = value
  }
})
defineProps<{ errors?: Record<string, string> }>()
</script>

<template>
  <UFormField
    name="title"
    :label="t('fields.title')"
    :error="errors?.title"
  >
    <UInput
      id="card-title"
      v-model="model.title"
      size="xl"
      :maxlength="200"
      :ui="{ base: 'rounded-xl font-semibold text-lg' }"
      class="w-full"
    />
  </UFormField>
  <UFormField
    name="topic"
    :label="t('catalogFilters.topic')"
    :error="errors?.topic"
    :description="t('catalogFilters.topicHint')"
  >
    <USelect
      v-model="model.topic"
      :items="topicOptions"
      size="lg"
      class="w-full"
    />
  </UFormField>
  <UFormField
    v-for="field in cardFields"
    :id="`task-${field.key}`"
    :key="field.key"
    class="scroll-mt-24 border-t border-default pt-6"
    :name="field.key"
    :label="t(`fields.${field.key}`)"
    :error="errors?.[field.key]"
  >
    <template #label>
      <span class="inline-flex items-center gap-2">
        <UIcon
          :name="model[field.key]?.trim() ? 'i-lucide-circle-check' : 'i-lucide-circle-dashed'"
          class="size-4 shrink-0"
          :class="model[field.key]?.trim() ? 'text-primary' : 'text-muted'"
          aria-hidden="true"
        />
        {{ t(`fields.${field.key}`) }}
      </span>
    </template>
    <UTextarea
      :id="`card-${field.key}`"
      v-model="model[field.key]"
      autoresize
      size="lg"
      :placeholder="t('task.notSpecified')"
      :ui="{ base: 'rounded-xl p-4 leading-7' }"
      :maxlength="102007"
      class="w-full"
      :rows="3"
    />
  </UFormField>
</template>
