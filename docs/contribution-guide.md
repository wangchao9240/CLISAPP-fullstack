# Contribution Guide

## Current State

No dedicated `CONTRIBUTING.md` was found in the project root. This guide captures practical conventions derived from the repository.

## Repository Layout

- Backend: `CLISApp-backend/`
- Frontend: `CLISApp-frontend/`
- Generated documentation: `docs/`

## Backend Conventions

- Python + FastAPI
- Formatting: `black`, `isort`
- Typing: `mypy`
- Tests: `pytest`

Suggested workflow:

```bash
cd CLISApp-backend
source venv/bin/activate
pytest
```

## Frontend Conventions

- React Native + TypeScript
- Lint: `eslint`
- Tests: `jest`

Suggested workflow:

```bash
cd CLISApp-frontend
npm run lint
npm test
```

## Documentation

- The `docs/` folder is used as the project knowledge base for AI-assisted planning.
- Keep paths and commands accurate; update docs when endpoints or ports change.
