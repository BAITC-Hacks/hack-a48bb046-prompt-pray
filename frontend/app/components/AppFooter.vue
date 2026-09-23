<script setup lang="ts">
const { t } = useAppI18n()
const year = useState('copyright-year', () => new Date().getUTCFullYear())
</script>

<template>
  <UFooter class="border-t border-default">
    <template #left>
      <p class="text-xs text-muted">
        AI Sana · © {{ year }}
      </p>
    </template>
    <template #right>
      <nav
        :aria-label="t('footer.links')"
        class="flex gap-6 text-sm"
      >
        <ULink
          to="/catalog"
          class="text-muted hover:text-default"
        >{{ t('navigation.catalog') }}</ULink>
        <ULink
          to="/tasks/new"
          class="text-muted hover:text-default"
        >{{ t('navigation.createTask') }}</ULink>
      </nav>
    </template>
  </UFooter>
</template>
