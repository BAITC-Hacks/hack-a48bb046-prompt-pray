import type { User } from '~/types/api'

export default defineNuxtRouteMiddleware(async (to) => {
  const api = useApi()
  try {
    api.user.value = await api.request<User>('/users/me')
  } catch {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }
})
