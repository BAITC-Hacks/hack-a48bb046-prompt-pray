import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { test } from 'node:test'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const { ref, reactive } = createRequire(require.resolve('nuxt/package.json'))('vue')

// Execute the real page script with Nuxt navigation and API calls replaced.
async function page(request, query = {}) {
  const source = readFileSync(new URL('../app/pages/tasks/new.vue', import.meta.url), 'utf8')
    .match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
  }).outputText
  const globals = {
    ref, reactive, definePageMeta: () => {}, useApi: () => ({ request }),
    useNuxtApp: () => ({ runWithContext: work => work() }),
    useRoute: () => ({ query }), navigateTo: async () => {}
  }
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
  return new AsyncFunction('exports', 'require', ...Object.keys(globals),
    `${compiled}\nreturn { state, draft, answers, questions, createDraft, loadQuestions, error }`
  )({}, require, ...Object.values(globals))
}

for (const locale of ['ru', 'kk', 'en']) {
  test(`draft creation sends ${locale} and retries without changing the saved draft`, async () => {
    let created = 0
    let generated = 0
    const form = await page(async (path, options) => {
      if (path === '/catalog/drafts') {
        created++
        assert.deepEqual(options.body, { description: 'Original description', locale })
        return { id: 'draft', ...options.body, card_id: null }
      }
      assert.equal(path, '/catalog/drafts/draft/questions')
      if (++generated === 1) throw new Error('AI temporarily unavailable')
      return [{ id: 'q', question: 'Question?', answer: null }]
    })
    form.state.description = 'Original description'
    form.state.title = 'My title'
    form.state.locale = locale
    await form.createDraft()
    assert.ok(form.error.value)
    assert.equal(form.draft.value.locale, locale)
    await form.createDraft()
    assert.equal(created, 1)
    assert.equal(generated, 2)
    assert.equal(form.state.description, 'Original description')
    assert.equal(form.state.title, 'My title')
    form.answers.q = 'Unsaved answer'
    await form.loadQuestions()
    assert.equal(form.answers.q, 'Unsaved answer', 'Reloading questions must not erase local input')
  })

  test(`reopening ${locale} restores its language and answers without regeneration`, async () => {
    const form = await page(async (path, options) => {
      assert.equal(options, undefined, 'Reopening must use GET without generating new questions')
      if (path === '/catalog/drafts/saved') {
        return { id: 'saved', description: 'Бастапқы мәтін', locale, card_id: null }
      }
      assert.equal(path, '/catalog/drafts/saved/questions')
      return [{ id: 'q', question: 'Saved question?', answer: 'Сохранённый ответ' }]
    }, { draft: 'saved' })
    assert.equal(form.state.locale, locale)
    assert.equal(form.state.description, 'Бастапқы мәтін')
    assert.equal(form.answers.q, 'Сохранённый ответ')
    assert.equal(form.questions.value[0].question, 'Saved question?')
  })
}
