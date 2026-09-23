import assert from 'node:assert/strict'
import { createAppI18n, normalizeLocale } from './helpers/i18n.mjs'

for (const value of [undefined, null, '', 'fr', 'EN', '<script>']) assert.equal(normalizeLocale(value), 'ru')
for (const value of ['ru', 'kk', 'en']) assert.equal(normalizeLocale(value), value)

const russian = createAppI18n('ru').global
const english = createAppI18n('en').global
assert.equal(russian.t('navigation.login'), 'Войти')
assert.equal(english.t('navigation.login'), 'Sign in')
english.locale.value = 'kk'
assert.equal(english.t('navigation.login'), 'Кіру')
assert.equal(russian.locale.value, 'ru', 'SSR requests must not share locale state')

english.mergeLocaleMessage('ru', { fallbackTest: 'Русский fallback' })
assert.equal(english.t('fallbackTest'), 'Русский fallback')
russian.mergeLocaleMessage('ru', { countTest: '{count} задача | {count} задачи | {count} задач' })
for (const [count, word] of [[1, 'задача'], [2, 'задачи'], [5, 'задач'], [11, 'задач'], [21, 'задача'], [24, 'задачи'], [112, 'задач']]) {
  assert.equal(russian.t('countTest', count), `${count} ${word}`)
}
const date = new Date('2026-09-23T23:30:00Z')
for (const locale of ['ru', 'kk', 'en']) {
  english.locale.value = locale
  assert.equal(english.d(date, 'date'), new Intl.DateTimeFormat(locale, {
    year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC'
  }).format(date))
  assert.equal(english.n(1234.56, 'decimal'), new Intl.NumberFormat(locale, {
    style: 'decimal', maximumFractionDigits: 2
  }).format(1234.56))
}
console.log('PASS: locale validation, translations, Russian fallback/plurals, SSR isolation, dates and numbers')
