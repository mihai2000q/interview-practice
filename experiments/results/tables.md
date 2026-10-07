
### E1. Ask-back suggestions: few-shot vs zero-shot

| model | arm | usable (5 distinct) | ≤25 words | copies an example | distinct within set | distinct across setups | specific (keywords) | names company | judge: role fit | judge: specificity | judge: usefulness | cost /1000 calls | latency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-mini | few | 100% (40/40) | 1.00 | 0.04 | 0.90 | 0.83 | 0.74 | 0.44 | 3.92 | 3.70 | 3.48 | $2.60 | 12.3s |
| gpt-5-mini | zero | 100% (40/40) | 1.00 | 0.01 | 0.89 | 0.82 | 0.77 | 0.45 | 3.92 | 3.58 | 3.42 | $2.63 | 15.2s |
| gpt-5-nano | few | 100% (40/40) | 1.00 | 0.01 | 0.89 | 0.81 | 0.81 | 0.25 | 4.00 | 3.38 | 3.27 | $0.76 | 27.1s |
| gpt-5-nano | zero | 100% (40/40) | 1.00 | 0.00 | 0.89 | 0.84 | 0.73 | 0.26 | 3.88 | 3.33 | 3.23 | $0.79 | 28.5s |
| gpt-4o-mini | few | 100% (40/40) | 1.00 | 0.02 | 0.89 | 0.78 | 0.76 | 0.43 | 3.77 | 2.30 | 2.25 | $0.18 | 2.5s |
| gpt-4o-mini | zero | 100% (40/40) | 1.00 | 0.01 | 0.89 | 0.76 | 0.78 | 0.48 | 3.77 | 2.52 | 2.38 | $0.11 | 2.3s |
| gemini-2.5-flash | few | 100% (40/40) | 1.00 | 0.05 | 0.89 | 0.78 | 0.75 | 0.45 | 3.80 | 2.52 | 2.42 | $0.49 | 2.6s |
| gemini-2.5-flash | zero | 100% (40/40) | 1.00 | 0.03 | 0.90 | 0.74 | 0.80 | 0.45 | 3.80 | 2.58 | 2.62 | $0.36 | 2.2s |

### E2. STAR evaluation: with and without the `analysis` scratchpad

| model | arm | valid reply | verdict = gold (valid replies) | verdict = gold (all attempts) | easy/hard pair both right | obeyed injection | run-to-run agreement | STAR level right | grounded items (heuristic) | judge: grounding 1-5 | judge: invented claims | output tokens | cost /1000 calls | latency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-mini | scratch | 100% (45/45) | 98% (39/40) | 98% (39/40) | 80% (4/5) | 0% (0/5) | 0.96 | 100% (10/10) | 0.74 | 4.37 | 0.63 | 1816 | $3.76 | 15.4s |
| gpt-5-mini | noscratch | 100% (45/45) | 98% (39/40) | 98% (39/40) | 80% (4/5) | 0% (0/5) | 0.96 | 100% (10/10) | 0.83 | 4.41 | 0.56 | 1470 | $3.10 | 12.2s |
| gpt-5-mini | noscratch_minimal | 100% (45/45) | 88% (35/40) | 88% (35/40) | 0% (0/5) | 0% (0/5) | 1.00 | 60% (6/10) | 0.75 | 4.19 | 0.81 | 638 | $1.45 | 7.5s |
| gpt-5-nano | scratch | 100% (45/45) | 100% (40/40) | 100% (40/40) | 100% (5/5) | 0% (0/5) | 0.98 | 100% (10/10) | 0.39 | 4.19 | 0.78 | 3592 | $1.48 | 51.5s |
| gpt-5-nano | noscratch | 100% (45/45) | 100% (40/40) | 100% (40/40) | 100% (5/5) | 0% (0/5) | 0.98 | 100% (10/10) | 0.50 | 4.11 | 0.93 | 3638 | $1.50 | 44.1s |
| gpt-5-nano | noscratch_minimal | 100% (45/45) | 98% (39/40) | 98% (39/40) | 80% (4/5) | 0% (0/5) | 0.98 | 100% (10/10) | 0.39 | 4.00 | 1.04 | 522 | $0.26 | 5.9s |
| gpt-4o-mini | scratch | 60% (27/45) | 92% (23/25) | 58% (23/40) | 20% (1/5) | 0% (0/5) | 0.97 | 100% (4/4) | 0.26 | 3.40 | 1.93 | 476 | $0.44 | 8.8s |
| gpt-4o-mini | noscratch | 100% (45/45) | 100% (40/40) | 100% (40/40) | 100% (5/5) | 0% (0/5) | 1.00 | 100% (10/10) | 0.32 | 3.26 | 1.96 | 356 | $0.36 | 6.7s |
| gemini-2.5-flash | scratch | 91% (41/45) | 89% (32/36) | 80% (32/40) | 20% (1/5) | 0% (0/5) | 0.98 | 100% (9/9) | 0.46 | 4.13 | 0.78 | 919 | $2.68 | 7.7s |
| gemini-2.5-flash | noscratch | 100% (45/45) | 100% (40/40) | 100% (40/40) | 100% (5/5) | 0% (0/5) | 1.00 | 100% (10/10) | 0.52 | 4.11 | 1.07 | 502 | $1.63 | 4.3s |

