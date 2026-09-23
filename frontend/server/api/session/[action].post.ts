import type { AccessSession, AuthUser } from '../../../shared/types/auth'

const cookieName = 'ai-sana-refresh'
const cookieOptions = {
  httpOnly: true,
  secure: !import.meta.dev,
  sameSite: 'lax' as const,
  path: '/'
}

export default defineEventHandler(async (event) => {
  setResponseHeader(event, 'Cache-Control', 'no-store')
  // A custom header prevents cross-origin forms from mutating the session.
  // No CORS permissions are granted on these same-origin Nitro routes.
  if (getHeader(event, 'x-requested-with') !== 'AI-Sana'
    || !isAllowedRequestOrigin(event)) {
    setResponseStatus(event, 403)
    return { detail: 'Запрос с другого сайта запрещён', code: 'forbidden' }
  }

  const action = getRouterParam(event, 'action')
  if (!action || !['login', 'register', 'refresh', 'logout'].includes(action)) {
    setResponseStatus(event, 404)
    return { detail: 'Unknown session route', code: 'not_found' }
  }
  if (action === 'logout') {
    deleteCookie(event, cookieName, cookieOptions)
    return { ok: true }
  }

  const refreshToken = action === 'refresh' ? getCookie(event, cookieName) : undefined
  if (action === 'refresh' && !refreshToken) {
    setResponseStatus(event, 401)
    return { detail: 'Войдите в аккаунт', code: 'unauthorized' }
  }

  const body = action === 'refresh' ? { refresh_token: refreshToken } : await readBody(event)
  try {
    const gateway = $fetch.create({
      baseURL: useRuntimeConfig(event).gatewayUrl + '/api/v1',
      method: 'POST',
      retry: 0,
      timeout: 15000,
      headers: getRequestIP(event) ? { 'X-Forwarded-For': getRequestIP(event)! } : undefined
    })
    if (action === 'register') {
      const user = await gateway<AuthUser>('/auth/register', { body })
      setResponseStatus(event, 201)
      return user
    }
    const result = await gateway<AccessSession & { refresh_token: string }>(`/auth/${action}`, { body })
    setCookie(event, cookieName, result.refresh_token, { ...cookieOptions, maxAge: 7 * 24 * 60 * 60 })
    // The refresh token never appears in browser-readable response data.
    return { access_token: result.access_token, token_type: result.token_type, expires_in: result.expires_in }
  } catch (error) {
    const failure = error as { status?: number, data?: { detail?: unknown, code?: string } }
    const status = failure.status || 502
    if (action === 'refresh' && (status === 401 || status === 403)) {
      deleteCookie(event, cookieName, cookieOptions)
    }
    setResponseStatus(event, status)
    return failure.data?.detail
      ? { detail: failure.data.detail, code: failure.data.code ?? (status === 422 ? 'validation_error' : 'http_error') }
      : { detail: 'Сервис авторизации недоступен. Попробуйте ещё раз.', code: 'auth_unavailable' }
  }
})
