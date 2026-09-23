<script setup lang="ts">
import type { ApiError } from '~/types/api'
import type { Draft } from '~/types/catalog'

const { t } = useAppI18n()

definePageMeta({ middleware: 'auth' })
useSeoMeta({ title: () => t('account.title') })
const api = useApi()
const { errorMessage } = useApiMessages()
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
      :title="errorMessage(error)"
    />
    <UPageCard
      :title="t('account.title')"
      :description="`${api.user.value?.username} · ${api.user.value?.email}`"
    >
      <p>{{ t('account.role', { role: api.user.value?.role === 'business' ? t('auth.business') : t('auth.student') }) }}</p>
      <UButton
        to="/catalog"
        :label="t('navigation.catalog')"
      />
      <UButton
        v-if="api.user.value?.role === 'business'"
        to="/tasks/new"
        :label="t('navigation.createTask')"
      />
      <UButton
        :label="t('account.logout')"
        variant="outline"
        @click="logout"
      />
    </UPageCard>
    <UPageCard
      v-if="api.user.value?.role === 'business'"
      :title="t('account.tasks')"
    >
      <UButton
        :label="t('account.refresh')"
        variant="outline"
        :loading="pending"
        @click="loadDrafts"
      />
      <p v-if="!drafts.length && !error && !pending">
        {{ t('account.empty') }}
      </p>
      <UPageCard
        v-for="draft in drafts"
        :key="draft.id"
        :title="draft.card_id ? t('account.openCard') : t('account.continue')"
        :description="draft.description"
        :to="draft.card_id ? `/tasks/${draft.card_id}` : `/tasks/new?draft=${draft.id}`"
      />
    </UPageCard>
  </UContainer>
</template>
