# Public Benchmarks for the App's Models

How the models this app can run on rank on the public benchmarks, what those rankings measure,
and how they relate to [the app's own benchmark](./prompt-benchmark.md). It covers the four
usable models of the app's allow-lists (`gpt-5-mini`, `gpt-5-nano`, `gpt-4o-mini`,
`gemini-2.5-flash`) and `gemini-3.5-flash-lite`, which is an allowed judge model. The image
model is out of scope.

**Figures are as of 2026-10-08**, when the pages were read. Leaderboards change, so treat the
numbers as a dated snapshot and re-read the sources (listed at the end) before relying on them.
Every figure comes from the leaderboard's or vendor's own page.

## The short answer

On general capability, by the public index with the widest coverage of these models
(Artificial Analysis Intelligence Index), the app's models rank:

| # | Model | Intelligence Index | In the app |
|---|---|---|---|
| 1 | `gemini-3.5-flash-lite` | 22 | judge phase only; **fails with the app's current OpenRouter key** (`404`, a guardrail on the key's workspace) |
| 2 | `gpt-5-mini` (high effort) | 17 | default for every interview phase |
| 3 | `gpt-5-nano` (high effort) | 13 | selectable for every phase |
| 4 | `gemini-2.5-flash` | 10 | default judge |
| 5 | `gpt-4o-mini` | 7 | selectable for the interview phases |

For scale, the index's top score is 58 (Claude Opus 5.5), so all five sit in the lower part of
the range. Three of the scores are labeled "estimated" on their pages (`gpt-5-nano`,
`gpt-4o-mini`, `gemini-2.5-flash`).

**This ordering matches what the app's own benchmark found, with exceptions:**

| | Public index | The app's own benchmark |
|---|---|---|
| Best overall | `gemini-3.5-flash-lite`, then `gpt-5-mini` | `gpt-5-mini` (not tested: `gemini-3.5-flash-lite`, which the app's key cannot call) |
| Worst | `gpt-4o-mini` | `gpt-4o-mini` (failed as a judge, 40% invalid evaluations) |
| `gpt-5-nano` vs `gemini-2.5-flash` | `gpt-5-nano` ahead (13 vs 10) | mixed: `gpt-5-nano` more accurate on the evaluation (100% vs 89%); `gemini-2.5-flash` passed the plan checks (100% vs 67%), fabricated less in hints (2 of 18 vs 7 of 18) and was as good a judge, much faster |
| Speed | `gemini-2.5-flash` and `gpt-4o-mini` respond in under a second; the `gpt-5` models take a minute | the same order, with much shorter times at the app's default effort |

So the public numbers are a reasonable first guide to *which model is stronger*, and a poor
guide to *which model works for the app's prompts*: the failures the app's benchmark found
(a rejected reply format, a rule not followed, invented experience) are not on any public
leaderboard.

## The models side by side

From each model's Artificial Analysis page (index v4.3.2 where the page states it):

| | `gemini-3.5-flash-lite` | `gpt-5-mini` | `gpt-5-nano` | `gemini-2.5-flash` | `gpt-4o-mini` |
|---|---|---|---|---|---|
| Intelligence Index | 22 | 17 | 13 | 10 | 7 |
| Variant scored | reasoning | high reasoning | high reasoning | non-reasoning | non-reasoning |
| Price per 1M tokens, in / out | $0.30 / $2.50 | $0.25 / $2.00 | $0.05 / $0.40 | $0.30 / $2.50 | $0.15 / $0.60 |
| Blended price per 1M | n/a | $0.27 | $0.05 | $0.33 | $0.14 |
| Output speed (tokens/s) | 347 | 125 | 131 | 193 | 101 |
| Time to first token | 8.75 s | 60.2 s | 89.9 s | 0.44 s | 0.83 s |
| Context window | 1M | 400k | 400k | 1M | 128k |
| Knowledge cutoff | n/a | May 2024 | May 2024 | Jan 2025 | Oct 2023 |
| Released | July 2026 | Aug 2025 | Aug 2025 | May 2025 | July 2024 |
| Marked deprecated by Artificial Analysis | no | yes (successor: GPT-5.4 mini) | yes (successor: GPT-5.4 nano) | yes | yes (successor: GPT-5 mini) |

How to read the table:

- **"Blended" price** is Artificial Analysis's figure for a 7:2:1 mix of cached input, input and
  output tokens.
- **The reasoning models' time to first token** (60 s and 90 s) includes thinking time at the
  high setting. In the app's own runs at the provider's default effort the whole call took 8 to
  36 s for `gpt-5-mini` and 17 to 71 s for `gpt-5-nano`, depending on the task, so the order
  matches and the numbers do not.
- **Cost to run the index:** Artificial Analysis lists $0.05 per task for `gpt-5-mini` and $0.19
  for `gemini-3.5-flash-lite`, although their per-token prices are similar. The pages do not say
  why, so the per-token price alone should not be read as the cost of using a model.
- **"Deprecated" is Artificial Analysis's word for superseded**, not a shutdown. OpenAI's
  deprecation page lists no shutdown date for `gpt-4o-mini`, `gpt-5-mini` or `gpt-5-nano`, and
  Google's lists none for `gemini-2.5-flash`, though Google recommends newer models for new
  projects (3.5 Flash-Lite or 3.8 Flash).

## Other leaderboards

**Arena (human preference, text leaderboard, updated 2026-10-02; 413 models, 8,626,731 votes).**
Only the Gemini models appear in the part of the list that could be read (the first 150 rows):

| Model | Rank | Score |
|---|---|---|
| `gemini-3.5-flash-lite` | 71 | 1455 ± 4 (35,763 votes) |
| `gemini-2.5-flash` | 148 | 1409 ± 2 (125,012 votes) |

`gpt-5-mini`, `gpt-5-nano` and `gpt-4o-mini` were not in those 150 rows, so they rank lower than
148 or are listed elsewhere. This document gives no Arena score for them rather than guess. For
scale, the leader scores 1525 and the top six are between 1501 and 1525.

**Epoch Capabilities Index.** Epoch's table did not load for these models when read (the page
fetches its data in the browser), so there is nothing to report. Epoch only includes a model with
at least four benchmark evaluations, so a model without one is absent.

