import assert from 'node:assert/strict'
import { test } from 'node:test'
import { storedTasksSchema, proposalSchema, isWebUrl } from '../app/utils/task-validation.ts'
import { taskFields, taskRating, readiness } from '../app/utils/task-rating.ts'
import { makeDemoTasks } from '../app/data/demo-tasks.ts'

test('storage accepts demo data and rejects malformed nested records', () => {
  const tasks = makeDemoTasks()
  assert.equal(storedTasksSchema.parse(tasks).length, 2)
  assert.equal(storedTasksSchema.safeParse({}).success, false)
  tasks[0].questions = [{ id: 'bad', question: 'Question', answer: null }]
  assert.equal(storedTasksSchema.safeParse(tasks).success, false)
})

test('prototype links permit web URLs only, including stored legacy links', () => {
  for (const value of ['javascript:alert(1)', 'data:text/html,test', 'file:///tmp/test', '//example.com']) {
    assert.equal(isWebUrl(value), false)
    assert.equal(proposalSchema.safeParse({ team: 'Team', idea: 'A sufficiently detailed idea', plan: 'A sufficiently detailed plan', link: value }).success, false)
  }
  assert.equal(isWebUrl('https://example.com/prototype'), true)
  assert.equal(proposalSchema.parse({ team: ' Team ', idea: 'A sufficiently detailed idea', plan: 'A sufficiently detailed plan', link: '' }).team, 'Team')
})

test('rating weights total 100 and readiness boundaries match the product rules', () => {
  const answers = Object.fromEntries(taskFields.map(field => [field.key, '']))
  assert.equal(taskRating(answers), 0)
  for (const field of taskFields) {
    assert.equal(taskRating({ ...answers, [field.key]: 'Detailed answer for the task' }), field.points)
  }
  assert.equal(taskRating(Object.fromEntries(taskFields.map(field => [field.key, 'Detailed answer for the task']))), 100)
  for (const [score, label] of [[39, 'Черновик'], [40, 'Рабочая'], [69, 'Рабочая'], [70, 'Готовая'], [89, 'Готовая'], [90, 'Приоритетная']]) {
    assert.equal(readiness(score).label, label)
  }
})
