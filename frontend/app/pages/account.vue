<script setup lang="ts">
import { taskRating, readiness } from '~/utils/task-rating'

definePageMeta({ middleware: 'auth' })
useSeoMeta({ title: 'Личный кабинет' })
const session = useSession()
const workspace = useTasks()
const toast = useToast()
const pending = ref(false)

async function logout() {
  pending.value = true
  try {
    await session.logout()
    await navigateTo('/login')
  } catch (error) {
    toast.add({ title: 'Не удалось выйти', description: normalizeApiError(error).message, color: 'error' })
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <UContainer class="py-16">
    <UAlert
      color="warning"
      variant="subtle"
      title="Задачи сохранены в этом браузере"
      description="Каталог задач ожидает подключения backend."
      class="max-w-xl mx-auto mb-6"
    />
    <UPageCard
      title="Личный кабинет"
      description="Вы вошли в AI Sana."
      class="max-w-xl mx-auto"
    >
      <dl class="space-y-4">
        <div>
          <dt class="text-muted">
            Имя пользователя
          </dt>
          <dd class="font-medium">
            {{ session.user.value?.username }}
          </dd>
        </div>
        <div>
          <dt class="text-muted">
            Электронная почта
          </dt>
          <dd class="font-medium">
            {{ session.user.value?.email }}
          </dd>
        </div>
      </dl>
      <UButton
        label="Выйти"
        icon="i-lucide-log-out"
        color="neutral"
        :loading="pending"
        @click="logout"
      />
    </UPageCard>
    <section class="max-w-xl mx-auto mt-10">
      <div class="flex flex-wrap justify-between items-center gap-4 mb-5">
        <div>
          <h2 class="text-2xl font-semibold">
            Мои задачи
          </h2>
          <p class="text-muted mt-1">
            Черновики и задачи из демо-каталога.
          </p>
        </div>
        <UButton
          label="Создать задачу"
          icon="i-lucide-plus"
          to="/tasks/new"
        />
      </div>
      <div
        v-if="workspace.tasks.value.length"
        class="space-y-3"
      >
        <UCard
          v-for="task in workspace.tasks.value"
          :key="task.id"
        >
          <div class="flex flex-wrap justify-between items-center gap-4">
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2 mb-2">
                <UBadge
                  :label="task.status === 'published' ? 'В каталоге' : 'Черновик'"
                  :color="task.status === 'published' ? 'success' : 'warning'"
                  variant="subtle"
                />
                <UBadge
                  :label="readiness(taskRating(task)).label"
                  :color="readiness(taskRating(task)).color"
                  variant="subtle"
                />
              </div>
              <h3 class="font-semibold truncate">
                {{ task.title }}
              </h3>
              <p class="text-sm text-muted mt-1 line-clamp-1">
                {{ task.brief }}
              </p>
            </div>
            <UButton
              label="Открыть"
              color="neutral"
              variant="outline"
              :to="`/tasks/${task.id}`"
            />
          </div>
        </UCard>
      </div>
      <UEmpty
        v-else
        title="Пока нет задач"
        description="Начните с короткого описания вашей потребности."
      >
        <template #actions>
          <UButton
            label="Создать первую задачу"
            to="/tasks/new"
          />
        </template>
      </UEmpty>
    </section>
  </UContainer>
</template>
