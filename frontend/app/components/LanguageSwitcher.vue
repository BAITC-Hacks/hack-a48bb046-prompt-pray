<script setup lang="ts">
const { locale, t, setLocale } = useAppI18n()
const selectedLocale = computed({ get: () => locale.value, set: setLocale })
const languages = [
  { value: 'ru', label: 'Русский' },
  { value: 'kk', label: 'Қазақша' },
  { value: 'en', label: 'English' }
]
</script>

<template>
  <select
    v-model="selectedLocale"
    :aria-label="t('language.label')"
    class="rounded-md border border-default bg-default px-2 py-1.5 text-sm text-highlighted focus-visible:outline-2 focus-visible:outline-primary"
  >
    <option
      v-for="language in languages"
      :key="language.value"
      :value="language.value"
      :lang="language.value"
    >
      {{ language.label }}
    </option>
  </select>
</template>
