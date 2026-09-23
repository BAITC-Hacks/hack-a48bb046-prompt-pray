import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import ts from 'typescript'

function load(path, globals) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8')
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
  }).outputText
  const exports = {}
  new Function('exports', ...Object.keys(globals), compiled)(exports, ...Object.values(globals))
  return exports
}

function states() {
  const values = new Map()
  return (key, init) => {
    if (!values.has(key)) values.set(key, { value: init() })
    return values.get(key)
  }
}

test('auth outage preserves session, retries in place, and redirects only on 401', async () => {
  const existingUser = { id: 'business', role: 'business' }
  const user = { value: existingUser }
  let error = { status: 503, code: 'upstream_unavailable' }
  const redirects = []
  const { useAuthAvailability } = load('../app/composables/useAuthAvailability.ts', {
    useState: states(),
    useApi: () => ({ user, request: async () => {
      if (error) throw error
      return existingUser
    } }),
    navigateTo: target => redirects.push(target)
  })
  const auth = useAuthAvailability()
  for (const status of [503, 502, 504, 0, 403]) {
    error = { status, code: 'upstream_unavailable' }
    await auth.check('/tasks/new?draft=123')
    assert.equal(user.value, existingUser)
    assert.equal(auth.failure.value.path, '/tasks/new?draft=123')
    assert.equal(auth.pending.value, false)
    assert.equal(redirects.length, 0)
  }
  user.value = null
  await auth.check('/account')
  assert.ok(auth.failure.value, 'first-load outage gets a recoverable fallback')
  error = null
  await auth.check('/account')
  assert.equal(auth.failure.value, null)
  assert.equal(user.value, existingUser)
  error = { status: 401 }
  await auth.check('/tasks/new?draft=123')
  assert.deepEqual(redirects, [{ path: '/login', query: { redirect: '/tasks/new?draft=123' } }])
})

test('catalog failures do not refresh/logout or replay writes, and always release loading state', async () => {
  const user = { value: { id: 'business' } }
  const token = { value: 'valid-token' }
  const useState = states()
  let count = 0
  let code = 503
  const { useApi } = load('../app/composables/useApi.ts', {
    useState,
    useSession: () => ({ user, token,
      refresh: () => assert.fail('outage must not refresh session'),
      clear: () => assert.fail('outage must not clear session') }),
    useRuntimeConfig: () => ({ public: { apiBase: '/api/gateway' } }),
    useRequestFetch: () => async () => {
      count++
      throw { statusCode: code }
    }
  })
  for (const [status, expected] of [[503, 'upstream_unavailable'], [502, 'upstream_unavailable'], [504, 'upstream_timeout'], [0, 'network_error']]) {
    code = status
    const before = count
    await assert.rejects(useApi().request('/catalog/drafts', { method: 'POST', body: { description: 'Draft' } }),
      error => error.status === status && error.code === expected)
    assert.equal(count, before + 1, 'writes are not automatically retried')
    assert.equal(useState('api-pending-requests').value, 0)
    assert.equal(token.value, 'valid-token')
    assert.equal(user.value.id, 'business')
  }
})