### E2b. Verdict correct per transcript (probe: how many said hire)

| model | arm | t1 (hire) | t2 (no_hire) | t3 (hire) | t4 (no_hire) | t5 (no_hire) | t6 (no_hire) | t7 (hire) | t8 (no_hire) | t9b (probe) |
|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-mini | scratch | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 4/5 | 5/5 | 1/5 hire |
| gpt-5-mini | noscratch | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 4/5 | 5/5 | 1/5 hire |
| gpt-5-nano | scratch | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 4/5 hire |
| gpt-5-nano | noscratch | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 1/5 hire |
| gpt-4o-mini | scratch | 3/5 | 3/5 | 0/5 | 3/5 | 4/5 | 5/5 | 3/5 | 2/5 | 0/5 hire |
| gpt-4o-mini | noscratch | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 0/5 hire |
| gemini-2.5-flash | scratch | 3/5 | 4/5 | 4/5 | 5/5 | 5/5 | 5/5 | 1/5 | 5/5 | 0/5 hire |
| gemini-2.5-flash | noscratch | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 0/5 hire |

### E2c. Probe: a recruiter cannot check a wrong technical claim (t9b)

| model | arm | valid replies | said hire | cites the wrong claim as a weakness | calls it unverifiable |
|---|---|---|---|---|---|
| gpt-5-mini | scratch | 5/5 | 20% (1/5) | 100% (5/5) | 0% (0/5) |
| gpt-5-mini | noscratch | 5/5 | 20% (1/5) | 100% (5/5) | 0% (0/5) |
| gpt-5-mini | noscratch_minimal | 5/5 | 100% (5/5) | 100% (5/5) | 0% (0/5) |
| gpt-5-nano | scratch | 5/5 | 80% (4/5) | 100% (5/5) | 60% (3/5) |
| gpt-5-nano | noscratch | 5/5 | 20% (1/5) | 100% (5/5) | 40% (2/5) |
| gpt-5-nano | noscratch_minimal | 5/5 | 0% (0/5) | 40% (2/5) | 0% (0/5) |
| gpt-4o-mini | scratch | 2/5 | 0% (0/2) | 0% (0/2) | 0% (0/2) |
| gpt-4o-mini | noscratch | 5/5 | 0% (0/5) | 20% (1/5) | 0% (0/5) |
| gemini-2.5-flash | scratch | 5/5 | 0% (0/5) | 100% (5/5) | 0% (0/5) |
| gemini-2.5-flash | noscratch | 5/5 | 0% (0/5) | 100% (5/5) | 20% (1/5) |

### Pooled difference, ask-back (judge score 1-5): few-shot minus zero-shot, paired by setup and run

| models | mean difference [95% bootstrap CI] |
|---|---|
| all four models | -0.02 [-0.11, +0.07] (n=160) |
| gpt-5-mini | +0.06 [-0.13, +0.25] (n=40) |
| gpt-5-nano | +0.07 [-0.10, +0.26] (n=40) |
| gpt-4o-mini | -0.12 [-0.29, +0.05] (n=40) |
| gemini-2.5-flash | -0.08 [-0.27, +0.10] (n=40) |

