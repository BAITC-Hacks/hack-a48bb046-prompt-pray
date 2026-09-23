import type { ApiErrorPayload } from '../types/api'

export class ApiError extends Error implements ApiErrorPayload {
  readonly detail: ApiErrorPayload['detail']
  readonly code: string
  readonly status: number

  constructor(payload: ApiErrorPayload, status = 0) {
    super(typeof payload.detail === 'string' ? payload.detail : 'Проверьте заполнение полей')
    this.name = 'ApiError'
    this.detail = payload.detail
    this.code = payload.code
    this.status = status
  }

  toJSON(): ApiErrorPayload {
    return { detail: this.detail, code: this.code }
  }
}

export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error

  const failure = error as { data?: Partial<ApiErrorPayload>, status?: number, statusCode?: number } | null
  const status = failure?.status ?? failure?.statusCode ?? 0
  const data = failure?.data
  const detail = typeof data?.detail === 'string' || Array.isArray(data?.detail)
    ? data.detail
    : status ? 'Не удалось выполнить запрос' : 'Не удалось связаться с сервером'
  const code = typeof data?.code === 'string'
    ? data.code
    : status === 422 ? 'validation_error' : status ? 'http_error' : 'network_error'

  return new ApiError({ detail, code }, status)
}
