<script setup lang="ts">
import { Translation as I18nT } from 'vue-i18n'

const { t } = useAppI18n()
useSeoMeta({ title: () => t('home.meta'), description: () => t('home.description') })
const steps = [
  { id: 'describe', icon: 'i-lucide-pencil-line' },
  { id: 'clarify', icon: 'i-lucide-messages-square' },
  { id: 'select', icon: 'i-lucide-users-round' }
]
</script>

<template>
  <main>
    <UPageHero
      class="relative overflow-hidden"
      :ui="{ container: 'relative py-24 sm:py-32' }"
    >
      <template #headline>
        <UBadge
          :label="t('home.badge')"
          icon="i-lucide-sparkles"
          color="primary"
          variant="subtle"
          class="mb-2"
        />
      </template>
      <template #title>
        <I18nT
          keypath="home.title"
          scope="global"
        >
          <template #highlight>
            <span class="text-primary">{{ t('home.highlight') }}</span>
          </template>
        </I18nT>
      </template>
      <template #description>
        {{ t('home.description') }}
      </template>
      <template #links>
        <div class="flex flex-wrap justify-center gap-3">
          <UButton
            :label="t('home.browse')"
            to="/catalog"
            size="xl"
            trailing-icon="i-lucide-arrow-right"
          />
          <UButton
            :label="t('home.business')"
            to="/tasks/new"
            color="neutral"
            variant="outline"
            size="xl"
            leading-icon="i-lucide-plus"
          />
        </div>
      </template>
    </UPageHero>

    <UPageSection
      id="workflow"
      :headline="t('home.workflowHeadline')"
      :title="t('home.workflowTitle')"
      :description="t('home.workflowDescription')"
      :ui="{ container: 'py-16 sm:py-24' }"
    >
      <UPageGrid>
        <UPageCard
          v-for="step in steps"
          :key="step.id"
          :icon="step.icon"
          :title="t(`home.steps.${step.id}.title`)"
          :description="t(`home.steps.${step.id}.description`)"
          variant="naked"
        />
      </UPageGrid>
    </UPageSection>

    <UPageSection
      class="border-y border-default bg-elevated/50"
      :headline="t('home.benefitsHeadline')"
      :title="t('home.benefitsTitle')"
      :description="t('home.benefitsDescription')"
      :ui="{ container: 'py-16 sm:py-20' }"
    >
      <div class="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
        <UPageCard
          :title="t('home.businessTitle')"
          :description="t('home.businessDescription')"
          icon="i-lucide-building-2"
          color="primary"
        />
        <UPageCard
          :title="t('home.studentsTitle')"
          :description="t('home.studentsDescription')"
          icon="i-lucide-graduation-cap"
          color="neutral"
        />
      </div>
    </UPageSection>
  </main>
</template>
