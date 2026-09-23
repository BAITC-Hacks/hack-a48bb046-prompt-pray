<script setup lang="ts">
const columns = [{
  label: 'Проекты',
  children: [{ label: 'Открытые задачи', to: '/catalog' }, { label: 'Предложить задачу', to: '/tasks/new' }]
}, {
  label: 'Участникам',
  children: [{ label: 'Войти', to: '/login' }, { label: 'Создать аккаунт', to: '/signup' }]
}]
</script>

<template>
  <USeparator
    icon="i-lucide-sparkles"
    class="h-px"
  />
  <UFooter :ui="{ top: 'border-b border-default' }">
    <template #top>
      <UContainer class="py-3">
        <UFooterColumns :columns="columns">
          <template #right>
            <p
              class="max-w-sm text-sm leading-relaxed text-muted"
            >
              AI Sana помогает бизнесу и студенческим командам находить проекты для совместной работы.
            </p>
          </template>
        </UFooterColumns>
      </UContainer>
    </template>
    <template #left>
      <p class="text-muted text-sm">
        AI Sana · Пилотный проект · © {{ new Date().getFullYear() }}
      </p>
    </template>
    <template #right>
      <ULink
        to="/catalog"
        class="text-sm text-muted hover:text-default"
      >Каталог задач</ULink>
    </template>
  </UFooter>
</template>
