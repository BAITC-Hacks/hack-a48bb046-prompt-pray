<script setup lang="ts">
import type { ApiError } from '~/types/api'
import type { Draft } from '~/types/catalog'

definePageMeta({ middleware: 'auth' })
const api = useApi()
const drafts = ref<Draft[]>([])
const error = ref<ApiError | null>(null)
const pending = ref(false)
async function loadDrafts() {
  pending.value = true
  error.value = null
  try {
    drafts.value = await api.request<Draft[]>('/catalog/drafts')
  } catch (cause) {
    error.value = cause as ApiError
  } finally {
    pending.value = false
  }
}
if (api.user.value?.role === 'business') await loadDrafts()
async function logout() {
  try {
    await api.request('/auth/logout', { method: 'POST' })
    await navigateTo('/login')
  } catch (cause) {
    error.value = cause as ApiError
  }
}
</script>

<template>
  <UContainer class="py-12 space-y-6">
    <UAlert
      v-if="error"
      color="error"
      :title="error.detail"
    />
    <UPageCard
      title="Личный кабинет"
      :description="`${api.user.value?.username} · ${api.user.value?.email}`"
    >
      <p>Роль: {{ api.user.value?.role === 'business' ? 'Бизнес' : 'Студент / команда' }}</p>
      <UButton
        to="/catalog"
        label="Каталог задач"
      />
      <UButton
        v-if="api.user.value?.role === 'business'"
        to="/tasks/new"
        label="Создать задачу"
      />
      <UButton
        label="Выйти"
        variant="outline"
        @click="logout"
      />
    </UPageCard>
    <UPageCard
      v-if="api.user.value?.role === 'business'"
      title="Мои задачи"
    >
      <UButton
        label="Обновить список"
        variant="outline"
        :loading="pending"
        @click="loadDrafts"
      />
      <p v-if="!drafts.length && !error && !pending">
        Сохранённых задач пока нет.
      </p>
      <UPageCard
        v-for="draft in drafts"
        :key="draft.id"
        :title="draft.card_id ? 'Открыть карточку и отклики' : 'Продолжить заполнение'"
        :description="draft.description"
        :to="draft.card_id ? `/tasks/${draft.card_id}` : `/tasks/new?draft=${draft.id}`"
      />
    </UPageCard>
  </UContainer>
</template>
