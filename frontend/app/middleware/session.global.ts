// Resolve the cookie-backed session before layouts render. Restoring it in a
// page's async setup is too late: the SSR header may already contain guest links.
export default defineNuxtRouteMiddleware(async () => {
  if (!import.meta.server) return
  const cookie = useRequestHeaders(['cookie']).cookie || ''
  if (!/(?:^|;\s*)ai-sana-refresh=/.test(cookie)) return
  const session = useSession()
  if (session.token.value) return
  try {
    await session.refresh()
  } catch {
    // Public pages remain available; auth middleware handles protected pages.
  }
})
