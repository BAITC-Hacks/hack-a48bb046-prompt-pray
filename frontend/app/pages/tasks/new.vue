<script setup lang="ts">
import * as z from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'

useSeoMeta({ title: 'Новая задача' })
const workspace = useTasks()
const submitting = ref(false)
const error = ref('')
const formState = reactive({ brief: '' })
const schema = z.object({
  brief: z.string().trim().min(30, 'Добавьте подробностей: минимум 30 символов.').max(4000, 'Уменьшите описание до 4000 символов.')
})
type Schema = z.output<typeof schema>

async function onSubmit({ data }: FormSubmitEvent<Schema>) {
  submitting.value = true
  error.value = ''
  try {
    const task = workspace.createDraft(data.brief)
    await navigateTo(`/tasks/${task.id}`)
  } catch {
    error.value = 'Не удалось сохранить черновик. Проверьте, доступно ли хранилище браузера.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UContainer class="py-12 sm:py-16 max-w-3xl">
    <div class="mb-8">
      <UBadge
        label="Шаг 1 из 3"
        color="primary"
        variant="subtle"
        class="mb-4"
      />
      <h1 class="text-3xl sm:text-4xl font-bold tracking-tight">
        Опишите, что нужно решить
      </h1>
      <p class="text-muted mt-3 text-lg">
        Расскажите о задаче своими словами. Мы поможем оформить её в понятный бриф для студенческих команд.
      </p>
    </div>
    <UAlert
      color="warning"
      variant="subtle"
      title="Демонстрационный режим"
      description="Черновик сохранится в этом браузере. Отправка в общий каталог станет доступна после подключения backend для каталога."
      class="mb-6"
    />
    <UCard>
      <UForm
        :schema="schema"
        :state="formState"
        class="space-y-6"
        @submit="onSubmit"
      >
        <UFormField
          label="О чём проект?"
          name="brief"
          description="Что сейчас происходит, какая потребность возникла и кому нужна помощь?"
          required
        >
          <UTextarea
            v-model="formState.brief"
            name="brief"
            :rows="8"
            autoresize
            :maxrows="14"
            placeholder="Например: сейчас наш магазин вручную сводит продажи из разных таблиц. Нам нужно понять, какие товары покупают вместе, чтобы планировать закупки…"
            class="w-full"
          />
        </UFormField>
        <UAlert
          v-if="error"
          color="error"
          :title="error"
        />
        <div class="flex flex-col-reverse sm:flex-row sm:justify-between sm:items-center gap-4">
          <ULink
            to="/account"
            class="text-sm text-muted hover:text-default"
          >Вернуться в личный кабинет</ULink>
          <UButton
            type="submit"
            label="Продолжить к вопросам"
            trailing-icon="i-lucide-arrow-right"
            size="lg"
            :loading="submitting"
          />
        </div>
      </UForm>
    </UCard>
  </UContainer>
</template>
