export default defineNuxtRouteMiddleware(async (to) => {
  return useAuthAvailability().check(to.fullPath)
})