## What the numbers mean for the app

1. **The scores are for specific settings, not what the app runs.** The index scores `gpt-5-mini`
   and `gpt-5-nano` at **high** reasoning effort. The app sends no effort setting, so the
   provider's default applies. In the app's benchmark, lowering `gpt-5-mini` to *minimal* effort
   cost it accuracy (88% vs 98%), so the setting matters, and the public score is not a
   measurement of the app's configuration. Artificial Analysis also scores `gemini-2.5-flash`
   as a *non-reasoning* model; whether the model the app reaches through OpenRouter thinks by
   default was not verified.
2. **A higher general score does not mean a better fit.** `gemini-3.5-flash-lite` scores highest
   here and is the only one of the five that the app's benchmark could not test: OpenRouter
   answers `404` ("Model blocked by guardrail") for it with the key the app runs on, a setting of
   that key's OpenRouter workspace. The app still offers it as a judge option, and picking it
   makes the review call fail; a failed review is logged and dropped, so the interview just has
   no review. Allowing the model in the OpenRouter guardrail would fix that. Its published score
   and speed (347 tokens/s) are promising for a judge, but the app's own judge test (flaw
   detection on planted cases) has not been run on it.
3. **Most of the app's models are one generation behind their vendors.** Artificial Analysis names
   GPT-5.4 mini and GPT-5.4 nano as successors of `gpt-5-mini` and `gpt-5-nano`, and Google
   recommends 3.5 Flash-Lite or 3.8 Flash over `gemini-2.5-flash`. Of those, only 3.5 Flash-Lite
   is in an allow-list (the judge's, and not callable with the app's current key); GPT-5.4 mini and nano
   and 3.8 Flash are neither allowed nor tested. Adding one to `experiments/run.py` and re-running
   the same cases would show whether a newer model does better on the app's own tasks; the
   cached results mean the models already tested are not re-paid for.
4. **Cheaper is not always worse here.** `gpt-5-nano` costs a fifth of `gpt-5-mini` per token and
   was as accurate on the evaluation in the app's benchmark, though about three times slower and
   fabricating experience in more coaching hints. Which is "better" depends on whether a task
   tolerates the slowness and the rule violations. A public index cannot say.

## Limits of these rankings

- **Leaderboards measure different things.** An aggregate index, a vote on style and an exam
  score can order the same models differently. For this app's models the public data is thin:
  one index covers all five, Arena covers two of them (in the part that could be read), and Epoch's
  index none.
- **Aggregates hide their composition.** The index averages ten evaluations (agentic tasks,
  coding, general knowledge and scientific reasoning, at 25% each); a model that is strong on
  one part and weak on another can land anywhere.
- **Human-preference voting can be skewed.** "The Leaderboard Illusion" (Singh et al., NeurIPS
  2025) reports that a few providers privately tested many variants before release and
  received a larger share of the Arena's data, and that access to Arena data improved scores on
  the Arena's own distribution by up to 112% (relative). These are the authors' findings about
  the 2025 platform. Treat small gaps as noise.
- **Older models are measured less.** The three Artificial Analysis pages that mark scores as
  "estimated" also say individual evaluation scores are "not publicly available", so they can be
  compared on the index only.
- **A public benchmark is not your task.** The strongest argument for the app's own benchmark
  is that the failures that mattered were not on any public leaderboard.

## Sources

- Artificial Analysis model pages:
  [gemini-3.5-flash-lite](https://artificialanalysis.ai/models/gemini-3-5-flash-lite),
  [gpt-5-mini](https://artificialanalysis.ai/models/gpt-5-mini),
  [gpt-5-nano](https://artificialanalysis.ai/models/gpt-5-nano),
  [gemini-2.5-flash](https://artificialanalysis.ai/models/gemini-2-5-flash),
  [gpt-4o-mini](https://artificialanalysis.ai/models/gpt-4o-mini); and its
  [Intelligence Index methodology](https://artificialanalysis.ai/evaluations/artificial-analysis-intelligence-index)
  and [models leaderboard](https://artificialanalysis.ai/leaderboards/models) (for the top score)
- [Arena text leaderboard](https://arena.ai/leaderboard/text) (formerly lmarena.ai)
- [Epoch AI benchmarks hub](https://epoch.ai/benchmarks/eci)
- [The Leaderboard Illusion](https://arxiv.org/abs/2504.20879), Singh et al.
- [OpenAI deprecations](https://developers.openai.com/api/docs/deprecations) and
  [Google Gemini API deprecations](https://ai.google.dev/gemini-api/docs/deprecations)

To refresh: re-read the pages above, replace the tables and update the dates at the top.
