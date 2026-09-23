import { ApiError, normalizeApiError } from '../utils/api-error'

export function useApi() {
  const config = useRuntimeConfig()
  const session = useSession()
  const client = $fetch.create({
    baseURL: config.public.apiBase,
    retry: 0,
    timeout: 15000
  })

  return async function api<T>(path: string, options: Omit<NonNullable<Parameters<typeof client>[1]>, 'baseURL'> = {}) {
    // Keep credentials on the configured gateway, even if a caller passes a URL.
    if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\') || path.includes('..')) {
      throw new ApiError({ detail: 'Ожидался относительный путь API, например /users/me', code: 'invalid_api_path' })
    }

    const initialToken = session.token.value
    const send = () => {
      const headers = new Headers(options.headers)
      if (session.token.value) headers.set('Authorization', `Bearer ${session.token.value}`)
      return client<T>(path, { ...options, baseURL: config.public.apiBase, headers })
    }
    try {
      return await send()
    } catch (error) {
      const failure = normalizeApiError(error)
      if (failure.status !== 401 || path.startsWith('/auth/')) throw failure
      // A concurrent request may already have refreshed this access token.
      if (!session.token.value || session.token.value === initialToken) await session.refresh()
      try {
        return await send()
      } catch (retryError) {
        const finalError = normalizeApiError(retryError)
        if (finalError.status === 401) session.clear()
        throw finalError
      }
    }
  }
}
