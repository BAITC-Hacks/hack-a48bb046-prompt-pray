const templateCard = {
  title: 'Прогноз спроса для сети кофеен',
  context: 'Тестовая сеть из трёх кофеен списывает выпечку из-за неточного планирования. Нужен прогноз спроса на следующий день.',
  data: 'Обезличенные продажи за 12 месяцев в CSV: дата, кофейня, товар, количество, цена и списания. Пример данных предоставим команде.',
  expected_result: 'Веб-прототип с загрузкой CSV, прогнозом продаж на неделю и рекомендациями по закупкам для каждой кофейни.',
  success_criteria: 'На отложенной выборке ошибка прогноза не более 20%. Цель пилота — сократить списания на 15% за месяц.',
  constraints: 'Срок — 6 недель. Использовать открытые библиотеки, не передавать данные внешним сервисам. Бюджет на платные API отсутствует.',
  users: 'Управляющие трёх кофеен и один закупщик. Ежедневно открывают отчёт на ноутбуке перед оформлением заказа.',
  business_contact: 'Анна, управляющая тестовой сети. Email: anna@example.com. Готова встречаться с командой раз в неделю.'
}

export function useTemplateMode() {
  const route = useRoute()
  const enabled = computed(() => route.query.t === '1')

  // Run once on entry/activation, never refill a field the user deliberately clears.
  function prefill(work: () => void) {
    watch(enabled, (active) => {
      if (active) work()
    }, { immediate: true })
  }

  return {
    enabled,
    prefill,
    card: templateCard,
    description: templateCard.context,
    proposal: {
      idea: 'Сделаем прогноз спроса по истории продаж и простой интерфейс рекомендаций по закупкам.',
      plan: 'Неделя 1: изучение данных. Недели 2–3: базовая модель и проверка качества. Недели 4–5: интерфейс и пилот. Неделя 6: демонстрация и документация.',
      prototype_url: 'https://example.com/coffee-prototype'
    },
    comment: 'Обсудим предложенный план, сроки и доступ к тестовым данным на встрече.',
    auth: { username: 'template_business', email: 'template@example.com', password: 'Template-demo-123!' }
  }
}
