# Issue tracker: Local Markdown

Issues for this repo live as markdown files in `specs/issues/`.

## Conventions

- One issue per file: `specs/issues/<NN>-<slug>.md`, numbered from `01`
- Triage state is recorded as a `Status:` line near the top of each issue file
  (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under
  a `## Comments` heading
- Step specs (`specs/steps/step-*.md`) serve as PRDs — when a skill says
  "write a PRD", create or update the relevant step spec instead

## When a skill says "publish to the issue tracker"

Create a new file under `specs/issues/` (creating the directory if needed).
Number it sequentially based on existing files.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path
or the issue number directly.
