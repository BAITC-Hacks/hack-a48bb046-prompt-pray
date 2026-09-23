export default defineEventHandler(async (event) => {
  const path = getRouterParam(event, 'path') || ''
  if (!/^[a-zA-Z0-9_/-]+$/.test(path) || path.includes('..')) throw createError({ statusCode: 400 })
  const method = getMethod(event)
  if (!['GET', 'HEAD'].includes(method)) {
    if (!isAllowedRequestOrigin(event)) throw createError({ statusCode: 403, data: { detail: 'Недопустимый источник запроса', code: 'forbidden' } })
  }
  const cookie = 'ai-sana-refresh'
  const cookieOptions = { httpOnly: true, secure: !import.meta.dev, sameSite: 'lax' as const, path: '/', maxAge: 60 * 60 * 24 * 7 }
  if (path === 'auth/logout' && method === 'POST') {
    deleteCookie(event, cookie, cookieOptions)
    return { ok: true }
  }
  const config = useRuntimeConfig(event)
  let body = ['GET', 'HEAD'].includes(method) ? undefined : await readBody(event)
  if (path === 'auth/refresh') {
    const refreshToken = getCookie(event, cookie)
    if (!refreshToken) throw createError({ statusCode: 401, data: { detail: 'Войдите в аккаунт', code: 'unauthorized' } })
    body = { refresh_token: refreshToken }
  }
  try {
    const response = await $fetch.raw<Record<string, unknown>>(`${config.gatewayUrl}${path === 'healthz' ? '/healthz' : `/api/v1/${path}`}`, {
      method,
      retry: 0,
      timeout: method === 'POST' && /\/(questions|rating-advice|analysis|title|similar|next-question)$/.test(path) ? 80000 : 15000,
      body,
      query: getQuery(event),
      headers: {
        ...(getRequestIP(event) ? { 'X-Forwarded-For': getRequestIP(event)! } : {}),
        ...(getHeader(event, 'authorization') ? { authorization: getHeader(event, 'authorization')! } : {})
      }
    })
    setResponseStatus(event, response.status)
    const result = response._data
    if (!result) return null
    if (path === 'auth/login' || path === 'auth/refresh') {
      if (typeof result.refresh_token === 'string') setCookie(event, cookie, result.refresh_token, cookieOptions)
      delete result.refresh_token
    }
    return result
  } catch (cause) {
    const error = cause as { statusCode?: number, data?: unknown, cause?: { name?: string } }
    if (path === 'auth/refresh' && error.statusCode === 401) deleteCookie(event, cookie, cookieOptions)
    const timedOut = error.cause?.name === 'TimeoutError' || error.cause?.name === 'AbortError'
    throw createError({ statusCode: error.statusCode || (timedOut ? 504 : 502), data: error.data || {
      detail: timedOut ? 'Gateway не ответил вовремя' : 'Gateway недоступен',
      code: timedOut ? 'upstream_timeout' : 'gateway_unavailable'
    } })
  }
})
