from datetime import date
from itertools import count

import httpx
import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_google_genai.chat_models import GoogleAPIError

import agent
import tools
from schemas import Answer, Link
from test_tools import FakeFirecrawl, scraped_page
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


# Streaming: LangChain's stream_mode=["messages", "updates"] yields (mode, data) pairs. "messages"
# carries each token as the model writes it, and "updates" carries each finished step.

class FakeStreamingAgent:
    def __init__(self, events):
        self.events = events

    def stream(self, state, stream_mode):
        return iter(self.events)


def stream(monkeypatch, events):
    monkeypatch.setattr(agent, "agent", FakeStreamingAgent(events))
    return list(agent.stream_agent("Where can we apply for conference funding?"))


def token(blocks, node="model"):
    return ("messages", (AIMessageChunk(content=blocks), {"langgraph_node": node}))


def model_step(tool_calls=(), answer=None):
    message = AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call-{i}"}
                                                for i, (name, args) in enumerate(tool_calls)])
    return ("updates", {"model": {"messages": [message], "structured_response": answer}})


def tool_step(name, url):
    return ("updates", {"tools": {"messages": [tool_result(name, url)]}})


def test_thoughts_stream_as_they_are_written(monkeypatch):
    url = "https://grants.example.edu/apply"
    events = stream(monkeypatch, [
        token([{"type": "reasoning", "reasoning": "Comparing travel grants"}]),
        token([{"type": "reasoning", "reasoning": " with sponsorships"}]),
        token([{"type": "text", "text": '{"summary": "Apply'}]),  # the answer's raw JSON is not a thought
        model_step(answer=answer_citing(url)),
    ])
    assert [e for e in events if e["type"] == "thought"] == [
        {"type": "thought", "text": "Comparing travel grants"},
        {"type": "thought", "text": " with sponsorships"},
    ]


def test_streamed_answer_still_gets_the_citation_check(monkeypatch):
    url = "https://grants.example.edu/apply"
    invented = "https://made-up.example/apply"
    answer = Answer(summary="Apply.", action_links=[Link(label="Apply", url=url), Link(label="Fake", url=invented)],
                    sources=[url, invented])

    events = stream(monkeypatch, [tool_step("read_page", url), model_step(answer=answer)])

    assert events[-1] == {"type": "answer", "answer": {
        "summary": "Apply.", "action_links": [{"label": "Apply", "url": url}], "sources": [url]}}


def test_tool_output_is_not_streamed_as_thoughts(monkeypatch):
    url = "https://grants.example.edu/apply"
    page = ("messages", (tool_result("read_page", url), {"langgraph_node": "tools"}))
    events = stream(monkeypatch, [page, model_step(answer=answer_citing(url))])
    assert [e["type"] for e in events] == ["answer"]


def test_a_run_that_ends_without_an_answer_says_so(monkeypatch):
    events = stream(monkeypatch, [model_step(tool_calls=[("research_web", {"query": "grants"})])])
    assert events[-1] == {"type": "error", "detail": "The research stopped before it reached an answer. Try asking again."}


# The real agent graph, driven by a scripted model, to check the guardrails are wired in and
# not just written. Gemini isn't called, and Firecrawl is replaced with a fake.

class ScriptedModel(GenericFakeChatModel):
    """Replies with the given messages in order, raising any exception among them, the way a
    busy model would. Running out means the agent called it too often."""

    calls: int = 0
    last_prompt: list = []

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls += 1
        self.last_prompt = messages
        reply = next(self.messages)
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(generations=[ChatGeneration(message=reply)])


call_ids = count()


def calling(*calls):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call-{next(call_ids)}"}
                                             for name, args in calls])


def final_answer(summary):
    # A model without native structured output answers by calling a tool named after the schema
    return calling(("Answer", {"summary": summary, "action_links": [], "sources": []}))


def read_then_answer(summary):
    return [calling(("read_page", {"url": "https://grants.example.edu"})), final_answer(summary)]


def ask(graph):
    return graph.invoke({"messages": [HumanMessage("Read https://grants.example.edu")]})


@pytest.fixture
def fake_firecrawl(monkeypatch):
    monkeypatch.setattr(tools, "firecrawl", FakeFirecrawl(
        results=[scraped_page("https://grants.example.edu")], page=scraped_page("https://grants.example.edu")))


@pytest.fixture
def run_graph(fake_firecrawl):
    def run(*replies, question="Where can we apply for conference funding?"):
        graph = agent.build_agent([ScriptedModel(messages=iter(replies))])
        return graph.invoke({"messages": [HumanMessage(question)]})
    return run


def test_an_answer_before_opening_any_page_is_sent_back_once(run_graph):
    # Searching alone isn't enough: search results can't confirm details or sign-up links
    result = run_graph(
        calling(("research_web", {"query": "conference travel grants"})),
        final_answer("From search results and memory."),
        final_answer("Second try."),  # accepted: it's sent back only once, so it can't loop forever
    )
    assert result["structured_response"].summary == "Second try."
    assert [m.content for m in result["messages"] if m.type == "human"][-1] == agent.GO_READ


