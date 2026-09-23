export function useRewardFeedback() {
  const api = useApi()
  const toast = useToast()
  const { t } = useAppI18n()

  async function balance(): Promise<number | null> {
    try {
      const result = await api.request<{ coins: number }>('/catalog/gamification', {
        query: { month: new Date().toISOString().slice(0, 7) }
      })
      return result.coins
    } catch {
      // Optional feedback must never prevent saving or hide a successful action.
      return null
    }
  }

  async function track<T>(work: () => Promise<T>): Promise<T> {
    const owner = api.user.value?.id
    const before = await balance()
    const result = await work()
    const after = await balance()
    if (owner === api.user.value?.id && before !== null && after !== null && after > before) {
      toast.add({ title: t('rewards.earned', { count: after - before }), description: t('rewards.separate'), icon: 'i-lucide-coins', color: 'success' })
    }
    return result
  }

  return { track }
}
