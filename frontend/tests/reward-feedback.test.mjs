import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import ts from 'typescript'

const source = ts.transpileModule(readFileSync(new URL('../app/composables/useRewardFeedback.ts', import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
}).outputText

function feedback(balances) {
  const notifications = []
  const user = { value: { id: 'owner' } }
  const exported = {}
  new Function('exports', 'useApi', 'useToast', 'useAppI18n', source)(exported,
    () => ({ user, request: async () => {
      const value = balances.shift()
      if (value instanceof Error) throw value
      return { coins: value }
    } }),
    () => ({ add: value => notifications.push(value) }),
    () => ({ t: (key, args) => args ? `${key}:${args.count}` : key }))
  return { ...exported.useRewardFeedback(), notifications, user }
}

test('toasts reflect actual balance increases and repeated actions earn no toast', async () => {
  const state = feedback([10, 20, 20, 20])
  assert.equal(await state.track(async () => 'saved'), 'saved')
  await state.track(async () => 'saved again')
  assert.equal(state.notifications.length, 1)
  assert.equal(state.notifications[0].title, 'rewards.earned:10')
})

test('failed optional reads never hide a successful save or invent a reward', async () => {
  for (const values of [[new Error('offline'), 30], [10, new Error('offline')]]) {
    const state = feedback(values)
    assert.equal(await state.track(async () => 'saved'), 'saved')
    assert.equal(state.notifications.length, 0)
  }
})

test('failed action and switched account do not show reward notifications', async () => {
  const state = feedback([10, 10, 1000])
  await assert.rejects(state.track(async () => { throw new Error('conflict') }), /conflict/)
  await state.track(async () => { state.user.value = { id: 'other' } })
  assert.equal(state.notifications.length, 0)
})
