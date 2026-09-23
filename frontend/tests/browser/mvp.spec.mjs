import { randomUUID } from 'node:crypto'
import { test, expect } from '@playwright/test'
import { createAppI18n } from '../helpers/i18n.mjs'

const password = 'Browser-test-password-123!'
const root = '/api/gateway/catalog'
const questions = {
  ru: 'Кто будет пользоваться решением?',
  kk: 'Шешімді кім пайдаланады?',
  en: 'Who will use the solution?'
}
const translate = locale => createAppI18n(locale).global.t

async function hydrated(page) {
  // SSR controls are visible before async page setup attaches event handlers.
  // Wait for Nuxt's hydration completion, not an arbitrary delay or a retry.
  await page.waitForFunction(() => document.querySelector('#__nuxt')?.__vue_app__?.$nuxt?.isHydrating === false)
}

async function account(request, role) {
  const username = `browser_${randomUUID().replaceAll('-', '').slice(0, 16)}`
  const response = await request.post('/api/session/register', {
    headers: { 'X-Requested-With': 'AI-Sana' },
    data: { username, email: `${username}@example.com`, password, role }
  })
  expect(response.status(), await response.text()).toBe(201)
  return username
}

async function language(page, locale) {
  await page.locator('select[aria-label]').selectOption(locale)
  await expect(page.locator('html')).toHaveAttribute('lang', locale)
}

async function login(page, username, locale, target = '/account') {
  const t = translate(locale)
  await page.goto(`/login?redirect=${encodeURIComponent(target)}`)
  await hydrated(page)
  await language(page, locale)
  await page.getByLabel(t('auth.identifier'), { exact: true }).fill(username)
  await page.getByLabel(t('auth.password'), { exact: true }).fill(password)
  const response = page.waitForResponse(r => r.url().endsWith('/api/session/login') && r.request().method() === 'POST')
  await page.getByRole('button', { name: t('navigation.login'), exact: true }).click()
  const session = await (await response).json()
  await expect(page).toHaveURL(new RegExp(`${target.replace(/[?]/g, '\\?')}$`))
  return session.access_token
}

