export default defineNuxtRouteMiddleware((to, from) => {
  if (from.query.t === '1' && to.query.t === undefined) {
    return navigateTo({ path: to.path, query: { ...to.query, t: '1' }, hash: to.hash }, { replace: true })
  }
})
