<script setup lang="ts">
import { ru, kk, en } from '@nuxt/ui/locale'
import { normalizeLocale } from '~/i18n/config'

const { locale, t } = useAppI18n()
const uiLocale = computed(() => ({ ru, kk, en })[normalizeLocale(locale.value)])
const colorMode = useColorMode()
const pendingRequests = useState('api-pending-requests', () => 0)
const themeColor = computed(() => colorMode.value === 'dark' ? '#020618' : '#ffffff')

useHead({
  meta: [
    { charset: 'utf-8' },
    { name: 'viewport', content: 'width=device-width, initial-scale=1' },
    { key: 'theme-color', name: 'theme-color', content: themeColor }
  ],
  link: [{ rel: 'icon', href: '/favicon.ico' }],
  htmlAttrs: { lang: locale }
})
useSeoMeta({
  titleTemplate: '%s — AI Sana',
  twitterCard: 'summary_large_image'
})
const { data: navigation } = await useAsyncData('navigation', () => queryCollectionNavigation('docs'), {
  transform: data => data.find(item => item.path === '/docs')?.children || []
})
const { data: files } = useLazyAsyncData('search', () => queryCollectionSearchSections('docs'), { server: false })
provide('navigation', navigation)
</script>

<template>
  <UApp :locale="uiLocale">
    <NuxtLoadingIndicator />
    <ClientOnly>
      <div
        v-if="pendingRequests > 0"
        role="status"
        aria-live="polite"
        class="pointer-events-none fixed right-4 bottom-4 z-50 flex items-center gap-2 rounded-lg border border-default bg-default px-4 py-3 text-sm shadow-lg"
      >
        <UIcon
          name="i-lucide-loader-circle"
          class="size-4 animate-spin"
        />
        {{ t('navigation.requestPending') }}
      </div>
    </ClientOnly>
    <NuxtLayout>
      <AuthAvailability>
        <NuxtPage />
      </AuthAvailability>
    </NuxtLayout>
    <ClientOnly>
      <LazyUContentSearch
        :files="files"
        :navigation="navigation"
        :links="navLinks"
        :fuse="{ resultLimit: 42 }"
      />
    </ClientOnly>
  </UApp>
</template>
