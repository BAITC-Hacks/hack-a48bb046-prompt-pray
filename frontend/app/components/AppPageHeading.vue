<script setup lang="ts">
defineProps<{ title: string, description?: string, eyebrow?: string, icon?: string }>()
</script>

<template>
  <header
    data-app-reveal
    class="flex flex-col gap-6 border-b border-default pb-8 sm:flex-row sm:items-end sm:justify-between"
  >
    <div class="min-w-0 max-w-3xl">
      <div
        v-if="eyebrow || icon"
        class="mb-4 flex items-center gap-2 text-sm font-medium text-primary"
      >
        <UIcon
          v-if="icon"
          :name="icon"
          class="size-5 shrink-0"
          aria-hidden="true"
        />
        <span v-if="eyebrow">{{ eyebrow }}</span>
      </div>
      <h1 class="break-words text-3xl font-semibold tracking-tight text-highlighted sm:text-4xl">
        {{ title }}
      </h1>
      <p
        v-if="description"
        class="mt-4 text-base leading-7 text-muted"
      >
        {{ description }}
      </p>
    </div>
    <div
      v-if="$slots.default"
      class="flex shrink-0 flex-wrap items-center gap-3"
    >
      <slot />
    </div>
  </header>
</template>
