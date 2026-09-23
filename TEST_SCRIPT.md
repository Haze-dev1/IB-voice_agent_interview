# Mock Interview — test script

Read this aloud. The questions come in a fixed order, so you can follow along.
Use **headphones** for the first run (speakers are a separate test, see §6).

---

## Q1 — Depreciation *(answer this one well)*

> "Walk me through how a 10 dollar increase in depreciation expense affects the three financial statements."

**Say:**

> "Depreciation goes up by ten, so EBIT falls by ten and pre-tax income falls by ten. At a twenty-one percent tax rate, taxes drop by two dollars ten, so net income falls by seven dollars ninety. On the cash flow statement you start with net income down seven ninety, add back the full ten of depreciation, so cash is up two dollars ten. On the balance sheet, cash is up two ten, PP&E is down ten, so assets are down seven ninety, and retained earnings is down seven ninety. Both sides balance."

✅ **Should:** acknowledge briefly, then move to Q2.
❌ **Bug if:** it asks the depreciation question again, or follows up as if you said nothing.

---

## Q2 — Why banking *(answer this one badly, on purpose)*

> "Why investment banking? What draws you to this career?"

**Say — then stop talking:**

> "I don't know really. It seems like a good job."

✅ **Should:** ask a **follow-up** that digs for more — not re-read the question.
❌ **Bug if:** it says "good, that covers it" and moves on. That means answer-scoring is dead again.

**Then give it a real answer:**

> "I've always been drawn to how companies get valued and how deals actually get done. I want to work on transactions that change a company's direction, and I want the reps — the modelling, the client work, the pace."

✅ **Should:** accept it and move to Q3.

---

## Q3 — WACC *(test the mid-answer pause)*

> "Explain what WACC is and when you would use it in a DCF valuation."

**Say this, then pause ~3 seconds mid-answer, then finish:**

> "WACC is the weighted average cost of capital. It blends the cost of equity and the after-tax cost of debt…"

*(pause, look thoughtful, then continue)*

> "…weighted by their share of the capital structure. You use it as the discount rate on unlevered free cash flows, because those cash flows belong to both debt and equity holders."

✅ **Should:** wait for you and take the whole answer.
❌ **Bug if:** it cuts in during the pause and treats the first half as your full answer.

---

## Q4 — Resume *(test mute)*

> "Walk me through your resume."

**Before answering, hit mute and talk for ~5 seconds.** Then unmute and answer normally — anything about yourself, 20 seconds is plenty.

✅ **Should:** stay quiet while muted, then take your real answer. If it reacts at all, it should say it didn't catch you — not score you badly.
❌ **Bug if:** it moves on, or treats the silence as a weak answer.

---

## Q5 — LBO *(answer normally, then let it finish)*

> "What are the key characteristics of a good LBO candidate?"

**Say:**

> "Stable, predictable cash flows so the company can service debt. A strong market position. Low existing leverage. Real levers to create value — margin or growth. And a clear exit inside three to seven years."

✅ **Should:** wrap up and give **spoken feedback** — strengths and areas to improve — then end.
❌ **Bug if:** feedback is generic praise with no reference to how you actually did.

---

## 6. Optional: the speaker test

Re-run Q1 with **speakers instead of headphones**, turned up.

✅ **Should:** ignore its own voice and finish its question.
❌ **Bug if:** it stutters, fragments, or interrupts itself — that's the barge-in problem back.

---

## Watch on screen while you talk

- **Your own captions.** When you speak you should see `You: …` lines appear. **This is the one thing never verified** — no mic in the test environment. If they never show, say so.
- **Captions track the voice.** They should advance roughly in time with what you're hearing — not dump the whole turn at once, not lag far behind.
- **Question counter** top-left should climb 1→5 and never jump or repeat.
- **Never** should you hear it say a tool name, a field name, or narrate its own reasoning
  ("the candidate gave a minimal answer", "should_follow_up false", "per protocol").
