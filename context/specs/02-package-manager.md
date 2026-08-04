# Role: Package Manager Decision
This spec records the package manager choices made for this monorepo and the concrete file changes applied to standardize the repository.

## Summary
- Frontend (and overall JS workspace): pnpm (managed via a pnpm workspace at the repo root).
- Backend (Python): pip using `backend/requirements.txt` (no change to Python packaging).

## Decisions
- Use `pnpm` as the single package manager for all JavaScript/TypeScript packages in this mono-repo (root, `frontend`, and `backend` if it contains JS subpackages).
- Continue using `pip` (requirements.txt) for Python dependencies in `backend/`.

## What was changed
- Added: `pnpm-workspace.yaml` at the repo root to declare workspace packages.
- Added: `.npmrc` at the repo root with `package-manager=pnpm` to signal preference.
- Removed: existing npm/yarn lockfiles to avoid mixed lockfile state (examples removed across the repo: `package-lock.json`, `yarn.lock`).

Files created
- [pnpm-workspace.yaml](../pnpm-workspace.yaml)
- [.npmrc](../.npmrc)

Files removed (examples)
- `package-lock.json` (root, frontend, backend)
- `yarn.lock` (root, frontend)

## Install / onboarding commands
Run these once on contributors' machines to get a correct environment:

```bash
corepack enable
corepack prepare pnpm@latest --activate
pnpm install

# Python backend deps
python -m pip install -r backend/requirements.txt
```

## Rationale
- `pnpm` gives deterministic installs, fast dependency resolution, and works well for monorepos via `pnpm-workspace.yaml`.
- Avoids mixed lockfiles which can cause inconsistent dependency trees and CI surprises.

## Notes / Next steps
- CI and developer docs should be updated to reference `pnpm` for JS installs.
- If you want, I can add a short `CONTRIBUTING.md` snippet or automation to reject PRs containing new `package-lock.json`/`yarn.lock` files.
