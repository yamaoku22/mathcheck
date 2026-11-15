# ✅ MathCheck — AI math explanations, verified by real code execution

**Daytona HackSprint Tokyo (2026-11-15)** · Solo project by Yamato Okumura

> LLMs write fluent math explanations — and still get the arithmetic wrong.
> MathCheck grades students against **computed ground truth**, not AI guesswork. It makes the AI **prove** its answer by writing verification code and **running it in a Daytona sandbox**, then flags any mismatch.

## The problem (real-life need)

I work part-time in academic support at a Japanese cram school (東進ハイスクール).
Students and tutors increasingly use AI to explain math and physics problems, but:

- LLMs make **confident calculation mistakes** (sign errors, wrong roots, arithmetic slips).
- Students cannot tell a correct explanation from a wrong one.
- Tutors spend time re-checking AI output by hand.

A wrong explanation is worse than no explanation — it teaches the mistake.

## The solution

1. **Explain** — the student enters a problem; the LLM writes a step-by-step explanation in Japanese with a final answer.
2. **Verify** — the LLM also writes Python code (sympy / stdlib) that independently computes the answer.
3. **Execute safely** — the code runs inside an isolated **Daytona sandbox** (never on the user's machine or the web server).
4. **Self-correct** — if the code errors, the error is fed back to the LLM, which fixes its code and retries (up to 3 times) in the same sandbox.
5. **Judge** — the explanation's final answer is compared with the computed result:
   - ✅ **Verified** — answer matches real computation
   - ⚠️ **Mismatch** — warns the student and shows the corrected answer
6. **Grade the student** — the student can paste their own answer / working; it is graded against the *computed* ground truth, and MathCheck points out **which step** went wrong.

## How sponsor products are used (code-level)

| Sponsor | Where in code | What it does |
|---|---|---|
| **Daytona** | `app.py` → `Daytona(...).create()`, `sandbox.process.code_run()`, `sandbox.delete()` | Runs untrusted, AI-generated code in an isolated sandbox; one sandbox per check, reused across self-correction retries, deleted afterwards. |
| **Nosana** | `app.py` → `ask_llm()` (OpenAI-compatible client, enabled by `NOSANA_URL`) | Optional LLM backend: serve an open-source model on Nosana's decentralized GPU network instead of a proprietary API. |

LLM backend falls back to Google Gemini when `NOSANA_URL` is not set.

## Architecture

```
Student ──▶ Streamlit UI ──▶ LLM (Nosana / Gemini)
                │                 │  explanation + verification code
                ▼                 ▼
          Daytona sandbox ◀── code_run()  ──(error)──▶ LLM fixes code, retry ≤3
                │
                ▼
        computed result ──▶ LLM judge ──▶ ✅ Verified / ⚠️ Mismatch
```

## Run locally

```bash
pip install -r requirements.txt
export DAYTONA_API_KEY=...      # PowerShell: $env:DAYTONA_API_KEY="..."
export GEMINI_API_KEY=...
# optional: use a model served on Nosana
export NOSANA_URL=https://<your-nosana-endpoint>/v1
export NOSANA_MODEL=<model-name>
streamlit run app.py
```

On Streamlit Community Cloud, set the same keys in **Secrets**.

## What's next

- Photo input (snap a textbook problem)
- Graph rendering from the sandbox for functions / physics motion
- Tutor dashboard: log which problem types the AI gets wrong most often
- Run the explanation model fully on Nosana for low-cost school deployments

---

### 日本語概要
AIの数学解説は計算ミスが多く、生徒には正誤が判断できません。MathCheckは、AIに解説と同時に「検算用のPythonコード」を書かせ、Daytonaのサンドボックスで実際に実行して答えを確かめます。エラー時はAIが自分でコードを修正し、解説と計算結果が食い違えば警告します。