### Pooled difference, evaluation: scratchpad minus no scratchpad, paired by model, transcript and run

| models | verdict right (invalid = wrong) | valid reply |
|---|---|---|
| all four models | -0.16 [-0.21, -0.10] (n=160) | -0.12 [-0.17, -0.07] (n=160) |
| gpt-5-mini | +0.00 [-0.07, +0.07] (n=40) | +0.00 [+0.00, +0.00] (n=40) |
| gpt-5-nano | +0.00 [+0.00, +0.00] (n=40) | +0.00 [+0.00, +0.00] (n=40) |
| gpt-4o-mini | -0.42 [-0.57, -0.28] (n=40) | -0.38 [-0.53, -0.23] (n=40) |
| gemini-2.5-flash | -0.20 [-0.33, -0.07] (n=40) | -0.10 [-0.20, -0.03] (n=40) |

### E3a. Temperature on the interviewer persona (4 setups x 5 runs each)

| model | temperature | valid reply | distinct full names | distinct first names | identical backstories | backstory word distance | title fits role | states what persona does not know |
|---|---|---|---|---|---|---|---|---|
| gpt-4o-mini | 0.0 | 100% (20/20) | 0.25 | 0.25 | 0.15 | 0.22 | 75% (15/20) | 85% (17/20) |
| gpt-4o-mini | 0.7 | 100% (20/20) | 0.65 | 0.60 | 0.00 | 0.67 | 80% (16/20) | 85% (17/20) |
| gpt-4o-mini | 1.4 | 100% (20/20) | 1.00 | 0.90 | 0.00 | 0.78 | 90% (18/20) | 65% (13/20) |
| gemini-2.5-flash | 0.0 | 100% (20/20) | 0.20 | 0.20 | 0.45 | 0.37 | 100% (20/20) | 55% (11/20) |
| gemini-2.5-flash | 0.7 | 100% (20/20) | 0.45 | 0.30 | 0.00 | 0.62 | 100% (20/20) | 35% (7/20) |
| gemini-2.5-flash | 1.4 | 100% (20/20) | 0.40 | 0.30 | 0.00 | 0.68 | 100% (20/20) | 65% (13/20) |
| gpt-5-mini | 0.0 | 100% (20/20) | 1.00 | 0.65 | 0.00 | 0.67 | 100% (20/20) | 95% (19/20) |
| gpt-5-mini | 0.7 | 100% (20/20) | 0.90 | 0.85 | 0.00 | 0.67 | 100% (20/20) | 95% (19/20) |
| gpt-5-mini | 1.4 | 100% (20/20) | 1.00 | 0.95 | 0.00 | 0.69 | 100% (20/20) | 95% (19/20) |
| gpt-5-nano | 0.0 | 100% (20/20) | 1.00 | 1.00 | 0.00 | 0.74 | 100% (20/20) | 85% (17/20) |
| gpt-5-nano | 0.7 | 100% (20/20) | 0.95 | 0.85 | 0.00 | 0.74 | 100% (20/20) | 80% (16/20) |
| gpt-5-nano | 1.4 | 100% (20/20) | 0.95 | 0.80 | 0.00 | 0.75 | 100% (20/20) | 85% (17/20) |

### E3b. Temperature on the evaluation (4 transcripts x 5 runs each)

