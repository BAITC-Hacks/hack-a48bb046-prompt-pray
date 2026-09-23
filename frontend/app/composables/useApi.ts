import type { AccessToken, ApiError, User } from '~/types/api'

const refreshing = new WeakMap<object, Promise<void>>()

export function useApi() {
  const app = useNuxtApp()
  const config = useRuntimeConfig()
  const fetcher = useRequestFetch()
  const token = useState<string | null>('access-token', () => null)
  const user = useState<User | null>('current-user', () => null)
  const responseCookies = import.meta.server ? useResponseHeader('set-cookie') : null
  const refreshHeaders = import.meta.server ? useRequestHeaders(['cookie']) : undefined

  async function refresh() {
    let pending = refreshing.get(app)
    if (!pending) {
      pending = $fetch.raw<AccessToken>('/api/gateway/auth/refresh', { method: 'POST', headers: refreshHeaders })
        .then((result) => {
          token.value = result._data!.access_token
          if (import.meta.server && responseCookies) {
            const cookies = result.headers.getSetCookie()
            if (cookies.length) responseCookies.value = cookies
          }
        })
        .catch((error) => {
          token.value = null
          user.value = null
          throw error
        })
        .finally(() => { refreshing.delete(app) })
      refreshing.set(app, pending)
    }
    await pending
  }

  async function request<T>(path: string, options: {
    method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
    body?: Record<string, unknown>
    query?: Record<string, string | number>
  } = {}, retry = true): Promise<T> {
    try {
      return await fetcher(path, {
        baseURL: path.startsWith('/auth/') ? '/api/gateway' : config.public.apiBase,
        ...options,
        headers: token.value ? { Authorization: `Bearer ${token.value}` } : undefined
      }) as T
    } catch (cause) {
      const response = cause as { statusCode?: number, data?: { detail?: unknown, code?: string, data?: { detail?: unknown, code?: string } } }
      if (response.statusCode === 401 && retry && !path.startsWith('/auth/')) {
        try {
          await refresh()
        } catch {
          throw normalize(response)
        }
        return request<T>(path, options, false)
      }
      throw normalize(response)
    }
  }

  function normalize(response: { statusCode?: number, data?: { detail?: unknown, code?: string, data?: { detail?: unknown, code?: string } } }): ApiError {
    const data = response.data?.data || response.data
    const fields: Record<string, string> = {}
    if (Array.isArray(data?.detail)) {
      for (const issue of data.detail) fields[issue.loc.slice(1).join('.')] = issue.msg
    }
    const detail = typeof data?.detail === 'string' ? data.detail : Object.values(fields).join('; ') || 'Не удалось выполнить запрос'
    return Object.assign(new Error(detail), { detail, code: data?.code || (response.statusCode === 422 ? 'validation_error' : 'request_failed'), status: response.statusCode || 0, fields })
  }

  return { request, refresh, token, user }
}
