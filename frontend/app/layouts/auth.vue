<script setup lang="ts">
const { t } = useAppI18n()
</script>

<template>
  <div class="relative isolate flex min-h-dvh items-center justify-center bg-gradient-to-b from-primary/5 to-transparent px-4 py-28">
    <UButton
      icon="i-lucide-chevron-left"
      to="/"
      :aria-label="t('navigation.home')"
      size="xl"
      color="neutral"
      variant="subtle"
      class="absolute left-4 top-6 sm:left-8 rounded-full z-10"
    />

    <div class="absolute right-4 top-6 z-10 flex items-center gap-2 sm:right-8">
      <LanguageSwitcher />
      <UColorModeButton />
    </div>

    <div
      data-app-panel
      data-app-reveal
      class="w-full max-w-md shadow-xl shadow-black/5"
    >
      <div class="mb-8 flex justify-center">
        <AppLogo class="h-8 w-auto" />
      </div>
      <slot />
    </div>
  </div>
</template>
