import type { TaskAnswers } from '../../shared/types/tasks'

export const taskFields: { key: keyof TaskAnswers, label: string, points: number, description: string }[] = [
  { key: 'context', label: 'Контекст и потребность', points: 20, description: 'Что сейчас происходит и что нужно изменить?' },
  { key: 'data', label: 'Данные и материалы', points: 20, description: 'Какие данные, материалы или доступы готовы?' },
  { key: 'outcome', label: 'Ожидаемый результат', points: 15, description: 'Какой результат вы хотите получить?' },
  { key: 'success', label: 'Критерии успеха', points: 15, description: 'Как вы поймёте, что задача выполнена успешно?' },
  { key: 'constraints', label: 'Ограничения', points: 10, description: 'Какие есть сроки, бюджет, правила или ограничения?' },
  { key: 'users', label: 'Пользователи', points: 10, description: 'Кто будет пользоваться результатом?' },
  { key: 'business', label: 'Связь с бизнесом', points: 10, description: 'Какую бизнес-цель поддержит этот проект?' }
]

export function taskRating(task: TaskAnswers) {
  return taskFields.reduce((total, field) => total + (task[field.key].trim().length >= 12 ? field.points : 0), 0)
}

export function readiness(score: number) {
  if (score >= 90) return { label: 'Приоритетная', color: 'success' as const }
  if (score >= 70) return { label: 'Готовая', color: 'primary' as const }
  if (score >= 40) return { label: 'Рабочая', color: 'warning' as const }
  return { label: 'Черновик', color: 'neutral' as const }
}
