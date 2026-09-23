import type { AuthUser } from '../../shared/types/auth'

export default defineNuxtRouteMiddleware(async (to) => {
  const session = useSession()
  const api = useApi()
  try {
    if (!session.token.value) await session.refresh()
    session.user.value = await api<AuthUser>('/users/me')
  } catch (error) {
    const failure = normalizeApiError(error)
    if (failure.status === 401 || failure.status === 403) {
      session.clear()
      return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
    }
    throw createError({ statusCode: 503, statusMessage: 'Сервис авторизации недоступен. Попробуйте позже.' })
  }
})
