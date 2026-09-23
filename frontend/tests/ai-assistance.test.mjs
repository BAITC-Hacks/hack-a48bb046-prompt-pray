import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { test } from 'node:test'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const { ref, reactive, computed } = createRequire(require.resolve('nuxt/package.json'))('vue')

async function page(request) {
  const source = readFileSync(new URL('../app/pages/tasks/new.vue', import.meta.url), 'utf8')
    .match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
  }).outputText
  const globals = {
    useTemplateMode: () => ({ enabled: ref(false), prefill: () => {} }),
    ref, reactive, computed,
    useAppI18n: () => ({ t: key => key }), useSeoMeta: () => {}, definePageMeta: () => {},
    useTemplateRef: () => ref(null), useLocalizedForm: () => {},
    useApiMessages: () => ({ errorMessage: () => '', fieldErrors: () => ({}) }),
    useApi: () => ({ request, user: ref({ role: 'business' }) }),
    useNuxtApp: () => ({ runWithContext: work => work() }), useRoute: () => ({ query: {} }),
    navigateTo: async () => {}
  }
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
  return new AsyncFunction('exports', 'require', ...Object.keys(globals), `${code}
    return { state, draft, answers, questions, visibleQuestions, saveAnswer, assemble, error, dialogue, pending, assemblingCard, adaptNextQuestion, checkSimilar, similar, similarError }`
  )({}, require, ...Object.values(globals))
}

test('dialogue saves an answer before adapting the next question', async () => {
  const calls = []
  const form = await page(async (path, options) => {
    calls.push(path)
    if (path.endsWith('/next-question')) return { id: 'q2', question: 'Who uses the CSV?', answer: null }
    return { answer: options.body.answer }
  })
  form.draft.value = { id: 'd', description: 'Reports' }
  form.state.description = 'Reports'
  form.questions.value = [{ id: 'q1', question: 'Data?', answer: null }, { id: 'q2', question: 'Users?', answer: null }]
  assert.equal(form.visibleQuestions.value.length, 1)
  form.answers.q1 = 'CSV'
  await form.saveAnswer(form.questions.value[0])
  assert.deepEqual(calls, ['/catalog/questions/q1', '/catalog/drafts/d/next-question'])
  assert.equal(form.questions.value[1].question, 'Who uses the CSV?')
  assert.equal(form.visibleQuestions.value.length, 2)
})

test('refinement does not change a question with an unsaved local answer', async () => {
  const calls = []
  const form = await page(async (path) => {
    calls.push(path)
    return { id: 'q', question: 'Changed question', answer: null }
  })
  form.draft.value = { id: 'd', description: 'Reports' }
  form.state.description = 'Reports'
  form.questions.value = [{ id: 'q', question: 'Original question', answer: null }]
  form.answers.q = 'Answer to the original question'
  await form.adaptNextQuestion()
  assert.deepEqual(calls, [])
  assert.equal(form.questions.value[0].question, 'Original question')
  assert.equal(form.answers.q, 'Answer to the original question')
})

for (const stage of ['answer', 'title', 'card']) {
  test(`assembly failure at ${stage} keeps input and clears loading state`, async () => {
    const calls = []
    const form = await page(async (path) => {
      calls.push(path)
      if (path.endsWith(stage === 'answer' ? '/q' : `/${stage}`)) throw new Error('Unavailable')
      return { title: 'Suggested', answer: 'CSV' }
    })
    form.draft.value = { id: 'd', description: 'Reports' }
    form.state.description = 'Reports'
    form.questions.value = [{ id: 'q', answer: null }]
    form.answers.q = 'CSV'
    await form.assemble()
    assert.ok(form.error.value)
    assert.equal(form.pending.value, false)
    assert.equal(form.assemblingCard.value, false)
    assert.equal(form.answers.q, 'CSV')
    assert.equal(form.state.description, 'Reports')
    assert.equal(calls.length, { answer: 1, title: 2, card: 3 }[stage])
  })
}

test('manual title bypasses AI and repeated submit is ignored while pending', async () => {
  let release
  const response = new Promise((resolve) => {
    release = resolve
  })
  const calls = []
  const form = await page(async (path) => {
    calls.push(path)
    return response
  })
  form.draft.value = { id: 'd', description: 'Reports' }
  form.state.description = 'Reports'
  form.state.title = 'Manual title'
  const first = form.assemble()
  await form.assemble()
  release({ id: 'card' })
  await first
  assert.deepEqual(calls, ['/catalog/drafts/d/card'])
  assert.equal(form.state.title, 'Manual title')
})

test('static mode saves answers without refinement and blank answers are not sent', async () => {
  const calls = []
  const form = await page(async (path) => {
    calls.push(path)
    return { answer: 'CSV' }
  })
  form.dialogue.value = false
  form.questions.value = [{ id: 'q', answer: null }, { id: 'q2', answer: null }]
  assert.equal(form.visibleQuestions.value.length, 2)
  form.answers.q = '   '
  await form.saveAnswer(form.questions.value[0])
  assert.deepEqual(calls, [])
  form.answers.q = 'CSV'
  await form.saveAnswer(form.questions.value[0])
  assert.deepEqual(calls, ['/catalog/questions/q'])
})

test('duplicate check failure does not prevent manual assembly', async () => {
  const form = await page(async (path) => {
    if (path.endsWith('/similar')) throw new Error('Unavailable')
    return { id: 'card' }
  })
  form.draft.value = { id: 'd', description: 'Reports' }
  form.state.description = 'Reports'
  form.state.title = 'Reports'
  await form.checkSimilar()
  assert.ok(form.similarError.value)
  await form.assemble()
  assert.equal(form.error.value, null)
})

test('failed AI refinement preserves the saved answer and allows the next static question', async () => {
  const form = await page(async (path, options) => {
    if (path.endsWith('/next-question')) throw new Error('Unavailable')
    return { answer: options.body.answer }
  })
  form.draft.value = { id: 'd', description: 'Reports' }
  form.state.description = 'Reports'
  form.questions.value = [{ id: 'q1', answer: null }, { id: 'q2', question: 'Users?', answer: null }]
  form.answers.q1 = 'CSV'
  await form.saveAnswer(form.questions.value[0])
  assert.equal(form.questions.value[0].answer, 'CSV')
  assert.equal(form.visibleQuestions.value[1].question, 'Users?')
  assert.ok(form.error.value)
})

test('blank title is generated after saving answers and card remains unpublished', async () => {
  const calls = []
  const form = await page(async (path, options) => {
    calls.push([path, options.body])
    if (path.endsWith('/title')) return { title: 'Sales reports' }
    if (path.endsWith('/card')) return { id: 'card' }
    return { answer: options.body.answer }
  })
  form.draft.value = { id: 'd', description: 'Reports' }
  form.state.description = 'Reports'
  form.questions.value = [{ id: 'q1', answer: null }]
  form.answers.q1 = 'CSV'
  await form.assemble()
  assert.equal(form.error.value, null)
  assert.deepEqual(calls.map(([path]) => path), ['/catalog/questions/q1', '/catalog/drafts/d/title', '/catalog/drafts/d/card'])
  assert.equal(calls[2][1].title, 'Sales reports')
})
