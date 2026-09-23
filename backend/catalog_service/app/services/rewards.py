"""Rewards share the triggering transaction and task write lock."""
from calendar import monthrange
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from ..models.domain import ActionDay, CoinTransaction, DailyVisit, Proposal, RewardEvent, SelectionDecision, TaskCard, decision_proposals

REWARDS = {"ready_card": (50, 10), "priority_card": (30, 10), "solution_selected": (20, 5)}
COINS = {"field_filled": 5, "proposal_sent": 10, "proposal_accepted": 100}
FIELDS = ("context", "data", "expected_result", "success_criteria", "constraints", "users", "business_contact")


def insert_for(session, model):
    if session.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    return insert(model)


async def record_action(session, owner_type, owner_id):
    await session.execute(insert_for(session, ActionDay).values(
        owner_type=owner_type, owner_id=owner_id, day=today_utc(),
    ).on_conflict_do_nothing(index_elements=["owner_type", "owner_id", "day"]))


async def award_coins(session, owner_type, owner_id, task_id, reason, detail=""):
    # DB uniqueness protects retries, concurrent requests, and changed team IDs.
    await session.execute(insert_for(session, CoinTransaction).values(
        owner_type=owner_type, owner_id=owner_id, task_id=task_id,
        reason=reason, detail=detail, amount=COINS[reason],
    ).on_conflict_do_nothing(index_elements=["owner_type", "owner_id", "task_id", "reason", "detail"]))


async def award_fields(session, card):
    for field in FIELDS:
        if (getattr(card, field) or "").strip():
            await award_coins(session, "business", card.business_id, card.id, "field_filled", field)


def today_utc():
    return datetime.now(timezone.utc).date()


async def check_in(session, business_id):
    # Atomic conflict handling works across workers, including simultaneous tabs.
    if session.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    today = today_utc()
    await session.execute(insert(DailyVisit).values(business_id=business_id, day=today)
                          .on_conflict_do_nothing(index_elements=["business_id", "day"]))
    await session.commit()
    return {"date": today.isoformat()}


def streaks(days, today):
    best = run = 0
    previous = None
    for day in sorted(set(day for day in days if day <= today)):
        run = run + 1 if previous is not None and day == previous + timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    current = run if previous in (today, today - timedelta(days=1)) else 0
    return current, best


async def leaderboard(session, business_id):
    rewards = select(RewardEvent.business_id, func.sum(RewardEvent.reputation).label("reputation"),
                     func.sum(RewardEvent.coins).label("coins")).group_by(RewardEvent.business_id).subquery()
    earned = select(CoinTransaction.owner_id, func.sum(CoinTransaction.amount).label("coins"))\
        .where(CoinTransaction.owner_type == "business").group_by(CoinTransaction.owner_id).subquery()
    owners = select(rewards.c.business_id).union(select(earned.c.owner_id)).subquery()
    reputation = func.coalesce(rewards.c.reputation, 0)
    coins = func.coalesce(rewards.c.coins, 0) + func.coalesce(earned.c.coins, 0)
    businesses = (await session.execute(select(owners.c.business_id, reputation.label("reputation"),
                                               coins.label("coins"))
        .outerjoin(rewards, rewards.c.business_id == owners.c.business_id)
        .outerjoin(earned, earned.c.owner_id == owners.c.business_id)
        .order_by(reputation.desc(), coins.desc(), owners.c.business_id).limit(10))).all()
    ranked = select(SelectionDecision.id, func.row_number().over(
        partition_by=SelectionDecision.task_id,
        order_by=(SelectionDecision.created_at.desc(), SelectionDecision.id.desc()),
    ).label("position")).subquery()
    chosen = select(decision_proposals.c.proposal_id).join(
        ranked, ranked.c.id == decision_proposals.c.decision_id,
    ).where(ranked.c.position == 1).subquery()
    wins = select(Proposal.team_id, func.count(func.distinct(Proposal.task_id)).label("selected_tasks"))\
        .join(chosen, chosen.c.proposal_id == Proposal.id).group_by(Proposal.team_id).subquery()
    selected = func.coalesce(wins.c.selected_tasks, 0)
    teams = (await session.execute(select(Proposal.team_id, func.count(Proposal.id).label("proposals"),
                                          selected.label("selected_tasks"))
        .outerjoin(wins, wins.c.team_id == Proposal.team_id)
        .group_by(Proposal.team_id, wins.c.selected_tasks)
        .order_by(selected.desc(), func.count(Proposal.id).desc(), Proposal.team_id).limit(10))).all()
    return dict(scope="all", businesses=[dict(id=row.business_id, coins=row.coins, reputation=row.reputation,
                                              is_you=row.business_id == business_id) for row in businesses],
                teams=[dict(id=row.team_id, proposals=row.proposals, selected_tasks=row.selected_tasks) for row in teams])


