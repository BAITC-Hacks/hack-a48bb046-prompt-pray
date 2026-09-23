<script setup lang="ts">
import { cardFields, taskTopics } from '~/types/catalog'

const { t } = useAppI18n()
const topicOptions = computed(() => ['unspecified', ...taskTopics].map(value => ({ value, label: t(`topics.${value}`) })))

const model = defineModel<Record<string, string>>({ required: true })
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
      size="lg"
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
    class="scroll-mt-24"
    :name="field.key"
    :label="t(`fields.${field.key}`)"
    :error="errors?.[field.key]"
  >
    <UTextarea
      :id="`card-${field.key}`"
      v-model="model[field.key]"
      autoresize
      size="lg"
      :maxlength="102007"
      class="w-full"
      :rows="3"
    />
  </UFormField>
</template>
