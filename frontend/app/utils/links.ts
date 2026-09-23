import type { NavigationMenuItem } from '@nuxt/ui'

export const navLinks: NavigationMenuItem[] = [{ label: 'Каталог задач', icon: 'i-lucide-layout-grid', to: '/catalog' }, {
  label: 'Создать задачу', icon: 'i-lucide-plus', to: '/tasks/new'
}]
