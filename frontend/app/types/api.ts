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
