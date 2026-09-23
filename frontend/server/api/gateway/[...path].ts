export default defineEventHandler(async (event) => {
  const path = getRouterParam(event, 'path') || ''
  if (!/^[a-zA-Z0-9_/-]+$/.test(path) || path.includes('..')) throw createError({ statusCode: 400 })
  const method = getMethod(event)
  if (!['GET', 'HEAD'].includes(method)) {
    const origin = getHeader(event, 'origin')
    if (origin && origin !== getRequestURL(event).origin) throw createError({ statusCode: 403, data: { detail: 'Недопустимый источник запроса', code: 'forbidden' } })
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
      body,
      query: getQuery(event),
      headers: getHeader(event, 'authorization') ? { authorization: getHeader(event, 'authorization')! } : undefined
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
    const error = cause as { statusCode?: number, data?: unknown }
    if (path === 'auth/refresh' && error.statusCode === 401) deleteCookie(event, cookie, cookieOptions)
    throw createError({ statusCode: error.statusCode || 502, data: error.data || { detail: 'Gateway недоступен', code: 'gateway_unavailable' } })
  }
})
