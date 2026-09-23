<script setup lang="ts">
import * as z from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { AccessToken, ApiError, User } from '~/types/api'

const { t } = useAppI18n()

definePageMeta({ layout: 'auth' })
const api = useApi()
const { errorMessage } = useApiMessages()
const route = useRoute()
const pending = ref(false)
const error = ref<ApiError | null>(null)
const role = ref<'business' | 'student'>('student')
const signup = false
const fields = computed(() => [
  ...(signup ? [{ name: 'username', type: 'text' as const, label: t('auth.username'), required: true }] : []),
  { name: 'email', type: 'text' as const, label: t('auth.identifier'), required: true },
  { name: 'password', type: 'password' as const, label: t('auth.password'), required: true }
])
const schema = computed(() => z.object({
  username: signup ? z.string({ error: t('validation.required') }).min(3, t('validation.username')).max(50, t('validation.username')).regex(/^[A-Za-z0-9_.-]+$/, t('validation.username')) : z.string({ error: t('validation.required') }).optional(),
  email: z.string({ error: t('validation.identifier') }).trim().min(1, t('validation.identifier')),
  password: z.string({ error: t('validation.required') }).min(signup ? 8 : 1, signup ? t('validation.passwordMin') : t('validation.password')).refine(value => !signup || new TextEncoder().encode(value).length <= 72, t('validation.passwordMax'))
}))
const authForm = useTemplateRef('authForm')
useLocalizedForm(() => authForm.value?.formRef)
useSeoMeta({ title: () => t(signup ? 'auth.signupTitle' : 'auth.loginTitle') })
async function onSubmit(payload: FormSubmitEvent<z.output<typeof schema.value>>) {
  pending.value = true
  error.value = null
  try {
    if (signup) await api.request<User>('/auth/register', { method: 'POST', body: { ...payload.data, role: role.value } })
    const result = await api.request<AccessToken>('/auth/login', { method: 'POST', body: { email: payload.data.email, password: payload.data.password } })
    api.token.value = result.access_token
    api.user.value = await api.request<User>('/users/me')
    const redirect = route.query.redirect
    await navigateTo(typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//') && !redirect.includes('\\') ? redirect : '/account')
  } catch (cause) {
    error.value = cause as ApiError
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <UAlert
      v-if="error"
      color="error"
      :title="errorMessage(error)"
    />
    <UFormField
      v-if="signup"
      :label="t('auth.role')"
    >
      <USelect
        v-model="role"
        :items="[{ label: t('auth.business'), value: 'business' }, { label: t('auth.student'), value: 'student' }]"
      />
    </UFormField>
    <UAuthForm
      ref="authForm"
      :fields="fields"
      :schema="schema"
      :loading="pending"
      :title="signup ? t('auth.signupTitle') : t('auth.loginTitle')"
      :submit="{ label: signup ? t('auth.createAccount') : t('navigation.login') }"
      @submit="onSubmit"
    >
      <template #description>
        <ULink :to="signup ? '/login' : '/signup'">{{ signup ? t('auth.existing') : t('auth.newAccount') }}</ULink>
      </template>
    </UAuthForm>
  </div>
</template>
