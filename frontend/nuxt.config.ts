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
    public: {
      apiBase: 'http://localhost:8000/api/v1'
    }
  },

  routeRules: {
    '/account': { prerender: false, headers: { 'cache-control': 'private, no-store' } },
    '/tasks/**': { prerender: false, headers: { 'cache-control': 'private, no-store' } },
    '/catalog': { prerender: false, headers: { 'cache-control': 'private, no-store' } },
    '/api/session/**': { headers: { 'cache-control': 'no-store' } },
    '/docs': { redirect: '/docs/getting-started', prerender: false }
  },

  compatibilityDate: '2026-06-30',

  nitro: {
    prerender: {
      routes: [
        '/'
      ],
      crawlLinks: true
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
