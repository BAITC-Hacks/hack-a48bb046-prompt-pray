import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { test } from 'node:test'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const { ref, computed } = createRequire(require.resolve('nuxt/package.json'))('vue')
const compile = source => ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
}).outputText
const types = {}
new Function('exports', compile(readFileSync(new URL('../app/types/catalog.ts', import.meta.url), 'utf8')))(types)
const initial = {
  id: 'task', business_id: 'owner', version: 1, title: 'Original', confirmed_at: null,
  ...Object.fromEntries(types.cardFields.map(field => [field.key, null]))
}

async function page(request) {
  const source = readFileSync(new URL('../app/pages/tasks/[id].vue', import.meta.url), 'utf8')
    .match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]
  const globals = {
    computed, useAppI18n: () => ({ t: key => key, n: value => String(value), locale: ref('ru') }),
    useSeoMeta: () => {}, useTemplateRef: () => ref(null), useLocalizedForm: () => {},
    useApiMessages: () => ({ errorMessage: () => '', fieldErrors: () => ({}) }),
    useRewardFeedback: () => ({ track: work => work() }),
    ref, useApi: () => ({ request, user: ref({ id: 'owner', role: 'business' }) }),
    useRoute: () => ({ params: { id: 'task' } })
  }
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
  return new AsyncFunction('exports', 'require', ...Object.keys(globals),
    `${compile(source)}\nreturn { card, form, error, conflict, localCopy, save, publish, action, reloadLatest, restoreLocalText, hasChanges, filledCount }`
  )({}, name => name === '~/types/catalog' ? types : require(name), ...Object.values(globals))
}

test('review tracks unsaved edits and filled sections without changing the saved card', async () => {
  const state = await page(async path => path.endsWith('/task') ? { ...initial } : [])
  assert.equal(state.hasChanges.value, false)
  assert.equal(state.filledCount.value, 0)
  state.form.value.title = 'Updated title'
  state.form.value.context = '  A business need  '
  state.form.value.data = '   '
  assert.equal(state.hasChanges.value, true)
  assert.equal(state.filledCount.value, 1)
  assert.equal(state.card.value.title, 'Original')
  assert.equal(state.card.value.context, null)
})

for (const operation of ['PATCH', 'confirm', 'publish']) {
  test(`${operation} conflict keeps input and requires explicit recovery`, async () => {
    let current = { ...initial }
    let conflictEnabled = true
    let failReload = false
    let reads = 0
    const form = await page(async (path, options) => {
      if (!options) {
        if (path.endsWith('/proposals') || path.endsWith('/decisions')) return []
        if (++reads > 1 && failReload) throw new Error('Network unavailable')
        return { ...current }
      }
      const kind = options.method === 'PATCH' ? 'PATCH' : path.split('/').at(-1)
      assert.equal(options.body.expected_version, current.version)
      if (conflictEnabled && kind === operation) {
        current = { ...current, title: 'Changed by another editor', version: current.version + 1 }
        throw { status: 409, code: 'catalog_version_conflict', detail: 'Card changed', fields: {} }
      }
      current = { ...current, version: current.version + 1 }
      if (kind === 'PATCH') {
        const { expected_version, ...fields } = options.body
        assert.ok(expected_version)
        Object.assign(current, fields)
      }
      return kind === 'publish' ? { task: { ...current } } : { ...current }
    })
    form.form.value.title = 'My unsaved text'
    if (operation === 'PATCH') await form.action(form.save)
    else await form.publish()
    assert.equal(form.error.value.code, 'catalog_version_conflict')
    assert.equal(form.form.value.title, 'My unsaved text')
    assert.equal(form.localCopy.value.title, 'My unsaved text')
    assert.equal(form.conflict.value, true)
    failReload = true
    await form.reloadLatest()
    assert.equal(form.form.value.title, 'My unsaved text', 'A failed reload must not discard input')
    assert.equal(form.conflict.value, true)
    failReload = false
    await form.reloadLatest()
    assert.equal(form.card.value.version, current.version)
    assert.equal(form.form.value.title, 'Changed by another editor')
    assert.equal(form.localCopy.value.title, 'My unsaved text', 'Local copy survives loading the server version')
    assert.equal(form.conflict.value, false)
    form.restoreLocalText()
    assert.equal(form.form.value.title, 'My unsaved text')
    conflictEnabled = false
    await form.action(form.save)
    assert.equal(form.error.value, null)
    assert.equal(current.title, 'My unsaved text')
    assert.equal(form.card.value.version, current.version)
  })
}

test('save → confirm → publish uses each returned version, including the publication response', async () => {
  const versions = []
  const form = await page(async (path, options) => {
    if (!options) return path.endsWith('/task') ? { ...initial } : []
    versions.push(options.body.expected_version)
    const next = { ...initial, title: 'New title', version: options.body.expected_version + 1 }
    return path.endsWith('/publish') ? { task: next } : next
  })
  form.form.value.title = 'New title'
  await form.publish()
  assert.equal(form.error.value, null)
  assert.deepEqual(versions, [1, 2, 3])
  assert.equal(form.card.value.version, 4)
})
