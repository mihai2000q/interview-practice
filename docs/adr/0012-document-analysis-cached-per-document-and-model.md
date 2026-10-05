# Document analysis is cached per Document and model; structured data is not JSONB

Phase 1 (JD/CV analysis) runs one small call per Document and stores the result as a
`DocumentAnalysis` row attached to that Document (`document_analyses`, one row per
Document), together with the `model` that produced it. The analysis describes the
Document, not the Interview: a CV's skills don't change between stages of the same
`JobApplication`. So a later Interview that uses the same Document reuses the row, unless
its `jd_analysis` model (override or default) differs from the stored one, in which case
the Document is re-analysed and the row overwritten. One row per Document, not one per
(Document, model): alternating models re-runs the analysis each time, which is rare enough
not to justify a wider key.

The alternative was a single combined call over the job title and all three Documents on
every submit, with the output kept only in memory. That repeats work for every stage,
can't be cached per Document, and leaves the skills/topics nowhere for the later phases
(the answer helpers read the analysis on every Q&A turn). The cost of caching is that
phase 1 is split into up to three calls (run in parallel) with a prompt per Document type,
and that the Interview's `domain` now comes from the job description's analysis (else the
CV's) instead of being inferred from the job title as well; with no analysed Document,
phase 2 supplies it.

The analysis is requested through its own endpoint, `PUT /api/documents/:id/analysis`
(a `PUT` because it is idempotent), which the client calls right after an upload, not
inside `POST /api/documents`: the upload stays fast and its "Uploading…" state stays
honest, and the client can show "Analyzing document…" separately. The latency is hidden
behind the candidate filling in the rest of the form. The endpoint takes the Interview's
`jd_analysis` override as an optional body (default model without it). For a Document the
candidate picks rather than uploads, the client calls it only on request: the API reports
the model that made each Document's analysis, the client compares it with the model the form
will use, and offers "Analyze now" when it is missing or from another model. If the
candidate doesn't, `POST /api/interviews` analyses the Document at submit, so the speed-up
applies only when the model wasn't changed after the analysis.

There is no separate cancel. The attachment stays visible while the analysis runs, and the
way to stop it is to remove the attachment (the client abandons the request and deletes the
Document) or to pick another Document. A failure is handled by who is at fault: if the Document
itself is rejected (`422`), the client deletes it and tells the candidate to use a different
file, back at the dropzone; for any other failure (`502`/`503`/`504`, network), which is not
the Document's fault, the client keeps it, shows it as not analyzed with a button to try
again, and otherwise the analysis runs at submit. Abandoning
a request is client-side only: the server can't interrupt a running LLM call, so it
finishes and caches the result (a deleted Document takes its analysis with it). A submit
that overlaps a still-running analysis can duplicate the call, and whichever commits first
wins.

The same decision settled how phase 2 and phase 6 output is stored: **structured data gets
columns or tables, not JSONB**, so the schema shows its shape. The question plan is
`interview_questions` rows, the evaluation rubric is `evaluation_criteria` rows, the STAR
breakdown is five columns on `evaluations`, and the interviewer scores are three
`CHECK`-constrained columns on `interviewer_reviews`. Flat lists of plain strings
(`skills`, `likely_topics`) use Postgres `text[]` columns rather than child tables, which
stay typed and visible; they would become tables if a skill ever needed its own attributes.
The per-Interview phase overrides are `interview_phase_settings` rows, one per overridden
phase with nullable setting columns, rather than a JSONB map: a child table avoids the wide
mostly-null table that a column per phase and setting would be, while keeping the shape
visible. The API keeps the nested `phaseSettingsOverride` object.

A stored analysis is derived from untrusted Document text and feeds later prompts, so its
values are length-bounded and tidied before they are saved.
