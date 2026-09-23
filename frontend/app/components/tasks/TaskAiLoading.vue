<script setup lang="ts">
defineProps<{ title: string, description: string }>()
</script>

<template>
  <section
    data-ai-loading
    class="overflow-hidden rounded-2xl border border-primary/20 bg-default p-5 sm:p-6"
    role="status"
    aria-live="polite"
    aria-atomic="true"
  >
    <div class="flex items-start gap-4">
      <div
        data-ai-orb
        class="relative flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary"
        aria-hidden="true"
      >
        <UIcon
          name="i-lucide-sparkles"
          class="size-6"
        />
      </div>
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-3">
          <h2 class="text-sm font-semibold text-highlighted">
            {{ title }}
          </h2>
          <span
            data-ai-dots
            class="flex gap-1"
            aria-hidden="true"
          ><i /><i /><i /></span>
        </div>
        <p class="mt-2 text-xs leading-6 text-muted">
          {{ description }}
        </p>
      </div>
    </div>
    <div
      class="mt-5 space-y-2.5 pl-16"
      aria-hidden="true"
    >
      <div
        data-ai-line
        class="h-2 w-4/5 rounded-full bg-primary/10"
      />
      <div
        data-ai-line
        class="h-2 w-full rounded-full bg-primary/10"
      />
      <div
        data-ai-line
        class="h-2 w-3/5 rounded-full bg-primary/10"
      />
    </div>
  </section>
</template>

<style scoped>
[data-ai-loading] { animation: ai-appear 300ms ease-out both; }
[data-ai-orb] { animation: ai-breathe 2.4s ease-in-out infinite; }
[data-ai-orb]::after {
  content: '';
  position: absolute;
  inset: -4px;
  border: 1px solid color-mix(in srgb, var(--ui-primary) 25%, transparent);
  border-radius: 1.25rem;
  animation: ai-breathe 2.4s ease-in-out infinite reverse;
}
[data-ai-dots] i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--ui-primary);
  animation: ai-dot 1.4s ease-in-out infinite;
}
[data-ai-dots] i:nth-child(2) { animation-delay: 160ms; }
[data-ai-dots] i:nth-child(3) { animation-delay: 320ms; }
[data-ai-line] { position: relative; overflow: hidden; }
[data-ai-line]::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--ui-primary) 18%, transparent), transparent);
  animation: ai-shimmer 2s ease-in-out infinite;
}
[data-ai-line]:nth-child(2)::after { animation-delay: 140ms; }
[data-ai-line]:nth-child(3)::after { animation-delay: 280ms; }
@keyframes ai-appear { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
@keyframes ai-breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.06); } }
@keyframes ai-dot { 0%, 70%, 100% { opacity: 0.4; transform: translateY(0); } 35% { opacity: 1; transform: translateY(-3px); } }
@keyframes ai-shimmer { from { transform: translateX(-100%); } to { transform: translateX(100%); } }
@media (prefers-reduced-motion: reduce) {
  [data-ai-loading], [data-ai-orb], [data-ai-orb]::after, [data-ai-dots] i, [data-ai-line]::after { animation: none; }
}
</style>
