export interface User {
  id: string
  username: string
  email: string
  role: 'business' | 'student'
}

export interface AccessToken {
  access_token: string
  token_type: string
}

export interface ApiError extends Error {
  detail: string
  code: string
  status: number
  fields: Record<string, string>
}

export interface ApiValidationIssue {
  loc: (string | number)[]
  msg: string
  type: string
  [key: string]: unknown
}

export interface ApiErrorPayload {
  detail: string | ApiValidationIssue[]
  code: string
}
