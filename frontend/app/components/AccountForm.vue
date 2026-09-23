<script setup lang="ts">
import * as z from 'zod'
import type { FormSubmitEvent, AuthFormField } from '@nuxt/ui'

const props = defineProps<{ signup?: boolean }>()
const session = useSession()
const route = useRoute()
const form = useTemplateRef('form')
const pending = ref(false)
const errorMessage = ref('')
const registered = ref(false)
const fields: AuthFormField[] = [
  ...(props.signup ? [{ name: 'username', type: 'text' as const, label: 'Имя пользователя', autocomplete: 'username', required: true, help: '3–50 символов: латиница, цифры, _, . или -' }] : []),
  { name: 'email', type: 'email', label: 'Электронная почта', autocomplete: 'email', required: true },
  { name: 'password', type: 'password', label: 'Пароль', autocomplete: props.signup ? 'new-password' : 'current-password', required: true }
]
const schema = z.object({
  username: props.signup
    ? z.string().min(3, 'Минимум 3 символа').max(50, 'Максимум 50 символов').regex(/^[A-Za-z0-9_.-]+$/, 'Используйте латиницу, цифры, _, . или -')
    : z.string().optional(),
  email: z.email('Укажите корректный email'),
  password: props.signup
    ? z.string().min(8, 'Минимум 8 символов').refine(value => new TextEncoder().encode(value).length <= 72, 'Пароль должен быть не длиннее 72 байт')
    : z.string().min(1, 'Введите пароль')
})

async function onSubmit({ data }: FormSubmitEvent<z.output<typeof schema>>) {
  if (pending.value) return
  pending.value = true
  errorMessage.value = ''
  form.value?.formRef?.clear()
  try {
    if (props.signup && !registered.value) {
      await session.register({ email: data.email, password: data.password, username: data.username! })
      registered.value = true
    }
    await session.login({ email: data.email, password: data.password })
    await navigateTo(authRedirect(route.query.redirect))
  } catch (error) {
    const failure = normalizeApiError(error)
    const messages: Record<string, string> = {
      invalid_credentials: 'Неверный email или пароль',
      email_taken: 'Этот email уже зарегистрирован',
      username_taken: 'Это имя пользователя уже занято',
      user_exists: 'Пользователь с такими данными уже существует'
    }
    errorMessage.value = messages[failure.code] ?? failure.message
    if (Array.isArray(failure.detail)) {
      form.value?.formRef?.setErrors(failure.detail.map(issue => ({ name: String(issue.loc.at(-1)), message: issue.msg })))
    } else if (failure.code === 'email_taken' || failure.code === 'username_taken') {
      form.value?.formRef?.setErrors([{ name: failure.code === 'email_taken' ? 'email' : 'username', message: errorMessage.value }])
    }
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <UAuthForm
    ref="form"
    :fields="fields"
    :schema="schema"
    :loading="pending"
    :disabled="pending"
    :title="signup ? 'Создать аккаунт' : 'Вход в AI Sana'"
    :submit="{ label: signup && !registered ? 'Зарегистрироваться' : 'Войти' }"
    icon="i-lucide-lock"
    @submit="onSubmit"
  >
    <template #description>
      {{ signup ? 'Уже есть аккаунт?' : 'Нет аккаунта?' }}
      <ULink
        :to="{ path: signup ? '/login' : '/signup', query: { redirect: authRedirect(route.query.redirect) } }"
        class="text-primary font-medium"
      >
        {{ signup ? 'Войти' : 'Зарегистрироваться' }}
      </ULink>
    </template>
    <template #validation>
      <UAlert
        v-if="registered && errorMessage"
        color="success"
        title="Аккаунт создан. Повторите вход или перейдите на страницу входа."
        class="mb-3"
      />
      <UAlert
        v-if="errorMessage"
        color="error"
        :title="errorMessage"
        role="alert"
      />
    </template>
  </UAuthForm>
</template>
