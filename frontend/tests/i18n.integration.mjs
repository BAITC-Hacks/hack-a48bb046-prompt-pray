import assert from 'node:assert/strict'

const base = process.env.I18N_TEST_FRONTEND || 'http://127.0.0.1:3000'
const labels = { ru: 'Язык интерфейса', kk: 'Интерфейс тілі', en: 'Interface language' }
const homeText = {
  ru: ['хочется решить', 'Простой путь к настоящему проекту', 'Польза обеим сторонам', 'Для студентов'],
  kk: ['Шешкің келетін', 'Нақты жобаға бастайтын қарапайым жол', 'Екі тарапқа да пайдалы', 'Студенттерге'],
  en: ['worth solving', 'A simple path to a real project', 'Value for both sides', 'For students']
}
// Concurrent requests catch accidental shared composers and cached language-specific HTML.
await Promise.all(['ru', 'kk', 'en', 'invalid', ''].map(async (cookieLocale) => {
  const locale = cookieLocale in labels ? cookieLocale : 'ru'
  for (const path of ['/', '/login?redirect=/account', '/signup', '/catalog']) {
    const response = await fetch(`${base}${path}`, {
      headers: cookieLocale ? { Cookie: `ai-sana-locale=${cookieLocale}` } : {}
    })
    assert.equal(response.status, 200, path)
    assert.match(response.headers.get('cache-control'), /private.*no-store/)
    const html = await response.text()
    assert.match(html, new RegExp(`<html[^>]*lang="${locale}"`), path)
    assert.ok(html.includes(`aria-label="${labels[locale]}"`), `${path}: server-rendered switcher ${locale}`)
    const options = html.match(/<option\b[^>]*>/g) || []
    assert.ok(options.some(option => option.includes(`value="${locale}"`) && option.includes('selected')), `${path}: selected language`)
    if (path === '/') {
      for (const text of homeText[locale]) assert.ok(html.includes(text), `Landing page missing ${locale}: ${text}`)
      const main = html.match(/<main\b[^>]*>([\s\S]*?)<\/main>/)?.[1] || ''
      assert.ok(main.length > 0)
      if (locale === 'en') assert.doesNotMatch(main, /[А-Яа-яЁё]/, 'English landing body must not contain Russian text')
    }
  }
}))
console.log('PASS: cookie-based SSR on landing/auth/catalog, default/invalid locale, private HTML cache policy')
