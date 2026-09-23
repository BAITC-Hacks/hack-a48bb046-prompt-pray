export function useApiMessages() {
  const { t, te } = useAppI18n()

  function errorMessage(error: unknown) {
    const failure = error as { code?: string, data?: { code?: string, data?: { code?: string } } } | null
    const code = failure?.code || failure?.data?.data?.code || failure?.data?.code
    const key = `errors.${code}`
    return code && te(key) ? t(key) : t('errors.generic')
  }

  function fieldErrors(error: unknown): Record<string, string> {
    const failure = error as { fields?: Record<string, string> } | null
    return Object.fromEntries(Object.keys(failure?.fields || {}).map(key => [key, t('validation.invalid')]))
  }

  return { errorMessage, fieldErrors }
}
