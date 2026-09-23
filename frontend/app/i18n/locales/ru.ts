import product from '../messages/ru'

export default {
  ...product,
  language: { label: 'Язык интерфейса' },
  navigation: {
    requestPending: 'Выполняем запрос…',
    catalog: 'Каталог задач',
    workflow: 'Как это работает',
    pilot: 'Пилот AI Sana',
    account: 'Личный кабинет',
    login: 'Войти',
    loginLabel: 'Вход в аккаунт',
    signup: 'Регистрация',
    createTask: 'Создать задачу',
    home: 'На главную'
  }
}
