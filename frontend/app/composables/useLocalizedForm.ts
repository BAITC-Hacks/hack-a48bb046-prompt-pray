import type { FormError } from '@nuxt/ui'

type LocalizedForm = {
  getErrors: () => FormError[]
  setErrors: (errors: FormError[]) => void
  validate: (options: { silent: true }) => Promise<unknown>
}

// Revalidate only fields already showing errors; preserve input and untouched fields.
export function useLocalizedForm(getForm: () => LocalizedForm | null | undefined) {
  const { locale } = useAppI18n()
  watch(locale, async () => {
    await nextTick()
    const form = getForm()
    const names = new Set(form?.getErrors().map(error => error.name))
    if (form && names.size) {
      await form.validate({ silent: true })
      form.setErrors(form.getErrors().filter(error => names.has(error.name)))
    }
  })
}
