export type TaskStatus = 'draft' | 'published'

export interface TaskAnswers {
  context: string
  data: string
  outcome: string
  success: string
  constraints: string
  users: string
  business: string
}
export interface FollowUpQuestion {
  id: string
  question: string
  answer: string
}

export interface Proposal {
  id: string
  team: string
  idea: string
  plan: string
  link: string
  createdAt: string
}

export interface TaskEntry extends TaskAnswers {
  id: string
  title: string
  brief: string
  status: TaskStatus
  questions: FollowUpQuestion[]
  proposals: Proposal[]
  selectedProposalIds: string[]
  createdAt: string
  updatedAt: string
}