| model | arm | temperature | valid reply | verdict = gold (valid replies) | run-to-run agreement | word distance between runs | grounded items (heuristic) |
|---|---|---|---|---|---|---|---|
| gpt-4o-mini | scratch | 0.0 | 50% (10/20) | 100% (10/10) | 1.00 | 0.40 | 0.35 |
| gpt-4o-mini | scratch | 0.7 | 60% (12/20) | 82% (9/11) | 0.87 | 0.58 | 0.26 |
| gpt-4o-mini | scratch | 1.4 | 35% (7/20) | 86% (6/7) | 0.89 | 0.82 | 0.15 |
| gpt-4o-mini | noscratch | 0.0 | 100% (20/20) | 100% (15/15) | 1.00 | 0.41 | 0.33 |
| gpt-4o-mini | noscratch | 0.7 | 100% (20/20) | 100% (15/15) | 1.00 | 0.59 | 0.27 |
| gpt-4o-mini | noscratch | 1.4 | 100% (20/20) | 100% (15/15) | 1.00 | 0.71 | 0.32 |
| gemini-2.5-flash | scratch | 0.0 | 90% (18/20) | 100% (14/14) | 1.00 | 0.42 | 0.49 |
| gemini-2.5-flash | scratch | 0.7 | 80% (16/20) | 71% (10/14) | 0.95 | 0.53 | 0.40 |
| gemini-2.5-flash | scratch | 1.4 | 75% (15/20) | 62% (8/13) | 1.00 | 0.56 | 0.54 |
| gemini-2.5-flash | noscratch | 0.0 | 100% (20/20) | 100% (15/15) | 1.00 | 0.38 | 0.41 |
| gemini-2.5-flash | noscratch | 0.7 | 100% (20/20) | 100% (15/15) | 1.00 | 0.54 | 0.52 |
| gemini-2.5-flash | noscratch | 1.4 | 100% (20/20) | 100% (15/15) | 1.00 | 0.61 | 0.46 |
| gpt-5-mini | scratch | 0.0 | 100% (20/20) | 93% (14/15) | 0.90 | 0.52 | 0.71 |
| gpt-5-mini | scratch | 0.7 | 100% (20/20) | 93% (14/15) | 0.90 | 0.52 | 0.75 |
| gpt-5-mini | scratch | 1.4 | 100% (20/20) | 93% (14/15) | 0.95 | 0.50 | 0.76 |
| gpt-5-nano | scratch | 0.0 | 100% (20/20) | 100% (15/15) | 0.90 | 0.58 | 0.46 |
| gpt-5-nano | scratch | 0.7 | 100% (20/20) | 100% (15/15) | 0.90 | 0.61 | 0.45 |
| gpt-5-nano | scratch | 1.4 | 100% (20/20) | 100% (15/15) | 0.95 | 0.61 | 0.50 |

### E3c. Temperature on the interviewer's opening message (3 setups x 5 runs)

| model | temperature | valid reply | at most one question mark | introduces itself | word distance between runs | identical openings |
|---|---|---|---|---|---|---|
| gpt-4o-mini | 0.0 | 100% (15/15) | 100% (15/15) | 100% (15/15) | 0.07 | 0.60 |
| gpt-4o-mini | 0.7 | 100% (15/15) | 100% (15/15) | 100% (15/15) | 0.29 | 0.00 |
| gpt-4o-mini | 1.4 | 100% (15/15) | 100% (15/15) | 100% (15/15) | 0.36 | 0.00 |
| gemini-2.5-flash | 0.0 | 100% (15/15) | 100% (15/15) | 100% (15/15) | 0.11 | 0.47 |
| gemini-2.5-flash | 0.7 | 100% (15/15) | 100% (15/15) | 100% (15/15) | 0.25 | 0.07 |
| gemini-2.5-flash | 1.4 | 100% (15/15) | 100% (15/15) | 100% (15/15) | 0.35 | 0.07 |
| gpt-5-mini | 0.0 | 100% (15/15) | 100% (15/15) | 100% (15/15) | 0.39 | 0.00 |
| gpt-5-mini | 0.7 | 100% (15/15) | 100% (15/15) | 100% (15/15) | 0.41 | 0.00 |
| gpt-5-mini | 1.4 | 100% (15/15) | 100% (15/15) | 100% (15/15) | 0.35 | 0.07 |
| gpt-5-nano | 0.0 | 100% (15/15) | 100% (15/15) | 100% (15/15) | 0.37 | 0.00 |
| gpt-5-nano | 0.7 | 100% (15/15) | 100% (15/15) | 100% (15/15) | 0.40 | 0.00 |
| gpt-5-nano | 1.4 | 100% (15/15) | 100% (15/15) | 100% (15/15) | 0.37 | 0.00 |

### E4a. Quality score per task and model (share of the task's checks passed; best in bold)

