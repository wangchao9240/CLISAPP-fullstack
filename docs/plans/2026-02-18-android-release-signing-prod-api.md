# Android Release Signing + Production API Configuration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Configure Android release signing and production API endpoints with minimal, secure changes.

**Architecture:** Use Gradle signing configs sourced from `android/gradle.properties`, keep keystore out of git, and load production URLs via `react-native-config` for release builds while preserving local dev defaults.

**Tech Stack:** React Native, Gradle (Android), react-native-config

---

### Task 1: Prepare a clean worktree and baseline

**Files:**
- Verify: `CLISApp-frontend/android/app/build.gradle`
- Verify: `CLISApp-frontend/src/constants/apiEndpoints.ts`
- Verify: `CLISApp-frontend/.env`
- Verify: `.gitignore`

**Step 1: Create a dedicated worktree (if not already)**

Run: `git worktree add ../CLISAPP-openmeteo-signing feature/migrate-to-openmeteo`
Expected: New worktree with clean status

**Step 2: Confirm current signing and env config**

Run: `sed -n '1,200p' CLISApp-frontend/android/app/build.gradle`
Expected: `signingConfig signingConfigs.debug` in release

**Step 3: Confirm current API endpoint logic**

Run: `sed -n '1,200p' CLISApp-frontend/src/constants/apiEndpoints.ts`
Expected: only `API_BASE_URL`/`TILE_SERVER_URL` env overrides

**Step 4: Commit checkpoint (optional)**

Run:
```bash
git status -sb
```
Expected: clean tree

---

### Task 2: Add release keystore generation script

**Files:**
- Create: `CLISApp-frontend/scripts/generate-keystore.sh`

**Step 1: Create scripts folder**

Run: `mkdir -p CLISApp-frontend/scripts`
Expected: directory exists

**Step 2: Add the script**

```bash
#!/bin/bash
# Generate CLISApp release keystore
# Usage: bash scripts/generate-keystore.sh
keytool -genkeypair -v \
  -storetype PKCS12 \
  -keystore android/app/clisapp-release.keystore \
  -alias clisapp \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -dname "CN=CLISApp, OU=Development, O=QUT, L=Brisbane, ST=Queensland, C=AU" \
  -storepass clisapp2024 \
  -keypass clisapp2024

echo "Keystore generated: android/app/clisapp-release.keystore"
```

**Step 3: Make it executable**

Run: `chmod +x CLISApp-frontend/scripts/generate-keystore.sh`
Expected: file is executable

**Step 4: Commit**

```bash
git add CLISApp-frontend/scripts/generate-keystore.sh
git commit -m "chore(android): add release keystore generator"
```

---

### Task 3: Configure release signing in Gradle

**Files:**
- Modify: `CLISApp-frontend/android/app/build.gradle`
- Modify: `CLISApp-frontend/android/gradle.properties`
- Verify: `.gitignore`

**Step 1: Add release signing properties**

Append to `CLISApp-frontend/android/gradle.properties`:

```properties
CLISAPP_RELEASE_STORE_FILE=clisapp-release.keystore
CLISAPP_RELEASE_KEY_ALIAS=clisapp
CLISAPP_RELEASE_STORE_PASSWORD=clisapp2024
CLISAPP_RELEASE_KEY_PASSWORD=clisapp2024
```

**Step 2: Add release signingConfig**

In `CLISApp-frontend/android/app/build.gradle` `signingConfigs` block:

```gradle
release {
    storeFile file(CLISAPP_RELEASE_STORE_FILE)
    storePassword CLISAPP_RELEASE_STORE_PASSWORD
    keyAlias CLISAPP_RELEASE_KEY_ALIAS
    keyPassword CLISAPP_RELEASE_KEY_PASSWORD
}
```

**Step 3: Point release build to release signing**

In `buildTypes.release`:

```gradle
signingConfig signingConfigs.release
```

**Step 4: Confirm keystore ignore rules**

Check `.gitignore` contains:
- `*.keystore`
- `!debug.keystore`

If already present, do not change.

**Step 5: Commit**

```bash
git add CLISApp-frontend/android/app/build.gradle CLISApp-frontend/android/gradle.properties .gitignore
git commit -m "build(android): configure release signing"
```

---

### Task 4: Configure production API envs and release env file

**Files:**
- Modify: `CLISApp-frontend/src/constants/apiEndpoints.ts`
- Modify: `CLISApp-frontend/android/app/build.gradle`
- Create: `CLISApp-frontend/.env.production`
- Modify: `CLISApp-frontend/.env`

**Step 1: Load `.env.production` for release**

Update `project.ext.envConfigFiles` in `CLISApp-frontend/android/app/build.gradle`:

```gradle
project.ext.envConfigFiles = [
    debug: ".env",
    release: ".env.production"
]
```

**Step 2: Prefer production envs in API resolver**

In `CLISApp-frontend/src/constants/apiEndpoints.ts`:
- Check `Config.PRODUCTION_API_URL` and `Config.PRODUCTION_TILE_URL` first
- Fall back to existing `API_BASE_URL` / `TILE_SERVER_URL` or platform-specific dev defaults

**Step 3: Add `.env.production` template**

Create `CLISApp-frontend/.env.production`:

```env
# Production configuration - set real server IP/hostname
PRODUCTION_API_URL=http://YOUR_SERVER_IP:8080
PRODUCTION_TILE_URL=http://YOUR_SERVER_IP:8000
```

**Step 4: Keep production vars commented in `.env`**

Append to `CLISApp-frontend/.env`:

```env
# Production API Configuration (Release)
# PRODUCTION_API_URL=http://YOUR_SERVER_IP:8080
# PRODUCTION_TILE_URL=http://YOUR_SERVER_IP:8000
```

**Step 5: Commit**

```bash
git add CLISApp-frontend/android/app/build.gradle CLISApp-frontend/src/constants/apiEndpoints.ts CLISApp-frontend/.env.production CLISApp-frontend/.env
git commit -m "feat(config): add production API env support"
```

---

### Task 5: Verify configuration

**Files:**
- Verify: `CLISApp-frontend/android/app/build.gradle`
- Verify: `CLISApp-frontend/src/constants/apiEndpoints.ts`
- Verify: `CLISApp-frontend/.env.production`

**Step 1: Sanity check configs**

Run:
```bash
rg -n "envConfigFiles" CLISApp-frontend/android/app/build.gradle
rg -n "PRODUCTION_API_URL|PRODUCTION_TILE_URL" CLISApp-frontend/src/constants/apiEndpoints.ts
```
Expected: release uses `.env.production`; API resolver prefers production vars

**Step 2: Optional release build smoke check**

Run (optional): `cd CLISApp-frontend/android && ./gradlew assembleRelease`
Expected: build uses release signing (will fail if keystore missing)

**Step 3: Final commit summary**

Run: `git status -sb`
Expected: clean

---

## Notes
- The keystore file must not be committed; `.gitignore` already covers `*.keystore`.
- If multiple environments are needed later, consider adding `.env.staging` and a build flavor.
