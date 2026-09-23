import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { test } from 'node:test'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const h3 = createRequire(require.resolve('nuxt/package.json'))('h3')

function load(path, globals) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8')
  const compiled = ts.transpileModule(source.replaceAll('import.meta.dev', 'true'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
  }).outputText
  const exports = {}
  new Function('exports', ...Object.keys(globals), compiled)(exports, ...Object.values(globals))
  return exports.default || exports.isAllowedRequestOrigin
}

test('both proxies forward the real visitor, preserve SSR context, and discard spoofed IP headers', async () => {
  const config = { gatewayUrl: 'http://gateway', trustProxyHeaders: false }
  const globals = {
    ...h3,
    useRuntimeConfig: () => config,
    setResponseStatus: () => {},
    setResponseHeader: () => {},
    readBody: async () => ({ email: 'test@example.com', password: 'password' })
  }
  const middleware = load('../server/middleware/client-ip.ts', globals)
  globals.isAllowedRequestOrigin = load('../server/utils/request-origin.ts', globals)
  const sent = []
  const gateway = load('../server/api/gateway/[...path].ts', {
    ...globals,
    $fetch: { raw: async (url, options) => {
      sent.push(options.headers)
      return { status: 200, _data: {} }
    } }
  })
  const session = load('../server/api/session/[action].post.ts', {
    ...globals,
    $fetch: { create: options => async () => {
      sent.push(options.headers)
      return {}
    } }
  })

  for (const ip of ['192.0.2.1', '192.0.2.2']) {
    const event = {
      context: { params: { path: 'catalog', action: 'register' } },
      node: { req: { method: 'GET', url: '/', socket: { remoteAddress: ip }, headers: {
        'x-forwarded-for': '198.51.100.99', 'x-requested-with': 'AI-Sana'
      } } }
    }
    await middleware(event)
    await gateway(event)
    assert.equal(sent.at(-1)['X-Forwarded-For'], ip)
    // An internal SSR request has context but no original TCP socket.
    event.node.req.socket = {}
    await middleware(event)
    await session(event)
    assert.equal(sent.at(-1)['X-Forwarded-For'], ip)
  }
})

test('origin checks support HTTPS proxies without trusting spoofed forwarding headers', async () => {
  const config = { gatewayUrl: 'http://gateway', appOrigin: '', trustProxyHeaders: false }
  const globals = { ...h3, useRuntimeConfig: () => config }
  const allowed = load('../server/utils/request-origin.ts', globals)
  const event = {
    path: '/api/gateway/catalog/drafts',
    context: { params: { path: 'catalog/drafts', action: 'login' } },
    node: { req: { method: 'POST', socket: {}, headers: {
      'host': '127.0.0.1:3000', 'origin': 'https://tasks.example.com',
      'x-forwarded-host': 'tasks.example.com', 'x-forwarded-proto': 'https',
      'x-requested-with': 'AI-Sana'
    } } }
  }
  assert.equal(allowed(event), false)
  config.trustProxyHeaders = true
  assert.equal(allowed(event), true)
  config.trustProxyHeaders = false
  config.appOrigin = 'https://tasks.example.com'
  assert.equal(allowed(event), true)
  event.node.req.headers.origin = 'https://attacker.example'
  assert.equal(allowed(event), false)

  let forwarded = false
  const routes = {
    ...globals, isAllowedRequestOrigin: allowed,
    $fetch: { raw: async () => { forwarded = true } },
    setResponseHeader: () => {}, setResponseStatus: () => {}
  }
  const gateway = load('../server/api/gateway/[...path].ts', routes)
  const session = load('../server/api/session/[action].post.ts', routes)
  await assert.rejects(() => gateway(event), error => error.statusCode === 403)
  assert.equal((await session(event)).code, 'forbidden')
  assert.equal(forwarded, false)

  delete event.node.req.headers.origin
  assert.equal(allowed(event), true, 'internal SSR without Origin remains supported')
  event.node.req.headers['sec-fetch-site'] = 'cross-site'
  assert.equal(allowed(event), false)
  delete event.node.req.headers['sec-fetch-site']
  config.appOrigin = ''
  event.node.req.headers.origin = 'http://127.0.0.1:3000'
  assert.equal(allowed(event), true, 'local HTTP ignores untrusted forwarded protocol')
})
