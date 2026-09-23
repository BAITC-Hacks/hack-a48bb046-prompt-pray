import type { FollowUpQuestion, Proposal, TaskEntry } from '../../shared/types/tasks'

import { makeDemoTasks } from '../data/demo-tasks'
import { proposalSchema } from '~/utils/task-validation'

function makeQuestions(brief: string): FollowUpQuestion[] {
  const normalized = brief.toLowerCase()
  const topics = [
    { keys: ['клиент', 'пользовател', 'посетител', 'студент', 'команд'], question: 'Кто будет пользоваться результатом и какая у него основная потребность?' },
    { keys: ['данн', 'файл', 'таблиц', 'материал', 'отчёт', 'отчет'], question: 'Какие исходные данные и материалы уже доступны команде?' },
    { keys: ['срок', 'недел', 'месяц', 'семестр', 'дат'], question: 'К какому сроку нужен результат и что должно быть готово первым?' },
    { keys: ['результат', 'сделать', 'создать', 'сайт', 'приложен', 'система'], question: 'Что конкретно вы хотите получить по завершении работы?' },
    { keys: ['бизнес', 'продаж', 'доход', 'врем', 'эконом', 'запис'], question: 'Какую рабочую или бизнес-задачу должен решить этот результат?' }
  ]
  const matched = topics.filter(topic => topic.keys.some(key => normalized.includes(key))).map(topic => topic.question)
  const fallback = [
    'Кто будет пользоваться результатом?',
    'Какие материалы и данные можно предоставить команде?',
    'По каким признакам вы поймёте, что решение оказалось полезным?'
  ]
  return [...matched, ...fallback].slice(0, 3).map(question => ({ id: crypto.randomUUID(), question, answer: '' }))
}

export function useTasks() {
  const tasks = useState<TaskEntry[]>('demo:tasks', makeDemoTasks)

  function save(task: TaskEntry) {
    task.updatedAt = new Date().toISOString()
    const index = tasks.value.findIndex(item => item.id === task.id)
    if (index < 0) tasks.value.unshift(task)
    else tasks.value[index] = { ...task }
    return task
  }

  function createDraft(brief: string) {
    const now = new Date().toISOString()
    const task: TaskEntry = {
      id: crypto.randomUUID(),
      title: brief.trim().split(/[.!?\n]/)[0]?.slice(0, 80) || 'Новая задача',
      brief: brief.trim(), status: 'draft', questions: makeQuestions(brief),
      proposals: [], selectedProposalIds: [],
      context: brief.trim(), data: '', outcome: '', success: '', constraints: '', users: '', business: '',
      createdAt: now, updatedAt: now
    }
    return save(task)
  }

  function byId(id: string) {
    return tasks.value.find(task => task.id === id)
  }

  function addProposal(task: TaskEntry, proposal: Omit<Proposal, 'id' | 'createdAt'>) {
    if (task.status !== 'published') throw new Error('Отклики доступны только для опубликованных задач.')
    const data = proposalSchema.parse(proposal)
    task.proposals.unshift({ ...data, id: crypto.randomUUID(), createdAt: new Date().toISOString() })
    save(task)
  }

  return { tasks, createDraft, byId, save, addProposal }
}
