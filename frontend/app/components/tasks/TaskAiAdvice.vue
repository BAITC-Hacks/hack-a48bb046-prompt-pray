<script setup lang="ts">
const props = defineProps<{ endpoint: string, label: string }>()
const api = useApi()
const { t } = useAppI18n()
const { errorMessage } = useApiMessages()
const pending = ref(false)
const error = ref<unknown>(null)
const advice = ref<{ summary: string, suggestions: string[] } | null>(null)
async function analyze() {
  if (pending.value) return
  pending.value = true
  error.value = null
  try {
    advice.value = await api.request(props.endpoint, { method: 'POST' })
  } catch (cause) {
    error.value = cause
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <section class="space-y-3 rounded-xl border border-primary/20 bg-primary/5 p-4">
    <UButton
      :label="label"
      :loading="pending"
      icon="i-lucide-sparkles"
      variant="soft"
      @click="analyze"
    />
    <p class="text-xs text-muted">
      {{ t('ai.advisory') }}
    </p>
    <p
      v-if="pending"
      role="status"
      class="text-sm text-muted"
    >
      {{ t('ai.wait') }}
    </p>
    <UAlert
      v-if="error"
      color="error"
      :title="errorMessage(error)"
    />
    <div
      v-if="advice"
      aria-live="polite"
      class="space-y-3 text-sm leading-6"
    >
      <p class="whitespace-pre-wrap">
        {{ advice.summary }}
      </p>
      <ul class="list-disc space-y-2 pl-5">
        <li
          v-for="(suggestion, index) in advice.suggestions"
          :key="index"
        >
          {{ suggestion }}
        </li>
      </ul>
    </div>
  </section>
</template>
