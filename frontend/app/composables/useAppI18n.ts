import { useI18n } from 'vue-i18n'
import { normalizeLocale } from '~/i18n/config'

export function useAppI18n() {
  const composer = useI18n({ useScope: 'global' })
  function setLocale(value: string) {
    composer.locale.value = normalizeLocale(value)
  }
  return { ...composer, setLocale }
}
