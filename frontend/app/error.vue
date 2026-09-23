<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{ error: NuxtError }>()
const { t, locale } = useAppI18n()
const notFound = computed(() => props.error.statusCode === 404)
const title = computed(() => t(notFound.value ? 'interface.notFound' : 'interface.errorTitle'))
const description = computed(() => t(notFound.value ? 'interface.notFoundHint' : 'interface.errorHint'))
useHead({ htmlAttrs: { lang: () => locale.value } })
useSeoMeta({ title: () => title.value, description: () => description.value })
</script>

<template>
  <UApp>
    <div class="flex min-h-dvh flex-col bg-gradient-to-b from-primary/5 to-transparent">
      <UContainer class="flex w-full items-center justify-between py-6">
        <AppLogo class="h-7 w-auto" />
        <div class="flex items-center gap-2">
          <LanguageSwitcher />
          <UColorModeButton />
        </div>
      </UContainer>
      <main class="flex flex-1 items-center justify-center px-4 py-16">
        <section
          data-app-panel
          data-app-reveal
          class="w-full max-w-xl text-center"
        >
          <div class="mx-auto mb-6 flex size-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <UIcon
              :name="notFound ? 'i-lucide-map-pin-off' : 'i-lucide-cloud-off'"
              class="size-8"
              aria-hidden="true"
            />
          </div>
          <p class="mb-3 text-sm font-semibold tabular-nums text-primary">
            {{ error.statusCode }}
          </p>
          <h1 class="text-3xl font-semibold tracking-tight text-highlighted">
            {{ title }}
          </h1>
          <p class="mx-auto mt-4 max-w-md text-sm leading-7 text-muted">
            {{ description }}
          </p>
          <div class="mt-8 flex flex-wrap justify-center gap-3">
            <UButton
              :label="t('navigation.catalog')"
              icon="i-lucide-layout-grid"
              size="lg"
              @click="clearError({ redirect: '/catalog' })"
            />
            <UButton
              v-if="!notFound"
              :label="t('interface.retry')"
              icon="i-lucide-refresh-cw"
              color="neutral"
              variant="outline"
              size="lg"
              @click="clearError()"
            />
            <UButton
              v-else
              :label="t('navigation.home')"
              icon="i-lucide-house"
              color="neutral"
              variant="outline"
              size="lg"
              @click="clearError({ redirect: '/' })"
            />
          </div>
        </section>
      </main>
      <AppFooter />
    </div>
  </UApp>
</template>
