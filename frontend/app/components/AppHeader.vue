<script setup lang="ts">
const route = useRoute()
const session = useApi()

const { open: searchOpen } = useContentSearch()

const open = ref(false)

// Both modals portal to `body` with no z-index, so after a client-side layout
// change the menu can end up painted over the search
watch(searchOpen, (value) => {
  if (value) {
    open.value = false
  }
})

const items = computed(() => [{ label: 'Каталог задач', to: '/catalog', active: route.path === '/catalog' }, {
  label: 'Как это работает', to: '/#workflow'
}])
</script>

<template>
  <UHeader v-model:open="open">
    <template #left>
      <NuxtLink
        to="/"
        class="focus-visible:outline-3 outline-primary/25 rounded-md p-1 -ms-1"
      >
        <AppLogo class="w-auto h-6 shrink-0" />
      </NuxtLink>

      <span class="hidden sm:inline-flex text-xs text-muted border border-default rounded-full px-2.5 py-1">Пилот AI Sana</span>
    </template>

    <UNavigationMenu
      :items="items"
      variant="link"
    />

    <template #right>
      <UColorModeButton />

      <UContentSearchButton class="lg:hidden" />

      <UButton
        icon="i-lucide-log-in" aria-label="Вход в аккаунт"
        color="neutral"
        variant="ghost"
        :to="session.token.value ? '/account' : '/login'"
        class="lg:hidden"
      />

      <UButton
        :label="session.token.value ? 'Личный кабинет' : 'Войти'"
        color="neutral"
        variant="outline"
        :to="session.token.value ? '/account' : '/login'"
        class="hidden lg:inline-flex"
      />

      <UButton
        v-if="!session.token.value"
        label="Регистрация"
        color="neutral"
        trailing-icon="i-lucide-arrow-right"
        class="hidden lg:inline-flex"
        to="/signup"
      />
    </template>

    <template #body>
      <UNavigationMenu
        :items="items"
        orientation="vertical"
        class="-mx-2.5"
      />

      <UButton
        v-if="!session.token.value"
        label="Создать задачу"
        to="/tasks/new"
        block
        class="mt-5"
      />
      <USeparator class="my-6" />

      <UButton
        :label="session.token.value ? 'Личный кабинет' : 'Войти'"
        color="neutral"
        variant="subtle"
        :to="session.token.value ? '/account' : '/login'"
        block
        class="mb-3"
      />
      <UButton
        v-if="!session.token.value"
        label="Регистрация"
        color="neutral"
        to="/signup"
        block
      />
    </template>
  </UHeader>
</template>
