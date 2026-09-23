import type { ApiError } from '~/types/api'

export function useApi() {
  const session = useSession()
  const config = useRuntimeConfig()
  const fetcher = useRequestFetch()
  const { token, user, refresh } = session
  const pendingRequests = useState('api-pending-requests', () => 0)

  async function request<T>(path: string, options: {
    method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
    body?: Record<string, unknown>
    query?: Record<string, string | number>
  } = {}, retry = true): Promise<T> {
    if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\') || path.includes('..')) {
      throw normalize({ statusCode: 400, data: { detail: 'Ожидался относительный путь API', code: 'invalid_api_path' } })
    }
    const initialToken = token.value
    const auth = path.startsWith('/auth/')
    pendingRequests.value++
    try {
      if (path === '/auth/logout') {
        await session.logout()
        return { ok: true } as T
      }
      return await fetcher(auth ? path.replace('/auth/', '/') : path, {
        baseURL: auth ? '/api/session' : config.public.apiBase,
        ...options,
        retry: 0,
        timeout: /\/(questions|rating-advice|analysis|title|similar|next-question)$/.test(path) && options.method === 'POST' ? 90000 : 20000,
        headers: auth ? { 'X-Requested-With': 'AI-Sana' } : token.value ? { Authorization: `Bearer ${token.value}` } : undefined
      }) as T
    } catch (cause) {
      const response = cause as { statusCode?: number, data?: { detail?: unknown, code?: string, data?: { detail?: unknown, code?: string } } }
      if (response.statusCode === 401 && retry && !path.startsWith('/auth/')) {
        try {
          if (!token.value || token.value === initialToken) await refresh()
        } catch (error) {
          const failure = error as { status: number, detail: string, code: string }
          throw normalize({ statusCode: failure.status, data: failure })
        }
        return request<T>(path, options, false)
      }
      if (response.statusCode === 401 && !auth) session.clear()
      throw normalize(response)
    } finally {
      pendingRequests.value--
    }
  }

  function normalize(response: { statusCode?: number, data?: { detail?: unknown, code?: string, data?: { detail?: unknown, code?: string } } }): ApiError {
    const data = response.data?.data || response.data
    const fields: Record<string, string> = {}
    if (Array.isArray(data?.detail)) {
      for (const issue of data.detail) fields[issue.loc.slice(1).join('.')] = issue.msg
    }
    const detail = typeof data?.detail === 'string' ? data.detail : Object.values(fields).join('; ') || 'Не удалось выполнить запрос'
    let fallback = 'request_failed'
    if (!response.statusCode) fallback = 'network_error'
    else if (response.statusCode === 422) fallback = 'validation_error'
    else if (response.statusCode === 504) fallback = 'upstream_timeout'
    else if (response.statusCode >= 500) fallback = 'upstream_unavailable'
    return Object.assign(new Error(detail), { detail, code: data?.code || fallback, status: response.statusCode || 0, fields })
  }

  return { request, refresh, token, user, pendingRequests }
}
