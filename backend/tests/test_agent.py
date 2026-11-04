from langchain_core.messages import HumanMessage, ToolMessage

import agent
from schemas import Answer, Link
from tools import _wrap_source


class FakeAgent:
    """Stands in for the LangChain agent: returns a canned answer and conversation."""

    def __init__(self, answer, messages):
        self.result = {"structured_response": answer, "messages": messages}

    def invoke(self, state):
        return self.result


def run(monkeypatch, answer, messages):
    monkeypatch.setattr(agent, "agent", FakeAgent(answer, messages))
    return agent.run_agent("Where can we apply for conference funding?")


def tool_result(name, url):
    return ToolMessage(content=_wrap_source(url, "Title", "page text"), name=name, tool_call_id="call-1")


def answer_citing(url):
    return Answer(summary="Apply here.", action_links=[Link(label="Apply", url=url)], sources=[url])


def test_links_from_pages_the_tools_opened_are_kept(monkeypatch):
    url = "https://grants.example.edu/apply"
    result = run(monkeypatch, answer_citing(url), [tool_result("read_page", url)])
    assert result.action_links == [Link(label="Apply", url=url)]
    assert result.sources == [url]


def test_invented_links_are_removed(monkeypatch):
    messages = [tool_result("research_web", "https://grants.example.edu/apply")]
    result = run(monkeypatch, answer_citing("https://made-up.example/apply"), messages)
    assert result.action_links == []
    assert result.sources == []


def test_links_with_special_characters_still_match(monkeypatch):
    # Tool results escape & as &amp; inside the source tag, so the check has to unescape it
    url = "https://grants.example.edu/apply?term=fall&year=2026"
    result = run(monkeypatch, answer_citing(url), [tool_result("research_web", url)])
    assert result.sources == [url]


def test_links_only_the_user_typed_are_not_citable(monkeypatch):
    # Only pages a tool actually returned count as sources, so the answer can't cite an unopened page
    url = "https://grants.example.edu/apply"
    result = run(monkeypatch, answer_citing(url), [HumanMessage(f"Is {url} legit?")])
    assert result.sources == []
