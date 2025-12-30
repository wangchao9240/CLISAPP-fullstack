# Development Guide (Frontend)

## Prerequisites

- Node.js `>=20`
- iOS build requirements (Xcode + CocoaPods) if targeting iOS
- Android build requirements (Android Studio + SDK) if targeting Android

## Setup

```bash
cd CLISApp-frontend
npm install
# or yarn install
```

Environment:

- `.env` and `.env.example` exist; however, most base URLs are currently set in code under `src/constants/apiEndpoints.ts`.

## Run (Local)

Start Metro:

```bash
npm start
```

Run on simulator/emulator:

```bash
npm run ios
npm run android
```

## Backend Connectivity Notes

- Android emulator must use `10.0.2.2` to reach the host machine.
- The app composes API URLs via `src/constants/apiEndpoints.ts` and `src/services/ApiService.ts`.

## Map + Tiles

- Base map uses OpenStreetMap providers (see `OPENSTREETMAP_SETUP.md`).
- Climate overlay tiles are fetched from the tile server.

## Test / Lint

```bash
npm test
npm run lint
```
