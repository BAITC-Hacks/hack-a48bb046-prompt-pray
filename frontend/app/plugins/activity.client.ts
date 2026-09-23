export default defineNuxtPlugin(() => {
  const api = useApi()
  let recorded = ''
  let pending = false
  async function visit() {
    const user = api.user.value
    if (!user || !['business', 'student'].includes(user.role) || document.visibilityState !== 'visible' || pending) return
    const key = `${user.id}:${new Date().toISOString().slice(0, 10)}`
    if (recorded === key) return
    pending = true
    try {
      await api.request('/catalog/gamification/check-in', { method: 'POST' })
      recorded = key
    } catch {
      // Retry on the next visible visit; activity never blocks navigation.
    } finally {
      pending = false
    }
  }
  watch(() => api.user.value?.id, () => void visit(), { immediate: true })
  document.addEventListener('visibilitychange', () => void visit())
  useRouter().afterEach(() => void visit())
  window.setInterval(() => void visit(), 60000)
})
