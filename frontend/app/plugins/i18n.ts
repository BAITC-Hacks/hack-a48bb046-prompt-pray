import { createAppI18n, localeCookieName, normalizeLocale } from '~/i18n/config'

export default defineNuxtPlugin((nuxtApp) => {
  const cookie = useCookie(localeCookieName, {
    default: () => 'ru',
    encode: value => value,
    decode: normalizeLocale,
    path: '/',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 365
  })
  // Serialize the server's choice so hydration starts with exactly the same locale.
  const initialLocale = useState('initial-locale', () => normalizeLocale(cookie.value))
  // Each SSR request owns its composer; never share mutable language state globally.
  const i18n = createAppI18n(initialLocale.value)
  nuxtApp.vueApp.use(i18n)

  watch(i18n.global.locale, (value) => {
    cookie.value = normalizeLocale(value)
  }, { flush: 'sync' })
})
