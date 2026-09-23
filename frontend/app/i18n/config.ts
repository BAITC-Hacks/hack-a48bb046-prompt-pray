import { createI18n } from 'vue-i18n'
import ru from './locales/ru'
import kk from './locales/kk'
import en from './locales/en'

export const appLocales = ['ru', 'kk', 'en'] as const
export type AppLocale = typeof appLocales[number]
export const localeCookieName = 'ai-sana-locale'

export function normalizeLocale(value: unknown): AppLocale {
  return appLocales.includes(value as AppLocale) ? value as AppLocale : 'ru'
}

export function createAppI18n(locale: AppLocale) {
  const date = { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' } as const
  const decimal = { style: 'decimal', maximumFractionDigits: 2 } as const

  return createI18n({
    legacy: false,
    locale,
    fallbackLocale: 'ru',
    messages: { ru, kk, en },
    datetimeFormats: { ru: { date }, kk: { date }, en: { date } },
    numberFormats: { ru: { decimal }, kk: { decimal }, en: { decimal } },
    pluralRules: {
      ru: (choice, choicesLength) => {
        const count = Math.abs(choice)
        if (choicesLength === 2) return count === 1 ? 0 : 1
        const mod10 = count % 10
        const mod100 = count % 100
        const form = Number.isInteger(count) && mod10 === 1 && mod100 !== 11
          ? 0
          : Number.isInteger(count) && mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? 1 : 2
        return choicesLength === 4 ? (count === 0 ? 0 : form + 1) : form
      }
    }
  })
}
