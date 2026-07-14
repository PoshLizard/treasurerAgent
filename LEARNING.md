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