def test_an_answer_after_opening_a_page_goes_through(run_graph):
    result = run_graph(
        calling(("research_web", {"query": "conference travel grants"})),
        calling(("read_page", {"url": "https://grants.example.edu"})),
        final_answer("From the grant's page."),
    )
    assert result["structured_response"].summary == "From the grant's page."
    assert agent.GO_READ not in [m.content for m in result["messages"]]


def test_a_failed_page_read_does_not_count_as_opening_one(run_graph):
    result = run_graph(
        calling(("read_page", {"url": "https://never-shown.example"})),  # refused: not from any result
        final_answer("Guessing."),
        final_answer("Second try."),
    )
    assert result["structured_response"].summary == "Second try."


def test_a_search_over_the_limit_points_the_model_to_the_pages_it_found(run_graph):
    # LangChain's default message ("Do not call it again") made the model answer from memory
    searches = [("research_web", {"query": f"travel grants {n}"}) for n in range(agent.SEARCH_LIMIT + 1)]
    result = run_graph(
        calling(*searches),
        calling(("read_page", {"url": "https://grants.example.edu"})),
        final_answer("From the grant's page."),
    )
    blocked = [m.content for m in result["messages"] if m.type == "tool" and m.status == "error"]
    assert blocked == [agent.LIMIT_REACHED["research_web"]]


def test_a_read_over_the_limit_says_to_answer_from_the_pages_opened(run_graph):
    reads = [("read_page", {"url": "https://grants.example.edu"})] * (agent.READ_LIMIT + 1)
    result = run_graph(
        calling(*reads),
        final_answer("From the grant's page."),
        question="Read https://grants.example.edu",
    )
    blocked = [m.content for m in result["messages"] if m.type == "tool" and m.status == "error"]
    assert blocked == [agent.LIMIT_REACHED["read_page"]]


def test_the_model_is_told_todays_date(fake_firecrawl):
    # Without it, a page about a past conference reads like one that's still open
    model = ScriptedModel(messages=iter(read_then_answer("From the grant's page.")))
    ask(agent.build_agent([model]))
    assert model.last_prompt[0].type == "system"
    assert date.today().isoformat() in model.last_prompt[0].content


@pytest.fixture
def stream_graph(fake_firecrawl, monkeypatch):
    def run(*replies, question="Read https://grants.example.edu"):
        # disable_streaming: the scripted model replies in one piece, so its tool calls stay whole
        model = ScriptedModel(messages=iter(replies), disable_streaming=True)
        monkeypatch.setattr(agent, "agent", agent.build_agent([model]))
        return list(agent.stream_agent(question))
    return run


def steps(events):
    return [e["text"] for e in events if e["type"] == "step"]


def test_each_tool_call_is_shown_as_a_readable_step(stream_graph):
    events = stream_graph(
        calling(("research_web", {"query": "conference travel grants"})),
        *read_then_answer("From the grant's page."),
    )
    assert steps(events) == ["Searching the web for “conference travel grants”", "Reading https://grants.example.edu"]
    assert events[-1]["type"] == "answer"


def test_calls_blocked_by_a_limit_are_not_shown_as_steps(stream_graph):
    # They never ran, so a "Searching the web for…" step for them would be false
    searches = [("research_web", {"query": f"grants {n}"}) for n in range(agent.SEARCH_LIMIT + 2)]
    events = stream_graph(calling(*searches), *read_then_answer("From the grant's page."))
    # Calls in one turn run in parallel, so their steps can arrive in any order
    assert sorted(steps(events)) == sorted([f"Searching the web for “grants {n}”" for n in range(agent.SEARCH_LIMIT)]
                                           + ["Reading https://grants.example.edu"])


def test_being_sent_back_to_read_pages_is_shown_as_a_step(stream_graph):
    events = stream_graph(final_answer("From memory."), *read_then_answer("From the grant's page."))
    assert steps(events) == ["Going back to open the official pages before answering", "Reading https://grants.example.edu"]
    assert events[-1]["answer"]["summary"] == "From the grant's page."


# The model chain: each question makes several model calls, so a model that just failed shouldn't
# cost its full timeout again on every one of them

def test_a_model_that_fails_hands_off_and_is_skipped_on_the_next_call(fake_firecrawl):
    hung = ScriptedModel(messages=iter([httpx.ReadTimeout("timed out")]))
    backup = ScriptedModel(messages=iter(read_then_answer("From the backup.")))

    result = ask(agent.build_agent([hung, backup]))

    assert result["structured_response"].summary == "From the backup."
    assert hung.calls == 1  # the second call went straight to the backup


def test_models_that_all_failed_recently_are_still_tried(fake_firecrawl):
    # Otherwise one brief outage would lock everyone out until the cooldown ends
    first = ScriptedModel(messages=iter([GoogleAPIError(503, {"error": {"message": "overloaded"}})] * 2))
    second = ScriptedModel(messages=iter([GoogleAPIError(503, {"error": {"message": "overloaded"}}),
                                          *read_then_answer("It's back.")]))
    graph = agent.build_agent([first, second])

    with pytest.raises(GoogleAPIError):
        ask(graph)
    assert ask(graph)["structured_response"].summary == "It's back."
    assert first.calls == 2  # once the second model worked again, it went first
