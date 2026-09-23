import type { H3Event } from 'h3'

export function isAllowedRequestOrigin(event: H3Event): boolean {
  if (getHeader(event, 'sec-fetch-site') === 'cross-site') return false
  const origin = getHeader(event, 'origin')
  // Internal SSR requests and non-browser API clients may omit Origin.
  if (!origin) return true

  const config = useRuntimeConfig(event)
  const trustProxy = config.trustProxyHeaders === true
  const expected = config.appOrigin
    ? new URL(config.appOrigin).origin
    : getRequestURL(event, {
      xForwardedHost: trustProxy,
      xForwardedProto: trustProxy
    }).origin
  return origin === expected
}
