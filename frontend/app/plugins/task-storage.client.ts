import { storedTasksSchema } from '~/utils/task-validation'

const storageKey = 'ai-sana-demo-tasks-v1'

export default defineNuxtPlugin((app) => {
  const { tasks } = useTasks()
  const toast = useToast()
  let warned = false

  // Restore after hydration; own persistence at app scope, not page scope.
  app.hook('app:mounted', () => {
    try {
      const saved = localStorage.getItem(storageKey)
      if (saved) tasks.value = storedTasksSchema.parse(JSON.parse(saved))
    } catch {
      toast.add({ title: 'Не удалось прочитать сохранённые задачи', description: 'Показаны примеры. Данные в хранилище не изменены.', color: 'warning' })
    }

    watch(tasks, (value) => {
      try {
        localStorage.setItem(storageKey, JSON.stringify(value))
        warned = false
      } catch {
        if (!warned) toast.add({ title: 'Изменения доступны только до перезагрузки', description: 'Хранилище браузера недоступно или заполнено.', color: 'warning' })
        warned = true
      }
    }, { deep: true })
  })
})
