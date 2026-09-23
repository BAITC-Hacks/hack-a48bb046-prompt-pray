<script setup lang="ts">
withDefaults(defineProps<{ title: string, description: string, icon?: string }>(), { icon: 'i-lucide-folder-open' })
</script>

<template>
  <div class="rounded-2xl border border-dashed border-default bg-muted/30 px-6 py-16 text-center">
    <UIcon
      :name="icon"
      class="mb-4 size-10 text-muted"
      aria-hidden="true"
    />
    <h2 class="text-lg font-semibold text-highlighted">
      {{ title }}
    </h2>
    <p class="mx-auto mt-2 max-w-md text-sm text-muted">
      {{ description }}
    </p>
    <div
      v-if="$slots.default"
      class="mt-6 flex justify-center gap-3"
    >
      <slot />
    </div>
  </div>
</template>
