<script setup lang="ts">
const route = useRoute()
const session = useApi()
const { t } = useAppI18n()

const { open: searchOpen } = useContentSearch()

const open = ref(false)
const canCreate = computed(() => session.user.value?.role === 'business')
watch(() => route.fullPath, () => {
  open.value = false
})

// Both modals portal to `body` with no z-index, so after a client-side layout
// change the menu can end up painted over the search
watch(searchOpen, (value) => {
  if (value) {
    open.value = false
  }
})

const items = computed(() => [{ label: t('navigation.catalog'), icon: 'i-lucide-layout-grid', to: '/catalog', active: route.path === '/catalog' || (route.path.startsWith('/tasks/') && route.path !== '/tasks/new') }, {
  label: t('navigation.workflow'), to: '/#workflow'
}])
</script>

<template>
  <UHeader v-model:open="open">
    <template #left>
      <AppLogo class="w-auto h-6 shrink-0 focus-visible:outline-3 outline-primary/25 rounded-md p-1 -ms-1" />

      <span class="hidden sm:inline-flex text-xs text-muted border border-default rounded-full px-2.5 py-1">{{ t('navigation.pilot') }}</span>
    </template>

    <UNavigationMenu
      :items="items"
      variant="link"
    />

    <template #right>
      <LanguageSwitcher />
      <UColorModeButton />

      <UButton
        :icon="session.token.value ? 'i-lucide-user-round' : 'i-lucide-log-in'"
        :aria-label="session.token.value ? t('navigation.account') : t('navigation.loginLabel')"
        color="neutral"
        variant="ghost"
        :to="session.token.value ? '/account' : '/login'"
        class="lg:hidden"
      />

      <UButton
        :label="session.token.value ? t('navigation.account') : t('navigation.login')"
        color="neutral"
        variant="outline"
        :to="session.token.value ? '/account' : '/login'"
        class="hidden lg:inline-flex"
      />

      <UButton
        v-if="canCreate"
        to="/tasks/new"
        :label="t('navigation.createTask')"
        icon="i-lucide-plus"
        class="hidden lg:inline-flex"
      />

      <UButton
        v-if="!session.token.value"
        :label="t('navigation.signup')"
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
        v-if="canCreate || !session.token.value"
        :label="t('navigation.createTask')"
        to="/tasks/new"
        block
        class="mt-5"
      />
      <USeparator class="my-6" />

      <UButton
        :label="session.token.value ? t('navigation.account') : t('navigation.login')"
        color="neutral"
        variant="subtle"
        :to="session.token.value ? '/account' : '/login'"
        block
        class="mb-3"
      />
      <UButton
        v-if="!session.token.value"
        :label="t('navigation.signup')"
        color="neutral"
        to="/signup"
        block
      />
    </template>
  </UHeader>
</template>
