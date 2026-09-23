import type { AccessSession, AuthUser, LoginInput, RegisterInput } from '../../shared/types/auth'
import type { User } from '~/types/api'

// One refresh per app/SSR request, including concurrent requests from different components.
const refreshes = new WeakMap<object, Promise<void>>()

export function useSession() {
  const app = useNuxtApp()
  const token = useState<string | null>('access-token', () => null)
  const user = useState<User | null>('current-user', () => null)
  const requestHeaders = useRequestHeaders(['cookie'])
  const responseCookies = import.meta.server ? useResponseHeader('set-cookie') : undefined

  function clear() {
    token.value = null
    user.value = null
  }

  async function request<T>(action: string, body?: LoginInput | RegisterInput) {
    try {
      const response = await $fetch.raw<T>(`/api/session/${action}`, {
        method: 'POST', body, headers: { ...requestHeaders, 'X-Requested-With': 'AI-Sana' }, retry: 0
      })
      if (responseCookies) responseCookies.value = response.headers.getSetCookie()
      return response._data as T
    } catch (error) {
      // Forward cookie deletion as well as rotation during SSR.
      const failure = error as { response?: Response }
      if (responseCookies && failure.response) responseCookies.value = failure.response.headers.getSetCookie()
      throw normalizeApiError(error)
    }
  }

  function refresh() {
    let pending = refreshes.get(app)
    if (!pending) {
      pending = request<AccessSession>('refresh').then((session) => {
        token.value = session.access_token
      }).catch((error) => {
        if (error.status === 401 || error.status === 403) clear()
        throw error
      }).finally(() => refreshes.delete(app))
      refreshes.set(app, pending)
    }
    return pending
  }

  async function login(input: LoginInput) {
    const session = await request<AccessSession>('login', input)
    token.value = session.access_token
    user.value = null
  }

  async function logout() {
    // Let any in-flight refresh finish before deleting its cookie and state.
    await refreshes.get(app)?.catch(() => {})
    await request('logout')
    clear()
  }

  return { token, user, clear, refresh, login, logout, register: (input: RegisterInput) => request<AuthUser>('register', input) }
}
