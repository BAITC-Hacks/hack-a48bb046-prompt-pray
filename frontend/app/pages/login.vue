<script setup lang="ts">
import * as z from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { AccessToken, ApiError, User } from '~/types/api'

definePageMeta({ layout: 'auth' })
const api = useApi()
const route = useRoute()
const pending = ref(false)
const error = ref<ApiError | null>(null)
const role = ref<'business' | 'student'>('student')
const signup = false
const fields = [
  ...(signup ? [{ name: 'username', type: 'text' as const, label: 'Имя пользователя', required: true }] : []),
  { name: 'email', type: 'email' as const, label: 'Email', required: true },
  { name: 'password', type: 'password' as const, label: 'Пароль', required: true }
]
const schema = z.object({
  username: signup ? z.string().min(3).max(50).regex(/^[A-Za-z0-9_.-]+$/, 'Латиница, цифры, _, . или -') : z.string().optional(),
  email: z.email('Введите email'),
  password: z.string().min(signup ? 8 : 1, signup ? 'Минимум 8 символов' : 'Введите пароль').refine(value => !signup || new TextEncoder().encode(value).length <= 72, 'Не более 72 байт')
})
async function onSubmit(payload: FormSubmitEvent<z.output<typeof schema>>) {
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
      :title="error.detail"
      :description="error.code"
    />
    <UFormField
      v-if="signup"
      label="Ваша роль"
    >
      <USelect
        v-model="role"
        :items="[{ label: 'Бизнес', value: 'business' }, { label: 'Студент / команда', value: 'student' }]"
      />
    </UFormField>
    <UAuthForm
      :fields="fields"
      :schema="schema"
      :loading="pending"
      :title="signup ? 'Регистрация в AI Sana' : 'Вход в AI Sana'"
      :submit="{ label: signup ? 'Создать аккаунт' : 'Войти' }"
      @submit="onSubmit"
    >
      <template #description>
        <ULink :to="signup ? '/login' : '/signup'">{{ signup ? 'Уже есть аккаунт? Войти' : 'Нет аккаунта? Зарегистрироваться' }}</ULink>
      </template>
    </UAuthForm>
  </div>
</template>
