<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const api = useApi()
async function logout() {
  await api.request('/auth/logout', { method: 'POST' })
  api.token.value = null
  api.user.value = null
  await navigateTo('/login')
}
</script>

<template>
  <UContainer class="py-12">
    <UPageCard
      title="Личный кабинет"
      :description="api.user.value?.email"
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
  </UContainer>
</template>
