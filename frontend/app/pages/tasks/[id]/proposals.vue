<script setup lang="ts">
const route = useRoute()
await navigateTo(`/tasks/${encodeURIComponent(String(route.params.id))}`, { replace: true })
</script>

<template>
  <div />
</template>