async def award(session, card, kind):
    existing = await session.scalar(select(RewardEvent.id).where(
        RewardEvent.task_id == card.id, RewardEvent.kind == kind,
    ))
    if existing is None:
        coins, reputation = REWARDS[kind]
        session.add(RewardEvent(business_id=card.business_id, task_id=card.id,
                                kind=kind, coins=coins, reputation=reputation))
        await record_action(session, "business", card.business_id)


async def progress(session, business_id, month, owner_type="business"):
    start = datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.utc)
    end = (datetime.max.replace(tzinfo=timezone.utc) if month == "9999-12" else
           datetime(start.year + (start.month == 12), start.month % 12 + 1, 1, tzinfo=timezone.utc))
    coins, reputation = (await session.execute(select(
        func.coalesce(func.sum(RewardEvent.coins), 0),
        func.coalesce(func.sum(RewardEvent.reputation), 0),
    ).where(RewardEvent.business_id == business_id, owner_type == "business"))).one()
    coins += await session.scalar(select(func.coalesce(func.sum(CoinTransaction.amount), 0)).where(
        CoinTransaction.owner_id == business_id, CoinTransaction.owner_type == owner_type))
    rows = (await session.execute(select(RewardEvent, TaskCard.title).join(
        TaskCard, TaskCard.id == RewardEvent.task_id,
    ).where(RewardEvent.business_id == business_id, owner_type == "business", RewardEvent.created_at >= start,
            RewardEvent.created_at < end).order_by(RewardEvent.created_at, RewardEvent.id))).all()
    visits = list((await session.scalars(select(DailyVisit.day).where(
        DailyVisit.business_id == business_id).order_by(DailyVisit.day))).all())
    visited = {day.isoformat() for day in visits}
    actions = list((await session.scalars(select(ActionDay.day).where(
        ActionDay.owner_id == business_id, ActionDay.owner_type == owner_type).order_by(ActionDay.day))).all())
    active = {day.isoformat() for day in actions}
    # Product decision: flames count visits; action history and wallets are separate.
    current, best = streaks(visits, today_utc())
    action_current, action_best = streaks(actions, today_utc())
    days = {f"{month}-{day:02}": {"date": f"{month}-{day:02}", "visited": f"{month}-{day:02}" in visited,
                               "active": f"{month}-{day:02}" in active,
                               "coins": 0, "reputation": 0, "events": []}
            for day in range(1, monthrange(start.year, start.month)[1] + 1)}
    for event, title in rows:
        day = days[event.created_at.strftime("%Y-%m-%d")]
        day["coins"] += event.coins
        day["reputation"] += event.reputation
        day["events"].append(dict(id=event.id, task_id=event.task_id, title=title,
                                  kind=event.kind, detail="", created_at=event.created_at,
                                  coins=event.coins, reputation=event.reputation))
    transactions = (await session.execute(select(CoinTransaction, TaskCard.title).join(
        TaskCard, TaskCard.id == CoinTransaction.task_id,
    ).where(CoinTransaction.owner_id == business_id, CoinTransaction.owner_type == owner_type,
            CoinTransaction.created_at >= start, CoinTransaction.created_at < end)
        .order_by(CoinTransaction.created_at, CoinTransaction.id))).all()
    for event, title in transactions:
        day = days[event.created_at.strftime("%Y-%m-%d")]
        day["coins"] += event.amount
        day["events"].append(dict(id=event.id, task_id=event.task_id, title=title,
                                  kind=event.reason, detail=event.detail, created_at=event.created_at,
                                  coins=event.amount, reputation=0))
    for day in days.values():
        day["events"].sort(key=lambda event: (event["created_at"], str(event["id"])))
    return dict(month=month, timezone="UTC", coins=coins, reputation=reputation,
                wallet=dict(owner_type=owner_type, owner_id=business_id, balance=coins),
                current_streak=current, best_streak=best,
                action_current_streak=action_current, action_best_streak=action_best,
                last_action_date=actions[-1] if actions else None,
                action_days=sum(day["active"] for day in days.values()),
                active_days=sum(day["visited"] for day in days.values()), days=list(days.values()))
