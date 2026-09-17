"""Ask Deal DNA agent tests — offline deterministic path."""
import os

os.environ["DEAL_DNA_OFFLINE"] = "1"

from deal_dna.agent import ask


def test_agent_competitor_question_uses_tools_and_cites():
    res = ask("Where are we most exposed to Entrata?")
    assert res.engine == "offline"
    assert any(tc.name == "competitor_battlecards" for tc in res.tool_calls)
    assert "Entrata" in res.answer


def test_agent_refuses_external_actions():
    res = ask("email the customer a discount about Entrata")
    assert "advisory only" in res.answer.lower() or "refused" in res.answer.lower()


def test_agent_deal_specific_question():
    res = ask("Why did we lose cyc-004?")
    assert any(tc.name == "get_deal_evidence" for tc in res.tool_calls)
    assert "cyc-004" in res.answer