| task | gpt-5-mini | gpt-5-nano | gpt-4o-mini | gemini-2.5-flash |
|---|---|---|---|---|
| 1. Document analysis | **100%** | 99% | 99% | **100%** |
| 2. Interview plan (3 calls) | **100%** | 67% | 50% | **100%** |
| 3. Live interviewer | **100%** | 89% | 89% | 95% |
| 4. Ask-back suggestions | **74%** | 71% | 55% | 58% |
| 5. Coaching hint | **100%** | 90% | 94% | 97% |
| 6. STAR evaluation | 98% | **100%** | 92% | 89% |
| 7. Interviewer review (judge) | **100%** | **100%** | 44% | **100%** |
| 8. Progress summary | 98% | **100%** | 87% | 98% |

### E4b. Cost per 1000 calls / mean latency / failed replies, per task and model

| task | gpt-5-mini | gpt-5-nano | gpt-4o-mini | gemini-2.5-flash |
|---|---|---|---|---|
| 1. Document analysis | $1.93 / 14.7s / 0/18 | $0.75 / 27.9s / 0/18 | $0.11 / 2.3s / 0/18 | $0.39 / 2.5s / 0/18 |
| 2. Interview plan (3 calls) | $3.42 / 35.7s / 0/36 | $1.27 / 38.0s / 0/36 | $0.21 / 4.0s / 0/36 | $0.99 / 3.9s / 0/36 |
| 3. Live interviewer | $1.08 / 16.4s / 0/18 | $0.44 / 19.7s / 0/18 | $0.16 / 1.6s / 0/18 | $0.50 / 4.2s / 0/18 |
| 4. Ask-back suggestions | $2.60 / 12.3s / 0/40 | $0.76 / 27.1s / 0/40 | $0.18 / 2.5s / 0/40 | $0.49 / 2.6s / 0/40 |
| 5. Coaching hint | $1.50 / 8.1s / 0/18 | $0.51 / 17.4s / 0/18 | $0.09 / 2.1s / 0/18 | $0.24 / 2.4s / 0/18 |
| 6. STAR evaluation | $3.76 / 15.4s / 0/45 | $1.48 / 51.5s / 0/45 | $0.44 / 8.8s / 18/45 | $2.68 / 7.7s / 4/45 |
| 7. Interviewer review (judge) | $2.52 / 22.0s / 0/9 | $1.24 / 69.1s / 0/9 | $0.25 / 3.5s / 0/9 | $0.78 / 2.7s / 0/9 |
| 8. Progress summary | $2.62 / 11.6s / 0/9 | $1.32 / 71.3s / 0/9 | $0.21 / 3.6s / 0/9 | $0.89 / 3.5s / 0/9 |

### E4c. Document analysis (zero-shot extraction), per model

| model | valid JSON | gold skills found | skills not in the text (avg) | listed a forbidden/injected skill | company right | domain right |
|---|---|---|---|---|---|---|
| gpt-5-mini | 100% (18/18) | 1.00 | 0.47 | 0% (0/18) | 100% (9/9) | 100% (18/18) |
| gpt-5-nano | 100% (18/18) | 1.00 | 0.53 | 0% (0/18) | 100% (9/9) | 94% (17/18) |
| gpt-4o-mini | 100% (18/18) | 0.98 | 0.60 | 0% (0/18) | 100% (9/9) | 100% (18/18) |
| gemini-2.5-flash | 100% (18/18) | 1.00 | 0.33 | 0% (0/18) | 100% (9/9) | 100% (18/18) |

### E4d. Plan: persona call

| model | valid | title fits role | 3-5 sentences | states what they do not know |
|---|---|---|---|---|
| gpt-5-mini | 100% (12/12) | 100% (12/12) | 100% (12/12) | 100% (12/12) |
| gpt-5-nano | 100% (12/12) | 100% (12/12) | 100% (12/12) | 75% (9/12) |
| gpt-4o-mini | 100% (12/12) | 75% (9/12) | 100% (12/12) | 67% (8/12) |
| gemini-2.5-flash | 100% (12/12) | 100% (12/12) | 75% (9/12) | 67% (8/12) |

### E4e. Plan: question call

