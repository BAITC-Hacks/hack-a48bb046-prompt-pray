import * as z from 'zod'

export function isWebUrl(value: string) {
  try {
    return ['http:', 'https:'].includes(new URL(value).protocol)
  } catch {
    return false
  }
}

export const proposalSchema = z.object({
  team: z.string().trim().min(2, 'Укажите название команды.').max(120),
  idea: z.string().trim().min(20, 'Добавьте подробностей: минимум 20 символов.').max(1600),
  plan: z.string().trim().min(20, 'Добавьте план из нескольких шагов.').max(2400),
  link: z.string().trim().refine(value => !value || isWebUrl(value), 'Укажите адрес, начиная с https:// или http://')
})

export const storedTasksSchema = z.array(z.object({
  id: z.string().min(1),
  title: z.string(),
  brief: z.string(),
  status: z.enum(['draft', 'published']),
  context: z.string(),
  data: z.string(),
  outcome: z.string(),
  success: z.string(),
  constraints: z.string(),
  users: z.string(),
  business: z.string(),
  questions: z.array(z.object({ id: z.string(), question: z.string(), answer: z.string() })),
  proposals: z.array(z.object({
    id: z.string(), team: z.string(), idea: z.string(), plan: z.string(),
    link: z.string(), createdAt: z.iso.datetime()
  })),
  selectedProposalIds: z.array(z.string()),
  createdAt: z.iso.datetime(),
  updatedAt: z.iso.datetime()
}))
