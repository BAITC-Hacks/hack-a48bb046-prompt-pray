// Run after npm run build. Uses its own servers; existing backend processes are untouched.
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { createServer } from 'node:http'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'

test('production SSR survives an upstream outage and recovers; proxy origin remains enforced', { timeout: 90000 }, async () => {
  let upstreamStatus = 503
  const upstream = createServer((req, res) => {
    res.writeHead(upstreamStatus, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(upstreamStatus === 200
      ? { id: 'test-user', username: 'Availability Test', email: 'test@example.com', role: 'business' }
      : { detail: 'Service unavailable', code: 'upstream_unavailable' }))
  })
  upstream.listen(0, '127.0.0.1')
  await once(upstream, 'listening')
  const portProbe = createServer()
  portProbe.listen(0, '127.0.0.1')
  await once(portProbe, 'listening')
  const port = portProbe.address().port
  await new Promise(resolve => portProbe.close(resolve))
  const server = spawn(process.execPath, ['.output/server/index.mjs'], {
    cwd: fileURLToPath(new URL('..', import.meta.url)), windowsHide: true,
    env: { ...process.env, NODE_ENV: 'production', NITRO_HOST: '127.0.0.1', NITRO_PORT: String(port),
      NUXT_GATEWAY_URL: `http://127.0.0.1:${upstream.address().port}`,
      NUXT_APP_ORIGIN: 'https://tasks.example.com' },
    stdio: ['ignore', 'pipe', 'pipe']
  })
  let logs = ''
  server.stdout.on('data', (data) => {
    logs = (logs + data).slice(-4000)
  })
  server.stderr.on('data', (data) => {
    logs = (logs + data).slice(-4000)
  })
  const base = `http://127.0.0.1:${port}`
  try {
    let ready = false
    for (let attempt = 0; attempt < 100; attempt++) {
      assert.equal(server.exitCode, null, logs)
      try {
        const response = await fetch(`${base}/login`, { signal: AbortSignal.timeout(2000) })
        if (response.status === 200) {
          ready = true
          break
        }
      } catch { /* wait for startup */ }
      await new Promise(resolve => setTimeout(resolve, 200))
    }
    assert.ok(ready, logs)
    const account = await fetch(`${base}/account`, { redirect: 'manual' })
    const html = await account.text()
    assert.equal(account.status, 200, html.slice(0, 1000))
    assert.match(html, /Не удалось проверить сессию/)
    assert.match(html, /Попробовать снова/)
    assert.equal((await fetch(`${base}/catalog`)).status, 200)

    const post = origin => fetch(`${base}/api/gateway/catalog/drafts`, {
      method: 'POST', headers: { 'Origin': origin, 'Content-Type': 'application/json' }, body: '{}'
    })
    assert.equal((await post('https://tasks.example.com')).status, 503)
    assert.equal((await post('https://attacker.example')).status, 403)
    upstreamStatus = 200
    const restored = await fetch(`${base}/account`, { redirect: 'manual' })
    const restoredHtml = await restored.text()
    assert.equal(restored.status, 200)
    assert.match(restoredHtml, /Availability Test/)
    assert.doesNotMatch(restoredHtml, /Не удалось проверить сессию/)
    upstreamStatus = 401
    const expired = await fetch(`${base}/account`, { redirect: 'manual' })
    assert.equal(expired.status, 302)
    assert.match(expired.headers.get('location'), /^\/login\?redirect=/)
  } finally {
    server.kill()
    if (server.exitCode === null) await once(server, 'exit')
    upstream.closeAllConnections()
    await new Promise(resolve => upstream.close(resolve))
  }
})
