export const cardFields = [
  { key: 'context', label: 'Контекст и потребность', points: 20 },
  { key: 'data', label: 'Данные и материалы', points: 20 },
  { key: 'expected_result', label: 'Ожидаемый результат', points: 15 },
  { key: 'success_criteria', label: 'Критерии успеха', points: 15 },
  { key: 'constraints', label: 'Ограничения', points: 10 },
  { key: 'users', label: 'Пользователи', points: 10 },
  { key: 'business_contact', label: 'Связь с бизнесом', points: 10 }
] as const
export type CardField = typeof cardFields[number]['key']
export type ReadinessCode = 'draft' | 'working' | 'ready' | 'priority'
export interface Draft { id: string, description: string, card_id: string | null }
export interface Question { id: string, question: string, field: CardField, answer: string | null, position: number }
export type Card = Record<CardField, string | null> & {
  id: string
  title: string
  business_id: string
  confirmed_at: string | null
  rating: (Record<CardField, number> & { total: number, readiness: string, readiness_code: ReadinessCode }) | null
}
export interface CatalogEntry { task_id: string, task: Card, published_at: string }
export interface CatalogPage { items: CatalogEntry[], total: number, limit: number, offset: number }
export interface Proposal { id: string, team_id: string, user_id: string, idea: string, plan: string, prototype_url: string | null }
export interface Decision { id: string, selected_proposal_ids: string[], comment: string | null }
