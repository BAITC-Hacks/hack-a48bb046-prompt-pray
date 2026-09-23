export function authRedirect(value: unknown): string {
  // Only local routes; never allow an open redirect after login.
  return typeof value === 'string' && /^\/(?!\/)/.test(value)
    && !/[\\\s]/.test(value) && !/^\/(login|signup)([/?#]|$)/.test(value)
    ? value
    : '/account'
}
