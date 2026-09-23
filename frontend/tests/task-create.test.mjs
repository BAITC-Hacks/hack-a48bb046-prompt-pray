import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { test } from 'node:test'
import ts from 'typescript'
import { createAppI18n } from './helpers/i18n.mjs'

const require = createRequire(import.meta.url)
const nuxtRequire = createRequire(require.resolve('nuxt/package.json'))
const { compileScript, parse } = nuxtRequire('vue/compiler-sfc')
const { createSSRApp, h, ref, reactive, computed, useTemplateRef } = nuxtRequire('vue')
const { renderToString } = nuxtRequire('vue/server-renderer')
const filename = new URL('../app/pages/tasks/new.vue', import.meta.url)
const { descriptor } = parse(readFileSync(filename, 'utf8'))
const compiled = compileScript(descriptor, { id: 'new-task-test', inlineTemplate: true })
const code = ts.transpileModule(compiled.content, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
}).outputText

async function renderPage(role, saved = false, questions = []) {
  const i18n = createAppI18n('ru')
  const globals = {
    ref, reactive, computed, useTemplateRef,
    useAppI18n: () => i18n.global,
    useSeoMeta: () => {},
    useLocalizedForm: () => {},
    useApiMessages: () => ({ errorMessage: () => '', fieldErrors: () => ({}) }),
    definePageMeta: () => {},
    useApi: () => ({ user: ref({ role }), request: async path => path.endsWith('/questions') ? questions : { id: 'saved', description: 'Saved description', card_id: null } }),
    useNuxtApp: () => ({}),
    useRoute: () => ({ query: saved ? { draft: 'saved' } : {} })
  }
  const exports = {}
  new Function('exports', 'require', ...Object.keys(globals), code)(exports, name => name === 'vue' ? nuxtRequire(name) : require(name), ...Object.values(globals))
  const app = createSSRApp(exports.default)
  for (const name of ['UContainer', 'UForm', 'UFormField']) {
    app.component(name, { setup: (_, { slots }) => () => h('div', slots.default?.()) })
  }
  for (const name of ['UPageHeader', 'TasksTaskWorkflow', 'TasksTaskQuestion', 'TasksTaskAiLoading', 'UInput', 'USelect', 'UBadge', 'UIcon', 'UProgress']) {
    app.component(name, { render: () => null })
  }
  app.component('UTextarea', {
    props: ['modelValue', 'disabled'],
    setup: props => () => h('textarea', { disabled: props.disabled }, props.modelValue)
  })
  app.component('UButton', {
    props: ['label', 'disabled'],
    setup: props => () => h('button', { disabled: props.disabled }, props.label)
  })
  app.component('UAlert', {
    props: ['title', 'description'],
    setup: props => () => h('p', `${props.title} ${props.description || ''}`)
  })
  return renderToString(app)
}

test('business sees an editable description and enabled create action', async () => {
  const html = await renderPage('business')
  assert.match(html, /<textarea/)
  assert.doesNotMatch(html, /<textarea[^>]*disabled/)
  assert.match(html, /<button(?![^>]*disabled)[^>]*>Сохранить и получить вопросы/)
})

for (const questions of [[], [{ id: 'q', answer: null }]]) {
  test(`saved draft remains editable with ${questions.length} questions`, async () => {
    const html = await renderPage('business', true, questions)
    assert.match(html, /<textarea[^>]*>Saved description<\/textarea>/)
    assert.doesNotMatch(html, /<textarea[^>]*disabled/)
  })
}

test('student sees an editable description and explanation instead of a missing form', async () => {
  const html = await renderPage('student')
  assert.match(html, /<textarea/)
  assert.doesNotMatch(html, /<textarea[^>]*disabled/)
  assert.match(html, /Для сохранения нужен аккаунт бизнеса/)
  assert.match(html, /<button[^>]*disabled[^>]*>Сохранить и получить вопросы/)
})
