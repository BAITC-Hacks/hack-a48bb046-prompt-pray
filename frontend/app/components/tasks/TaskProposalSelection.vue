<script setup lang="ts">
import type { Proposal } from '~/types/catalog'

const selected = defineModel<string[]>('selected', { required: true })
const comment = defineModel<string>('comment', { required: true })
defineProps<{ proposals: Proposal[], pending: boolean, error?: string }>()
const emit = defineEmits<{ decide: [] }>()
</script>

<template>
  <UPageCard
    title="Отклики команд"
    description="Выберите одну, несколько или ни одной команды. Решение принимаете только вы."
  >
    <AppEmptyState
      v-if="!proposals.length"
      title="Пока нет откликов"
      description="Команды смогут предложить решение после публикации задачи в каталоге."
      icon="i-lucide-messages-square"
    />
    <UPageCard
      v-for="(item, index) in proposals"
      :key="item.id"
      :title="`Отклик команды №${index + 1}`"
    >
      <UCheckbox
        :model-value="selected.includes(item.id)"
        label="Выбрать эту команду"
        @update:model-value="value => selected = value ? [...selected, item.id] : selected.filter(id => id !== item.id)"
      />
      <p><strong>Идея:</strong> {{ item.idea }}</p>
      <p><strong>План:</strong> {{ item.plan }}</p>
      <ULink
        v-if="item.prototype_url"
        :to="item.prototype_url"
        target="_blank"
        rel="noopener noreferrer"
      >Открыть прототип</ULink>
    </UPageCard>
    <UFormField
      label="Комментарий к решению"
      :error="error"
    >
      <UTextarea
        v-model="comment"
        :maxlength="10000"
        class="w-full"
      />
    </UFormField>
    <UButton
      :label="selected.length ? `Подтвердить выбор (${selected.length})` : 'Подтвердить: никого не выбирать'"
      :loading="pending"
      @click="emit('decide')"
    />
  </UPageCard>
</template>