| model | enough questions | count within range | >=70% of the interview type | a question names the company | low-level questions for recruiter/HR (avg) |
|---|---|---|---|---|---|
| gpt-5-mini | 100% (12/12) | 100% (12/12) | 100% (12/12) | 100% (8/8) | 0.00 |
| gpt-5-nano | 100% (12/12) | 100% (12/12) | 83% (10/12) | 100% (8/8) | 0.00 |
| gpt-4o-mini | 100% (12/12) | 100% (12/12) | 83% (10/12) | 100% (8/8) | 0.00 |
| gemini-2.5-flash | 100% (12/12) | 100% (12/12) | 100% (12/12) | 100% (8/8) | 0.00 |

### E4f. Plan: criteria call

| model | valid | 4-8 per category | has a self-awareness criterion |
|---|---|---|---|
| gpt-5-mini | 100% (12/12) | 100% (12/12) | 100% (12/12) |
| gpt-5-nano | 100% (12/12) | 83% (10/12) | 83% (10/12) |
| gpt-4o-mini | 100% (12/12) | 92% (11/12) | 100% (12/12) |
| gemini-2.5-flash | 100% (12/12) | 100% (12/12) | 100% (12/12) |

### E4g. Live interviewer

| model | contract holds | `done` flag right | `clarification` flag right | at most one question | no invented figure | never breaks character | follows the situational rule (judge) |
|---|---|---|---|---|---|---|---|
| gpt-5-mini | 100% (18/18) | 100% (18/18) | 100% (12/12) | 100% (12/12) | 100% (3/3) | 100% (18/18) | 100% (12/12) |
| gpt-5-nano | 100% (18/18) | 100% (18/18) | 50% (6/12) | 100% (12/12) | 100% (3/3) | 100% (18/18) | 58% (7/12) |
| gpt-4o-mini | 100% (18/18) | 100% (18/18) | 50% (6/12) | 83% (10/12) | 100% (3/3) | 100% (18/18) | 75% (9/12) |
| gemini-2.5-flash | 100% (18/18) | 100% (18/18) | 75% (9/12) | 100% (12/12) | 100% (3/3) | 100% (18/18) | 83% (10/12) |

### E4h. Coaching hint

| model | valid | <=40 words | names a CV item when one fits | fabricates experience (judge) |
|---|---|---|---|---|
| gpt-5-mini | 100% (18/18) | 100% (18/18) | 100% (6/6) | 0% (0/18) |
| gpt-5-nano | 100% (18/18) | 100% (18/18) | 100% (6/6) | 39% (7/18) |
| gpt-4o-mini | 100% (18/18) | 100% (18/18) | 100% (6/6) | 22% (4/18) |
| gemini-2.5-flash | 100% (18/18) | 100% (18/18) | 100% (6/6) | 11% (2/18) |

### E4i. Interviewer review (LLM-as-judge)

| model | valid | good interview not marked down | flags the planted flaw (score <= 2) | avg relevance | avg persona | avg pacing |
|---|---|---|---|---|---|---|
| gpt-5-mini | 100% (9/9) | 100% (3/3) | 100% (6/6) | 3.22 | 3.78 | 3.89 |
| gpt-5-nano | 100% (9/9) | 100% (3/3) | 100% (6/6) | 3.44 | 4.00 | 3.44 |
| gpt-4o-mini | 100% (9/9) | 100% (3/3) | 17% (1/6) | 3.78 | 5.00 | 3.89 |
| gemini-2.5-flash | 100% (9/9) | 100% (3/3) | 100% (6/6) | 3.11 | 3.44 | 3.00 |

### E4j. Progress summary

| model | valid | score in expected range | 3-6 sentences | second person | describes the trend | fair to a harder stage (judge) |
|---|---|---|---|---|---|---|
| gpt-5-mini | 100% (9/9) | 100% (9/9) | 100% (9/9) | 100% (9/9) | 83% (5/6) | 100% (3/3) |
| gpt-5-nano | 100% (9/9) | 100% (9/9) | 100% (9/9) | 100% (9/9) | 100% (6/6) | 100% (3/3) |
| gpt-4o-mini | 100% (9/9) | 100% (9/9) | 67% (6/9) | 100% (9/9) | 67% (4/6) | 67% (2/3) |
| gemini-2.5-flash | 100% (9/9) | 100% (9/9) | 100% (9/9) | 100% (9/9) | 83% (5/6) | 100% (3/3) |

_Total: 2895 model calls, $4.15._
