<script setup lang="ts">
const route = useRoute()
const { t } = useAppI18n()
const { errorMessage } = useApiMessages()
const { failure, pending, check, user } = useAuthAvailability()
const affected = computed(() => failure.value?.path === route.fullPath)
</script>

<template>
  <UContainer
    v-if="affected"
    class="py-6"
  >
    <UAlert
      color="warning"
      icon="i-lucide-wifi-off"
      :title="errorMessage(failure)"
      :description="t('errors.session_check_unavailable')"
    >
      <template #actions>
        <UButton
          :label="t('interface.retry')"
          :loading="pending"
          color="neutral"
          variant="outline"
          @click="check(route.fullPath)"
        />
      </template>
    </UAlert>
  </UContainer>
  <slot v-if="!affected || user" />
</template>
