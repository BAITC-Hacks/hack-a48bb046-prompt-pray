<script setup lang="ts">
const { t } = useAppI18n()
</script>

<template>
  <div>
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-xl focus:bg-primary focus:px-5 focus:py-3 focus:text-inverted"
    >{{ t('interface.skip') }}</a>
    <AppHeader />

    <UMain
      id="main-content"
      tabindex="-1"
    >
      <slot />
    </UMain>

    <AppFooter />
  </div>
</template>
