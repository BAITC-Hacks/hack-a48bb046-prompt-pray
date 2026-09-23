// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/image',
    '@nuxt/ui',
    '@nuxt/content',
    '@vueuse/nuxt',
    'nuxt-og-image'
  ],

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  content: {
    experimental: {
      sqliteConnector: 'native'
    }
  },
  runtimeConfig: {
    gatewayUrl: 'http://127.0.0.1:8000',
    public: { apiBase: '/api/gateway' }
  },

  routeRules: {
    '/': { prerender: false, headers: { 'cache-control': 'private, no-store' } },
    '/catalog': { prerender: false, headers: { 'cache-control': 'private, no-store' } },
    '/account': { prerender: false, headers: { 'cache-control': 'private, no-store' } },
    '/tasks/**': { prerender: false, headers: { 'cache-control': 'private, no-store' } },
    '/login': { prerender: false, headers: { 'cache-control': 'private, no-store' } },
    '/signup': { prerender: false, headers: { 'cache-control': 'private, no-store' } },
    '/api/**': { prerender: false, headers: { 'cache-control': 'private, no-store' } },
    '/docs': { redirect: '/docs/getting-started', prerender: false }
  },

  compatibilityDate: '2026-06-30',

  nitro: {
    prerender: {
      // HTML depends on the language cookie, including the landing page.
      routes: [],
      crawlLinks: false
    }
  },

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },

  ogImage: {
    zeroRuntime: true
  }
})
