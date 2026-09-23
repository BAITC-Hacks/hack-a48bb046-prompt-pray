import type { User } from '~/types/api'

export function useAuthAvailability() {
  const app = useNuxtApp()
  const api = useApi()
  const failure = useState<{ path: string, code: string } | null>('auth-availability', () => null)
  const pending = useState('auth-check-pending', () => false)

  async function check(path: string) {
    if (pending.value) return
    pending.value = true
    try {
      api.user.value = await api.request<User>('/users/me')
      failure.value = null
    } catch (cause) {
      const error = cause as { status?: number, code?: string }
      if (error.status === 401) {
        failure.value = null
        const template = new URL(path, 'http://localhost').searchParams.get('t') === '1'
        return app.runWithContext(() => navigateTo({ path: '/login', query: { redirect: path, ...(template ? { t: '1' } : {}) } }))
      }
      // A service outage is not an expired session. Keep existing user/form state.
      failure.value = { path, code: error.code || 'upstream_unavailable' }
    } finally {
      pending.value = false
    }
  }

  return { failure, pending, check, user: api.user }
}
