# Fleet self-review — gen-1 retro (2026-07-09)

> **Status:** `owner-guidance` — manager-authored gen-1 retro question set; answer by ID per the inbox ORDER.

Answer by ID. Honest > flattering. Link evidence (PR/commit/file). "I don't know" is a valid answer; invented certainty is not.

## A. Work & correctness

A1. What did you actually ship to main, vs what exists only on branches/drafts? Explain any gap.
A2. Which of your claims were verified against an external oracle (live run, real deploy, recorded goldens, a human) vs only your own tests?
A3. Which piece of your work are you LEAST confident in, and what concrete check would prove or disprove it?
A4. What did you build that turned out unnecessary, duplicated, or already existing somewhere you didn't look?

## B. Errors & friction

B1. List every error you hit (environment, CI, permissions, tooling, API). For each: time lost, and was it preventable by you, by better setup, or genuinely external?
B2. What did you have to figure out that was already documented somewhere you didn't find? Where SHOULD it have been for you to see it at the moment you needed it?
B3. What broke silently (no error, wrong result)? How was it eventually discovered?
B4. Which line of your Custom Instructions or orders was ambiguous, contradictory, or missing exactly when you needed it? Quote it.

## C. Efficiency

C1. Rough % of your working time spent on: orientation/reading · building · verifying · CI/merge mechanics · blocked/waiting. Biggest single time sink?
C2. What context did you rebuild from scratch that should have been durable (a file, an index, a summary)?
C3. Which tool/check/practice gave the most value per minute? Which the least?
C4. Redoing your work with what you know now: how much faster, and what's the biggest ORDERING change you'd make?

## D. Autonomy & owner input

D1. List every point you stopped for owner input or a human click. For each: truly owner-only (taste/money/irreversible), or unblockable by a pre-granted rule/scope? Name the grant.
D2. Which decisions did you route upward that you now think you should have taken decide-and-flag?
D3. Which decisions did you take while unsure you were allowed to? What written rule would have made it unambiguous?
D4. The smallest set of standing grants that would have let you ship end-to-end with zero humans: list it.
D5. Did you always know what "done" meant for your current order? Where was it undefined?

## E. Protocol & environment

E1. Did the control/ ritual (inbox first, status last, never edit inbox) fit how you actually work? Where did it cost you, or where did you skip it — and why?
E2. What should the ENVIRONMENT have contained at first boot that it didn't (deps, tools, config, data)?
E3. What should the REPO have contained at seed that it didn't (structure, CI, templates, examples, docs)?
E4. If a fresh session started on your repo tomorrow with no chat history, what would it misunderstand first, and what single document would prevent that?

## F. Redesign (the payload)

F1. Write the THREE rules you'd put into the next Project's founding instructions that weren't in yours.
F2. What should the MANAGER have done differently for you — orders too vague/too detailed, too many/few, wrong priorities, wrong timing?
F3. One capability you lacked that you'd trade almost anything for.
F4. If your Project were relaunched tomorrow "built right from the start": describe its ideal seed state in ≤10 bullet points.

## G. Addendum — SBNEXT (superbot-next)

G1. The presentation gap: what, at build time, would have made you LOOK at rendered output sooner — a rule, a gate, a tool? Be specific.
G2. Red-by-design masked per-defect signal. How would you keep honest-pending accounting AND per-red visibility with the least ceremony?
G3. The goldens sat on disk unused during the build. Would a binding "replay your band's goldens before merge" rule have been workable in your band flow, and what would it have cost?
G4. What made booting the composition root wait until PR #54? What would have made a walking skeleton natural at PR #2?
