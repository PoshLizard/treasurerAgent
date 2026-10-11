# Treasurer Agent — Build Log

Running notes on what I did and what I learned while building this. Only meaningful changes get an entry (not every tiny edit).

---

## 2026-07-14 — Project setup

**What I did:**
- Installed Python 3.13.14 via `winget` (`winget install --id Python.Python.3.13`)
- Created `treasurerAgent/` project folder
- Created a virtual environment inside the project: `python -m venv venv`
- Created an empty `requirements.txt` to track dependencies

**What I learned:**
- A **virtual environment** isolates a project's installed packages from the system-wide Python and from other projects. It's conceptually closer to Node's `node_modules/` than `dist/` — it holds dependencies, not build output.
- Activating a venv (`venv\Scripts\activate`) just prepends the venv's folder to `PATH` for that terminal session, so `python`/`pip` resolve to the venv's copies instead of the system ones. Deactivating removes the override.
- The venv only matters when *running* scripts or *installing* packages — editing source files works the same regardless of whether it's activated.
- `python -m venv venv` auto-generates a `.gitignore` inside the `venv/` folder itself, so it's excluded from git without extra setup.
- On Windows, a stale already-open terminal won't see a newly-installed program until `PATH` is refreshed (new terminal window, or manually re-read `PATH` from the registry).
- Prefer `python -m pip ...` over calling `pip.exe` directly — more reliable on Windows.

---

## 2026-10-07 — First LangChain agent on Gemini

**What I did:**
- Chose the Gemini API (free tier from Google AI Studio) after finding out my Claude subscription doesn't include API access
- Recreated my venv after moving it into the project folder (a venv stores absolute paths, so it breaks when moved) and installed packages with `pip install -r requirements.txt`
- Built my first agent with LangChain 1.x `create_agent`: a Gemini model, one placeholder tool, a system prompt, and a Pydantic `Answer` response format

**What I learned:**
- An **agent** is a model (decides what to do) + tools (Python functions it can ask to run) + a loop (`create_agent` runs the tool calls and feeds the results back until the model gives a final answer)
- The model never sees my code. It only sees each tool's name, docstring and parameter schema, so the docstring is the tool's documentation for the model
- `@tool` and `response_format` both turn Pydantic models into **JSON Schema**. That's how the LLM learns the shape of inputs and outputs, and Pydantic validates what comes back
- `agent.invoke` returns the agent's whole state: `messages` (the full conversation, including tool calls) and `structured_response` (my `Answer` object)
- Structured output guarantees the fields exist, not that the content is true. The model made up URLs for `sources` until a `Field` description told it to cite only URLs returned by tools
- Many tutorials use pre-1.0 LangChain APIs (`AgentExecutor`, `create_tool_calling_agent`), so check which version a tutorial targets
- To read a traceback, start at the last line, then find the line in my own file
- Newer or limited-time Gemini models can return 503/504 when overloaded. Use the stable model, with a fallback

**Decisions / why:**
- LangChain 1.x `create_agent` and the official docs instead of older tutorials, because that's the current API

---

## 2026-10-10 — FastAPI + Next.js skeleton, deployed to dev

**What I did:**
- Split the repo into `backend/` (FastAPI) and `frontend/` (Next.js 16) in one repository
- Backend: `/health` and `/chat` endpoints with Pydantic request/response models; agent setup in `agent.py`, schemas in `schemas.py`, tools in `tools.py`
- Frontend: chat page (Server Component), chat box (Client Component), and an `/api/chat` route handler that forwards requests to the backend
- Security: a shared API secret in an `X-API-Key` header (checked with a FastAPI dependency and a constant-time comparison) and a Basic Auth login in `proxy.ts`
- Reliability: `ModelFallbackMiddleware` falls back to a lighter model, and Gemini outages return 503 instead of 500
- Deployed the backend to Render and the frontend to Vercel as a dev environment that redeploys automatically from the `dev` branch; pinned Python dependencies
- Started using feature branch → PR → `dev` → `main`

**What I learned:**
- FastAPI maps closely to Spring Boot: `@app.post` is like `@PostMapping`, Pydantic models are like DTOs, Uvicorn is like embedded Tomcat, and `/docs` is like a built-in Postman
- Importing a Python file runs it. `if __name__ == "__main__":` keeps test code from running when another file imports it
- Use plain `def` endpoints for blocking calls like `agent.invoke`. A blocking call inside `async def` freezes the whole server
- Status codes say which side failed: 404 no route, 405 wrong method, 422 bad request body, 401 bad credentials, 500 my code crashed, 502 a proxy couldn't reach the server behind it, 503 a dependency is unavailable
- In Next.js, components are Server Components unless marked `"use client"`. Route handlers run on the server, so environment variables without `NEXT_PUBLIC_` never reach the browser
- A proxy should pass status codes through unchanged, or every error looks like a success
- Environment variables: the same code runs everywhere and only the configuration changes. `.env` files never reach GitHub, so Vercel and Render need their values in their dashboards, and they only read them when creating a deployment (redeploy after changes)
- Vercel detects the framework once, at import, from the default branch. When `main` didn't have the frontend yet, I had to set Root Directory and Framework Preset by hand
- A deployed server must listen on `0.0.0.0` and the port the host provides (`$PORT`), not `127.0.0.1`
- **Least privilege:** each service gets only the secrets it uses. The Gemini key belongs only on the backend

**Decisions / why:**
- Deployed a minimal skeleton before building features, because deployment problems are easiest to fix while the app is tiny
- The browser calls the app's own `/api/chat` route, not Render directly, so the secret stays on the server and there's no CORS setup
- Basic Auth for now because I'm the only user. Real accounts later if other officers use the app

---

## Template for new entries

```
## YYYY-MM-DD — <short title>

**What I did:**
-

**What I learned:**
-

**Decisions / why:**
-
```