for (const locale of ['ru', 'kk', 'en']) {
  test(`${locale}: SSR, forms, low-rating task, proposals and manual decisions`, async ({ browser, page, request, baseURL }) => {
    const t = translate(locale)
    const alternate = locale === 'en' ? 'kk' : 'en'
    const other = translate(alternate)
    const runtimeErrors = []
    function watchErrors(target) {
      target.on('pageerror', error => runtimeErrors.push(`${target.url()}: ${error.message}`))
      target.on('console', (message) => {
        if (/hydration.*mismatch/i.test(message.text())) runtimeErrors.push(`${target.url()}: ${message.text()}`)
      })
    }
    watchErrors(page)

    await page.goto('/')
    await hydrated(page)
    await language(page, locale)
    await page.reload()
    await hydrated(page)
    await expect(page.locator('html')).toHaveAttribute('lang', locale)
    await expect(page.getByRole('heading', { name: t('home.workflowTitle'), exact: true })).toBeVisible()
    const ssr = await page.request.get('/')
    expect(ssr.headers()['cache-control']).toMatch(/private.*no-store/)
    expect(await ssr.text()).toContain(`lang="${locale}"`)
    expect(await ssr.text()).toContain(t('home.highlight'))

    const business = await account(request, 'business')
    const students = [await account(request, 'student'), await account(request, 'student')]
    await page.goto('/login?redirect=/account#form')
    await hydrated(page)
    await page.getByLabel(t('auth.identifier'), { exact: true }).fill(business)
    await page.getByLabel(t('auth.password'), { exact: true }).fill('wrong-password')
    await language(page, alternate)
    await expect(page).toHaveURL(/\/login\?redirect=\/account#form$/)
    await expect(page.getByLabel(other('auth.identifier'), { exact: true })).toHaveValue(business)
    await expect(page.getByLabel(other('auth.password'), { exact: true })).toHaveValue('wrong-password')
    await page.getByRole('button', { name: other('navigation.login'), exact: true }).click()
    await expect(page.getByText(other('errors.invalid_credentials'), { exact: true })).toBeVisible()
    await language(page, locale)
    await expect(page.getByText(t('errors.invalid_credentials'), { exact: true })).toBeVisible()
    const token = await login(page, business, locale)
    const headers = { Authorization: `Bearer ${token}` }

    await page.goto('/tasks/new')
    await hydrated(page)
    await page.getByRole('button', { name: t('task.getQuestions'), exact: true }).click()
    await expect(page.getByText(t('validation.description'), { exact: true })).toBeVisible()
    await language(page, alternate)
    await expect(page.getByText(other('validation.description'), { exact: true })).toBeVisible()
    const description = `Original бизнес мәтіні ${randomUUID()}`
    await page.getByLabel(other('task.problem'), { exact: true }).fill(description)
    await language(page, locale)
    await expect(page.getByLabel(t('task.problem'), { exact: true })).toHaveValue(description)

    const draftResponse = page.waitForResponse(r => r.url().endsWith(`${root}/drafts`) && r.request().method() === 'POST')
    await page.getByRole('button', { name: t('task.getQuestions'), exact: true }).click()
    const draft = await (await draftResponse).json()
    expect(draft.locale).toBe(locale)
    expect(draft.description).toBe(description)
    await expect(page.getByText(t('errors.ai_unavailable'), { exact: true })).toBeVisible()
    await page.getByRole('button', { name: t('task.retry'), exact: true }).click()
    await expect(page.locator('[data-question-card]')).toHaveCount(3)
    const answer = 'Original answer — бастапқы жауап'
    await page.getByLabel(questions[locale], { exact: true }).fill(answer)
    await language(page, alternate)
    await expect(page.getByLabel(questions[locale], { exact: true })).toHaveValue(answer)
    await expect(page.locator('[data-question-card]')).toHaveCount(3)
    await language(page, locale)
    await page.locator('[data-question-card]').first().getByRole('button', { name: t('task.save'), exact: true }).click()
    await expect(page.locator('[data-question-card]').first().getByRole('button', { name: t('task.saved'), exact: true })).toBeVisible()
    await page.reload()
    await hydrated(page)
    await expect(page.getByLabel(questions[locale], { exact: true })).toHaveValue(answer)
    await expect(page.locator('html')).toHaveAttribute('lang', locale)

    const title = `Browser ${locale} ${randomUUID()}`
    await page.getByLabel(t('task.title'), { exact: true }).fill(title)
    const cardResponse = page.waitForResponse(r => r.url().endsWith(`/drafts/${draft.id}/card`) && r.request().method() === 'POST')
    await page.getByRole('button', { name: t('task.assemble'), exact: true }).click()
    const card = await (await cardResponse).json()
    expect(card.rating.total).toBe(30)
    expect(card.users).toBe(answer)
    expect(card.context).toBe(description)
    expect(card.confirmed_at).toBeNull()
    await expect(page).toHaveURL(new RegExp(`/tasks/${card.id}$`))
    await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '30')
    await expect(page.getByText(t('rating.draft'), { exact: true })).toBeVisible()
    expect((await (await request.get(root)).json()).items.some(item => item.task_id === card.id)).toBe(false)
    const publication = page.waitForResponse(r => r.url().endsWith(`/tasks/${card.id}/publish`) && r.request().method() === 'POST')
    await page.getByRole('button', { name: t('task.publish'), exact: true }).click()
    expect((await publication).ok()).toBe(true)
    await expect(page.getByText(t('task.published'), { exact: true })).toBeVisible()
    await page.goto('/catalog')
    await hydrated(page)
    await page.getByRole('link').filter({ has: page.getByRole('heading', { name: title, exact: true }) }).click()
    await expect(page).toHaveURL(new RegExp(`/tasks/${card.id}$`))

    const proposals = []
    for (const [index, username] of students.entries()) {
      const context = await browser.newContext({ baseURL })
      try {
        const studentPage = await context.newPage()
        watchErrors(studentPage)
        await login(studentPage, username, locale, `/tasks/${card.id}`)
        const idea = `Student ${index} idea — идея`
        await studentPage.getByLabel(t('proposal.idea'), { exact: true }).fill(idea)
        await studentPage.getByLabel(t('proposal.plan'), { exact: true }).fill('Plan — жоспар')
        await language(studentPage, alternate)
        await expect(studentPage.getByLabel(other('proposal.idea'), { exact: true })).toHaveValue(idea)
        await language(studentPage, locale)
        const response = studentPage.waitForResponse(r => r.url().endsWith(`/tasks/${card.id}/proposals`) && r.request().method() === 'POST')
        await studentPage.getByRole('button', { name: t('proposal.send'), exact: true }).click()
        const submitted = await response
        expect(submitted.status()).toBe(201)
        proposals.push(await submitted.json())
        await expect(studentPage.getByText(t('task.proposalSent'), { exact: true })).toBeVisible()
        await expect(studentPage.getByRole('checkbox')).toHaveCount(0)
      } finally {
        await context.close()
      }
    }

    const decisionsUrl = `${root}/tasks/${card.id}/decisions`
    expect(await (await page.request.get(decisionsUrl, { headers })).json()).toEqual([])
    await page.reload()
    await hydrated(page)
    const boxes = page.getByRole('checkbox', { name: t('proposal.select'), exact: true })
    await expect(boxes).toHaveCount(2)
    const displayed = await (await page.request.get(`${root}/tasks/${card.id}/proposals`, { headers })).json()
    for (const count of [1, 2, 0]) {
      for (let i = 0; i < 2; i++) await boxes.nth(i).setChecked(i < count)
      const response = page.waitForResponse(r => r.url().endsWith(decisionsUrl) && r.request().method() === 'POST')
      await page.getByRole('button', { name: count ? t('proposal.confirm', { count }) : t('proposal.confirmNone'), exact: true }).click()
      const saved = await response
      expect(saved.status()).toBe(201)
      const decision = await saved.json()
      expect(decision.selected_proposal_ids).toHaveLength(count)
      expect([...decision.selected_proposal_ids].sort()).toEqual(displayed.slice(0, count).map(proposal => proposal.id).sort())
      expect(decision.selected_proposal_ids.every(id => proposals.some(proposal => proposal.id === id))).toBe(true)
      await expect(page.getByText(count ? t('task.decisionSaved', { count }, count) : t('task.decisionNone'), { exact: true })).toBeVisible()
      await page.reload()
      await hydrated(page)
      await expect(boxes).toHaveCount(2)
      await expect(page.getByRole('checkbox', { checked: true })).toHaveCount(count)
    }
    expect(runtimeErrors).toEqual([])
  })
}
