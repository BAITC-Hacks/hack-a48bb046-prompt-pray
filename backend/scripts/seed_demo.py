"""Local development fixtures, created through the API without replacing user data."""
import uuid

import httpx

PASSWORD = "password123"
ACCOUNTS = [("user1", "business"), ("user2", "student"), ("user3", "student")]
TASKS = [
    {
        "title": "Демо: дашборд продаж кофейни",
        "context": "Учебный пример: владелец кофейни вручную сводит продажи и хочет видеть выручку по дням.",
        "data": "В демосценарии предполагается CSV с датой, товаром, количеством и суммой. Реальные файлы не приложены.",
        "expected_result": "Прототип дашборда с фильтром периода и популярными товарами.",
        "success_criteria": "Итоги совпадают с учебным CSV; можно сравнить два периода.",
        "constraints": "Две недели, без персональных данных и платных интеграций.",
        "users": "Управляющий кофейней.",
        "business_contact": "Демоаккаунт user1.",
    },
    {
        "title": "Демо: учёт заявок мастерской",
        "context": "Учебный пример: заявки на ремонт теряются в таблицах и переписке.",
        "expected_result": "Прототип списка заявок со статусами и поиском.",
        "success_criteria": "Оператор находит заявку и меняет статус без помощи разработчика.",
        "users": "Оператор мастерской.",
    },
    {
        "title": "Демо: анализ отзывов магазина",
        "context": "Учебный пример: нужно понять, на что чаще всего жалуются покупатели.",
    },
]


def seed_demo(base_url: str) -> None:
    """Called only by the development launcher; repeat runs preserve edited fixtures."""
    with httpx.Client(base_url=base_url.rstrip('/') + '/api/v1', timeout=15) as client:
        def request(method, path, *, headers=None, **kwargs):
            response = client.request(method, path, headers=headers, **kwargs)
            if not response.is_success:
                # Do not print bodies containing account data or credentials.
                raise RuntimeError(f"Demo setup: {method} {path}: HTTP {response.status_code}")
            return response.json()

        accounts = {}
        for username, role in ACCOUNTS:
            email = f"{username}@demo.example.com"
            registered = client.post('/auth/register', json={
                'email': email, 'username': username, 'password': PASSWORD, 'role': role,
            })
            if registered.status_code not in (201, 409):
                raise RuntimeError(f"Demo registration failed: HTTP {registered.status_code}")
            tokens = request('POST', '/auth/login', json={'email': email, 'password': PASSWORD})
            headers = {'Authorization': f"Bearer {tokens['access_token']}"}
            user = request('GET', '/users/me', headers=headers)
            if user['username'] != username or user['role'] != role:
                raise RuntimeError(f"Demo account {username} conflicts with an existing account; nothing overwritten")
            accounts[username] = (headers, user['id'])

        owner = accounts['user1'][0]
        drafts = request('GET', '/catalog/drafts', headers=owner)
        by_description = {draft['description']: draft for draft in drafts}
        cards = []
        for payload in TASKS:
            description = payload['context']
            draft = by_description.get(description)
            if draft is None:
                draft = request('POST', '/catalog/drafts', headers=owner, json={'description': description})
            if draft['card_id']:
                cards.append(draft['card_id'])
                continue
            card = request('POST', f"/catalog/drafts/{draft['id']}/card", headers=owner, json=payload)
            path = f"/catalog/tasks/{card['id']}"
            # These are explicitly labelled fixtures, not AI output or real business decisions.
            card = request('POST', path + '/confirm', headers=owner, json={'confirmed': True, 'expected_version': card['version']})
            request('POST', path + '/publish', headers=owner, json={'expected_version': card['version']})
            cards.append(card['id'])

        description = 'Демо-черновик: хочу автоматизировать запись клиентов, пока не знаю с чего начать.'
        if description not in by_description:
            request('POST', '/catalog/drafts', headers=owner, json={'description': description})

        path = f'/catalog/tasks/{cards[0]}'
        existing = request('GET', path + '/proposals', headers=owner)
        # Do not republish a fixture that the user has edited and withdrawn.
        public = client.get(path)
        if public.status_code != 200:
            return
        for username, idea, plan in [
            ('user2', 'Сделаем интерактивный дашборд', 'Разберём учебный CSV, соберём графики, сверим итоги.'),
            ('user3', 'Предлагаем простой отчёт для управляющего', 'Согласуем показатели, сделаем прототип и проведём демонстрацию.'),
        ]:
            headers, user_id = accounts[username]
            if any(proposal['user_id'] == user_id for proposal in existing):
                continue
            request('POST', path + '/proposals', headers=headers, json={
                'team_id': str(uuid.uuid5(uuid.NAMESPACE_URL, f'ai-sana-demo/{username}')),
                'idea': idea, 'plan': plan,
            })
        print('Демоданные готовы: user1 — бизнес; user2, user3 — студенты. Пароль: password123.', flush=True)
