<script setup lang="ts">
useSeoMeta({ title: 'Понятные бизнес-задачи — проекты для студенческих команд' })
const steps = [
  { icon: 'i-lucide-pencil-line', title: 'Опишите потребность', description: 'Расскажите задачу своими словами. Не нужно заранее уметь составлять идеальное техническое задание.' },
  { icon: 'i-lucide-messages-square', title: 'Уточните важное', description: 'Ответьте на вопросы о результатах, сроках, пользователях и доступных материалах.' },
  { icon: 'i-lucide-users-round', title: 'Выберите команду', description: 'Просмотрите идеи и предложения команд. Бизнес сам решает, с кем работать.' }
]
</script>

<template>
  <main>
    <UPageHero
      class="relative overflow-hidden"
      :ui="{ container: 'relative py-24 sm:py-32' }"
    >
      <template #top>
        <div
          class="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
          aria-hidden="true"
        >
          <div class="absolute -top-52 left-1/2 size-[44rem] -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />
          <div class="absolute top-48 right-0 size-72 rounded-full bg-blue-400/10 blur-3xl" />
        </div>
      </template>
      <template #headline>
        <UBadge
          label="Пилот AI Sana · Казахстан"
          icon="i-lucide-sparkles"
          color="primary"
          variant="subtle"
          class="mb-2"
        />
      </template>
      <template #title>
        Задача, которую&nbsp;<span class="text-primary">хочется решить</span>
      </template>
      <template #description>
        Бизнес делится настоящими задачами, а студенческие команды предлагают идеи и решения. Начните с простого описания — детали поможем собрать.
      </template>
      <template #links>
        <div class="flex flex-wrap justify-center gap-3">
          <UButton
            label="Посмотреть задачи"
            to="/catalog"
            size="xl"
            trailing-icon="i-lucide-arrow-right"
          />
          <UButton
            label="Я представляю бизнес"
            to="/tasks/new"
            color="neutral"
            variant="outline"
            size="xl"
            leading-icon="i-lucide-plus"
          />
        </div>
      </template>
      <template #bottom>
        <UAlert
          color="warning"
          variant="subtle"
          icon="i-lucide-flask-conical"
          title="Интерактивный демонстрационный MVP"
          description="Сейчас задачи и отклики сохраняются в вашем браузере. Общий каталог подключим после готовности backend."
          class="max-w-2xl mx-auto mt-12 text-left"
        />
      </template>
    </UPageHero>

    <UPageSection
      id="workflow"
      headline="От потребности до предложения"
      title="Простой путь к настоящему проекту"
      description="Никаких автоматических назначений: люди договариваются с людьми."
      :ui="{ container: 'py-16 sm:py-24' }"
    >
      <UPageGrid>
        <UPageCard
          v-for="(step, index) in steps"
          :key="step.title"
          :icon="step.icon"
          :title="step.title"
          :description="step.description"
          :spotlight="true"
        >
          <template #footer>
            <div class="flex items-center gap-2 text-sm font-medium text-primary">
              <span class="grid size-6 place-items-center rounded-full bg-primary/10">{{ index + 1 }}</span> Шаг {{ index + 1 }}
            </div>
          </template>
        </UPageCard>
      </UPageGrid>
    </UPageSection>

    <UPageSection
      class="border-y border-default bg-elevated/50"
      headline="Общий результат"
      title="Польза обеим сторонам"
      description="Бизнес лучше формулирует запрос. Студенты получают опыт на задачах из реального мира."
      :ui="{ container: 'py-16 sm:py-20' }"
    >
      <div class="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
        <UPageCard
          title="Для бизнеса"
          description="Задайте контекст, обозначьте ограничения и получите идеи от заинтересованных команд."
          icon="i-lucide-building-2"
          color="primary"
        />
        <UPageCard
          title="Для студентов"
          description="Выбирайте проект по интересу, собирайте команду и предлагайте свой план решения."
          icon="i-lucide-graduation-cap"
          color="neutral"
        />
      </div>
    </UPageSection>

    <UPageCTA
      headline="Есть задача или идея?"
      title="Начните сегодня"
      description="Добавьте проект в каталог или найдите задачу, над которой вашей команде будет интересно работать."
      :links="[{ label: 'Создать задачу', to: '/tasks/new', icon: 'i-lucide-plus' }, { label: 'Открыть каталог', to: '/catalog', color: 'neutral', variant: 'outline' }]"
      class="py-12 sm:py-20"
    />
  </main>
</template>
