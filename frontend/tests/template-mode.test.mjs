import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { test } from 'node:test'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const { computed, reactive, watch, nextTick, effectScope } = createRequire(require.resolve('nuxt/package.json'))('vue')
const source = readFileSync(new URL('../app/composables/useTemplateMode.ts', import.meta.url), 'utf8')
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText

test('template mode requires t=1, allows clearing text and preserves edits on navigation', async () => {
  const route = reactive({ query: {} })
  const exports = {}
  new Function('exports', 'useRoute', 'computed', 'watch', code)(exports, () => route, computed, watch)
  const scope = effectScope()
  const form = reactive({ description: '' })
  const template = scope.run(() => {
    const template = exports.useTemplateMode()
    template.prefill(() => {
      if (!form.description) form.description = template.description
    })
    return template
  })
  assert.equal(form.description, '')
  route.query = { t: '0' }
  await nextTick()
  assert.equal(form.description, '')
  route.query = { t: '1' }
  await nextTick()
  assert.equal(form.description, template.description)
  form.description = ''
  await nextTick()
  assert.equal(form.description, '')
  form.description = 'Мой текст'
  route.query = { t: '1', draft: 'saved' }
  await nextTick()
  assert.equal(form.description, 'Мой текст')
  scope.stop()
})

test('navigation carries template flag and respects explicit opt out', () => {
  const source = readFileSync(new URL('../app/middleware/00.template.global.ts', import.meta.url), 'utf8')
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  const exports = {}
  new Function('exports', 'defineNuxtRouteMiddleware', 'navigateTo', code)(exports, fn => fn, to => to)
  const from = { query: { t: '1' } }
  assert.deepEqual(exports.default({ path: '/tasks/new', query: { draft: 'saved' }, hash: '#form' }, from), {
    path: '/tasks/new', query: { draft: 'saved', t: '1' }, hash: '#form'
  })
  assert.equal(exports.default({ query: { t: '0' } }, from), undefined)
  assert.equal(exports.default({ query: {} }, { query: {} }), undefined)
})
