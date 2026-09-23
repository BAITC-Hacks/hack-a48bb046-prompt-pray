<script setup lang="ts">
import { NuxtLink } from '#components'

withDefaults(defineProps<{
  to?: string
  title?: string
  description?: string
  variant?: 'outline' | 'soft'
}>(), { variant: 'outline' })
</script>

<template>
  <component
    :is="to ? NuxtLink : 'section'"
    v-bind="to ? { to } : {}"
    data-app-card
    :data-linked="to ? '' : undefined"
    :data-variant="variant"
    class="group space-y-4"
  >
    <div v-if="$slots.leading">
      <slot name="leading" />
    </div>
    <header v-if="title || description">
      <h2
        v-if="title"
        class="text-xl font-semibold leading-snug tracking-tight text-highlighted"
      >
        {{ title }}
      </h2>
      <p
        v-if="description"
        class="mt-3 text-sm leading-7 text-muted"
      >
        {{ description }}
      </p>
    </header>
    <slot />
    <footer v-if="$slots.footer">
      <slot name="footer" />
    </footer>
  </component>
</template>

<style scoped>
[data-app-card] {
  display: block;
  padding: 1.5rem;
  border-radius: 1rem;
}
[data-variant='outline'] { border: 1px solid var(--ui-border); background: var(--ui-bg); }
[data-variant='soft'] { background: color-mix(in srgb, var(--ui-bg-muted) 60%, transparent); }
[data-linked] {
  height: 100%;
  min-height: 240px;
  padding: 1.75rem;
  transition: border-color 180ms ease, background-color 180ms ease;
}
[data-linked]:hover { border-color: var(--ui-primary); background: var(--ui-bg-muted); }
[data-linked]:focus-visible { outline: 2px solid var(--ui-primary); outline-offset: 4px; }
@media (prefers-reduced-motion: reduce) { [data-linked] { transition: none; } }
</style>
