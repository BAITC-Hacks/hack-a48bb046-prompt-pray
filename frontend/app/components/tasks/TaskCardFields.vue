<script setup lang="ts">
import { cardFields } from '~/types/catalog'

const { t } = useAppI18n()

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
      v-model="model.title"
      class="w-full"
    />
  </UFormField>
  <UFormField
    v-for="field in cardFields"
    :key="field.key"
    :name="field.key"
    :label="t(`fields.${field.key}`)"
    :error="errors?.[field.key]"
  >
    <UTextarea
      v-model="model[field.key]"
      :maxlength="102007"
      class="w-full"
      :rows="3"
    />
  </UFormField>
</template>
