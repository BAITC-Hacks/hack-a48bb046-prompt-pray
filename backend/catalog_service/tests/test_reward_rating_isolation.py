"""Engagement rewards must never purchase catalog ranking or card completeness."""
from uuid import uuid4

from conftest import auth_headers
from test_workflow import API, make_card, publish


async def test_earned_rewards_do_not_keep_an_incomplete_card_above_a_complete_one(client):
    owner = auth_headers()
    card = await make_card(client, owner, "Previously complete")
    fields = dict(data="CSV", expected_result="Report", success_criteria="Accuracy",
                  constraints="One month", users="Sales", business_contact="Owner")
    response = await client.patch(f"{API}/tasks/{card['id']}", headers=owner,
                                  json={**fields, "expected_version": card["version"]})
    assert response.status_code == 200, response.text
    await publish(client, owner, card["id"])

    current = (await client.get(f"{API}/tasks/{card['id']}", headers=owner)).json()
    response = await client.patch(f"{API}/tasks/{card['id']}", headers=owner,
                                  json={**dict.fromkeys(fields), "expected_version": current["version"]})
    assert response.status_code == 200, response.text
    assert response.json()["rating"]["total"] == 20
    await publish(client, owner, card["id"])

    other = auth_headers()
    competitor = await make_card(client, other, "More complete now")
    response = await client.patch(f"{API}/tasks/{competitor['id']}", headers=other,
                                  json={"data": "CSV", "expected_version": competitor["version"]})
    assert response.status_code == 200, response.text
    await publish(client, other, competitor["id"])
    catalog = (await client.get(API)).json()["items"]
    assert [entry["task_id"] for entry in catalog] == [competitor["id"], card["id"]]
    assert [entry["task"]["rating"]["total"] for entry in catalog] == [40, 20]

    # Rewards and low completeness cannot disable proposals or pick a winner.
    proposal = await client.post(f"{API}/tasks/{card['id']}/proposals", headers=auth_headers("student"),
                                 json=dict(team_id=str(uuid4()), idea="Dashboard", plan="Test it"))
    assert proposal.status_code == 201, proposal.text
    assert (await client.get(f"{API}/tasks/{card['id']}/decisions", headers=owner)).json() == []
