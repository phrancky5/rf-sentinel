# CLAUDE.md

Coding preferences for this project.

## General

- Make the minimum change needed. Don't refactor surrounding code unless asked.
- Delete dead code rather than leaving it around (e.g. obsolete CLI modules, unused functions).
- Don't add comments unless the logic is genuinely non-obvious.

## File organisation

- Don't create a new file for something that's only used in one place. Keep it in the same file.
- Split modules when a single file mixes distinct concerns (e.g. WebSocket management, REST routes, and entry point all in one file is too much).
- Use thin `__init__.py` / index files as re-export surfaces — put the real logic in focused submodules.
- When splitting causes circular imports, extract shared types into a dedicated `types.py` (or similar) rather than restructuring everything else.

## React / TypeScript

- Extract repeated or complex JSX into named components in the **same file** — don't create a new file unless the component is used in more than one place.
- Extract complex render logic (long canvas draw functions, multi-state returns) into named helper functions in the same file.
- State should live as low as possible. If only one subtree uses a piece of state, own it there — don't prop-drill from a parent that doesn't need it.
- Unify near-identical abstractions (e.g. two broadcast functions that do the same thing → one).

## Python

- Pure data-transform functions (e.g. `downsample_2d`) belong in `dsp/`, not in plotting or runner.

## Git

- Commit messages: one short line, no bullet points, no details.
- Stage only the files relevant to the change.
