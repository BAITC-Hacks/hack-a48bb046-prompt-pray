import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { createHmac } from 'node:crypto'
import ts from 'typescript'

// Run against the local Nuxt server and gateway with a disposable auth database.
const base = process.env.AUTH_TEST_FRONTEND || 'http://127.0.0.1:3000'
const gateway = process.env.AUTH_TEST_GATEWAY || 'http://127.0.0.1:8000/api/v1'
const secret = process.env.AUTH_TEST_JWT_SECRET
assert.ok(secret, 'Set AUTH_TEST_JWT_SECRET to the disposable backend JWT key to test expiry')
const input = { email: `t10-${Date.now()}@example.com`, username: `t10_${Date.now()}`, password: 'Test-password-123!' }
const headers = { 'Content-Type': 'application/json', 'X-Requested-With': 'AI-Sana' }
const call = (action, body, cookie = '') => fetch(`${base}/api/session/${action}`, { method: 'POST', headers: { ...headers, Cookie: cookie }, body: JSON.stringify(body) })
assert.equal((await call('register', input)).status, 201)
assert.equal((await call('register', { ...input, username: '!' })).status, 422)
let login = await call('login', input)
assert.equal(login.status, 200)
let cookie = login.headers.get('set-cookie')
assert.match(cookie, /HttpOnly/i)
assert.match(cookie, /SameSite=Lax/i)
const session = await login.json()
assert.equal(session.refresh_token, undefined)
assert.ok(session.access_token)
cookie = cookie.split(';')[0]
assert.equal((await call('login', { ...input, password: 'wrong' })).status, 401)
assert.equal((await call('register', input)).status, 409)
const refresh = await call('refresh', {}, cookie)
assert.equal(refresh.status, 200)
const refreshed = await refresh.json()
assert.equal(refreshed.refresh_token, undefined)
const me = await fetch(`${gateway}/users/me`, { headers: { Authorization: `Bearer ${refreshed.access_token}` } })
assert.equal((await me.json()).email, input.email)
const account = await fetch(`${base}/account`, { headers: { Cookie: cookie }, redirect: 'manual' })
const html = await account.text()
assert.equal(account.status, 200, html.slice(0, 1000))
assert.ok(html.includes(input.username))
assert.ok(account.headers.get('set-cookie'), 'SSR forwards refreshed cookie')
assert.ok(!html.includes(cookie.split('=')[1]), 'Refresh token absent from HTML')
assert.equal((await fetch(`${base}/account`, { redirect: 'manual' })).status, 302)
assert.equal((await fetch(`${base}/api/session/logout`, { method: 'POST', headers: { Cookie: cookie } })).status, 403)
const logout = await call('logout', {}, cookie)
assert.match(logout.headers.get('set-cookie'), /Max-Age=0/i)
assert.equal((await call('refresh', {})).status, 401)
assert.equal((await call('refresh', {}, 'ai-sana-refresh=invalid')).status, 401)
console.log('PASS: real registration/login/errors, HttpOnly refresh, SSR session restore, guest redirect, CSRF guard, logout')

// Exercise the actual composables outside Nuxt, supplying only its app-scoped primitives.
const require = createRequire(import.meta.url)
const { $fetch } = createRequire(require.resolve('nuxt/package.json'))('ofetch')
function load(relativePath, imports, globals = {}) {
  const source = readFileSync(new URL(relativePath, import.meta.url), 'utf8').replaceAll('import.meta.server', 'false')
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  const exports = {}
  new Function('exports', 'require', ...Object.keys(globals), compiled)(exports, name => imports[name], ...Object.values(globals))
  return exports
}
const errors = load('../app/utils/api-error.ts', {})
const token = { value: session.access_token }
const user = { value: null }
const app = {}
let refreshCount = 0
const sessionFetch = $fetch.create({
  baseURL: base,
  onRequest({ request, options }) {
    if (request.endsWith('/refresh')) refreshCount++
    options.headers.set('Cookie', cookie)
  },
  onResponse({ response }) {
    const nextCookie = response.headers.get('set-cookie')
    if (nextCookie) cookie = nextCookie.split(';')[0]
  }
})
const { useSession } = load('../app/composables/useSession.ts', {}, {
  useNuxtApp: () => app,
  useState: key => key === 'current-user' ? user : token,
  useRequestHeaders: () => ({}),
  $fetch: sessionFetch,
  normalizeApiError: errors.normalizeApiError
})
const { useApi } = load('../app/composables/useApi.ts', {}, {
  useRuntimeConfig: () => ({ public: { apiBase: gateway } }), useSession,
  useRequestFetch: () => $fetch
})
await useSession().login(input)
const encode = value => Buffer.from(JSON.stringify(value)).toString('base64url')
const payload = JSON.parse(Buffer.from(token.value.split('.')[1], 'base64url').toString())
const unsigned = `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode({ ...payload, exp: 1 })}`
token.value = `${unsigned}.${createHmac('sha256', secret).update(unsigned).digest('base64url')}`
const api = useApi().request
const users = await Promise.all([api('/users/me'), api('/users/me'), api('/users/me')])
assert.ok(users.every(value => value.email === input.email))
assert.equal(refreshCount, 1, 'Concurrent 401 responses share a single refresh')
assert.notEqual(token.value.split('.')[1], unsigned.split('.')[1])

let attempts = 0
const { useApi: useRejectingApi } = load('../app/composables/useApi.ts', {}, {
  useRuntimeConfig: () => ({ public: { apiBase: gateway } }), useSession,
  useRequestFetch: () => async () => {
    attempts++
    throw { statusCode: 401, data: { detail: 'Rejected', code: 'unauthorized' } }
  }
})
await assert.rejects(useRejectingApi().request('/users/me'), error => error.status === 401)
assert.equal(attempts, 2, 'At most one replay even if refreshed access is rejected')
assert.equal(token.value, null)
await useSession().logout()
token.value = 'expired'
await assert.rejects(api('/users/me'), error => error.status === 401)
assert.equal(token.value, null)
console.log('PASS: actual useApi/useSession, expired JWT recovery, concurrent refresh deduplication, one replay, expired session cleanup')
