<script setup lang="ts">
withDefaults(defineProps<{ title: string, description: string, icon?: string }>(), { icon: 'i-lucide-folder-open' })
</script>

<template>
  <div class="rounded-2xl border border-dashed border-default bg-muted/30 px-6 py-16 text-center">
    <div class="mx-auto mb-5 flex size-16 items-center justify-center rounded-2xl border border-default bg-default shadow-sm">
      <UIcon
        :name="icon"
        class="size-7 text-primary"
        aria-hidden="true"
      />
    </div>
    <h2 class="text-lg font-semibold text-highlighted">
      {{ title }}
    </h2>
    <p class="mx-auto mt-2 max-w-md text-sm leading-7 text-muted">
      {{ description }}
    </p>
    <div
      v-if="$slots.default"
      class="mt-6 flex flex-wrap justify-center gap-3"
    >
      <slot />
    </div>
  </div>
</template>
