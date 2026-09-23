export default defineEventHandler((event) => {
  // Context survives internal SSR fetches; HTTP headers cannot override it.
  if (!event.context.clientAddress) {
    event.context.clientAddress = getRequestIP(event, {
      xForwardedFor: useRuntimeConfig(event).trustProxyHeaders === true
    })
  }
})
