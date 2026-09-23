import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'

// Use a disposable backend database: this test creates accounts and tasks.
const base = process.env.AUTH_TEST_FRONTEND || 'http://127.0.0.1:3000'
async function call(path, { token, cookie, body, method = 'GET', status = 200 } = {}) {
  const response = await fetch(`${base}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json', 'X-Requested-With': 'AI-Sana',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(cookie ? { Cookie: cookie } : {})
    },
    body: body === undefined ? undefined : JSON.stringify(body), redirect: 'manual'
  })
  const text = await response.text()
  assert.equal(response.status, status, `${path}: ${text.slice(0, 500)}`)
  return { response, data: text ? JSON.parse(text) : null }
}
async function account(role) {
  const username = `it_${randomUUID().replaceAll('-', '').slice(0, 20)}`
  const input = { username, email: `${username}@example.com`, password: 'Test-password-123!', role }
  await call('/api/session/register', { method: 'POST', body: input, status: 201 })
  const { response, data } = await call('/api/session/login', { method: 'POST', body: input })
  assert.equal(data.refresh_token, undefined)
  return { token: data.access_token, cookie: response.headers.get('set-cookie').split(';')[0] }
}
const owner = await account('business')
const student = await account('student')
const root = '/api/gateway/catalog'
const { data: draft } = await call(`${root}/drafts`, { ...owner, method: 'POST', body: { description: 'Integration test: sales report' }, status: 201 })
assert.equal(draft.card_id, null)
// AI generation is covered by the service tests with a controlled provider.
const { data: card } = await call(`${root}/drafts/${draft.id}/card`, { ...owner, method: 'POST', body: { title: 'Integration report' }, status: 201 })
const task = `${root}/tasks/${card.id}`
assert.equal(card.rating.total, 20)
const { data: drafts } = await call(`${root}/drafts`, owner)
assert.equal(drafts.find(item => item.id === draft.id).card_id, card.id)
const page = await fetch(`${base}/account`, { headers: { Cookie: owner.cookie }, redirect: 'manual' })
assert.equal(page.status, 200)
assert.ok((await page.text()).includes(`/tasks/${card.id}`), 'SSR account links to saved card')
const resume = await fetch(`${base}/tasks/new?draft=${draft.id}`, { headers: { Cookie: owner.cookie }, redirect: 'manual' })
assert.equal(resume.status, 302, (await resume.text()).slice(0, 3000))
assert.equal(resume.headers.get('location'), `/tasks/${card.id}`)
await call(`${task}/confirm`, { ...owner, method: 'POST', body: { confirmed: true } })
await call(`${task}/publish`, { ...owner, method: 'POST' })
const { data: catalog } = await call(root)
assert.ok(catalog.items.some(item => item.task_id === card.id))
await call(task)
const { data: proposal } = await call(`${task}/proposals`, { ...student, method: 'POST', body: { team_id: randomUUID(), idea: 'Dashboard', plan: 'Prepare and test' }, status: 201 })
assert.deepEqual((await call(`${task}/decisions`, owner)).data, [])
await call(`${task}/decisions`, { ...student, method: 'POST', body: { selected_proposal_ids: [proposal.id] }, status: 403 })
const { data: decision } = await call(`${task}/decisions`, { ...owner, method: 'POST', body: { selected_proposal_ids: [proposal.id] }, status: 201 })
assert.deepEqual(decision.selected_proposal_ids, [proposal.id])
await call(task, { ...owner, method: 'PATCH', body: { users: 'Sales team' } })
await call(task, { status: 401 })
assert.equal((await call(task, owner)).data.rating.total, 30)
console.log('PASS: Nuxt proxy → gateway → database; SSR draft recovery, publication, low-rating proposals, manual selection, edit unpublishes')
