# User Awards Page — Design

## Overview

A new page (initially on the bot's frontend, `../ce-assistant-frontend/`, with an eventual goal of moving to cedb.me) that evaluates a user's progress against a configurable list of milestone-style "awards" — e.g. "earn 3000 points in at least one category", "complete 100 objectives worth 10+ points", "complete every Tier 1 game". The page shows a single user their unlocked and locked awards, with progress bars for locked ones.

This is a single-user progress view for now. The data model is designed so that a leaderboard ("everyone who has unlocked award X") can be built later without schema changes.

## Goals

- Show a user which awards they've unlocked and how close they are to unlocking the rest
- Avoid recomputing everything on every page load — cache results, recompute only on explicit user action
- Keep computation logic out of the Discord bot; the bot should trend toward being a pure reporting/frontend tool
- Make award definitions easy to add to and easy to test in isolation

## Non-goals

- Leaderboards / cross-user views (future work, enabled by this schema but not built now)
- Live/automatic recomputation on every page load (explicitly rejected — recompute only on button press)
- Moving this logic to cedb.me (future work, once the user has access to that codebase)

## Data model (Supabase)

Two tables: one holding static award metadata, one holding per-user dynamic state.

### `awards` — static metadata

One row per defined award. Edited directly/rarely; not user-specific.

| column        | type      | notes                                              |
|---------------|-----------|----------------------------------------------------|
| `id`          | string    | slug, e.g. `"category_3000_one"`; primary key      |
| `name`        | string    | e.g. `"Category Specialist"`                       |
| `description` | string    | e.g. `"Earn 3000 points in at least one category"` |
| `icon`        | string    | path or emoji                                      |
| `target`      | int, null | optional fixed denominator, e.g. `3000`            |

### `userAwards` — per-user dynamic state

Sparse: a row exists for a `(user, award)` pair only once that award has been evaluated at least once for that user. No row means "never checked yet"; a row with `achieved = false` means "checked, still locked, here's the progress."

| column                 | type      | notes                                  |
|------------------------|-----------|----------------------------------------|
| `user_ce_id`           | string    | FK → `users.ce_id`                     |
| `award_id`             | string    | FK → `awards.id`                       |
| `achieved`             | bool      |                                         |
| `achieved_at`          | timestamp | null until unlocked                    |
| `progress_numerator`   | int       | cached progress value, e.g. `1800`     |
| `progress_denominator` | int       | cached target value, e.g. `3000`       |
| `last_checked_at`      | timestamp | when this row was last (re)computed    |

Primary key: `(user_ce_id, award_id)`.

Future leaderboard queries become a simple `SELECT user_ce_id FROM userAwards WHERE award_id = X AND achieved`.

## Architecture

All computation lives in the SvelteKit frontend (`../ce-assistant-frontend/`), split into three layers:

1. **Pure logic layer** (`src/lib/awards/`) — award definitions and the helpers/evaluator that compute progress from plain data. No I/O.
2. **Data access layer** — fetches/persists via Supabase.
3. **Routes/UI layer** — page, API endpoints, components.

### Pure logic layer

**`src/lib/awards/helpers.js`** — small, generic, reusable building blocks operating on plain `userGames`/`gameDb` data:
- `sumPointsWhere(userGames, gameDb, predicate)` — e.g. sum points where a game's categories include `"Female Protagonist"`
- `categoryTotals(userGames, gameDb)` — map of category → total points (backs checks like "3000 in at least one category" and "500 in every category")
- `countObjectivesWhere(userGames, predicate)` — e.g. count completed objectives worth ≥10 points
- `countCompletedGamesWhere(userGames, gameDb, predicate)` — e.g. completed Tier 1 games

**`src/lib/awards/registry.js`** — an array of award definitions. Each entry wires "what to check" to the helpers that compute it, and is keyed by the same `id` used in the `awards` Supabase table (so the registry supplies the *evaluation logic*, the table supplies the *display metadata* — no duplicated strings):

```js
{
  id: "category_3000_one",
  evaluate(userGames, gameDb) {
    const totals = categoryTotals(userGames, gameDb);
    const best = Math.max(...Object.values(totals));
    return { progress: best, target: 3000, achieved: best >= 3000 };
  }
}
```

**`src/lib/awards/evaluate.js`** — `evaluateAwards(userGames, gameDb, awardIds)`: loops the registry (optionally filtered to a subset of ids — e.g. only the user's currently-locked awards), calls each `evaluate()`, wraps each call in try/catch so a single failing check can't sink the batch, and returns plain `{ id, progress, target, achieved }` results.

Everything in this layer is pure — data in, data out — making it straightforward to unit test with small fixture objects, independent of Supabase or the network.

### Data access layer

Lives in `src/lib/awards/data.js` (or alongside `src/db/supabase.ts`):
- `getCachedAwards(userCeId)` — joins `userAwards` with `awards`, returns everything the page needs to render (name, description, icon, progress, achieved). Used on every page load.
- `getUserGameData(userCeId)` — fetches the user's owned games + objectives (same shape already assembled in the existing `withcompletion` endpoint). Used only during a refresh.
- `upsertAwardResults(userCeId, results)` — bulk upserts `{ user_ce_id, award_id, achieved, achieved_at, progress_numerator, progress_denominator, last_checked_at }` rows.

### Routes / UI layer

**Route:** `src/routes/users/[slug]/awards/`, following the existing `users/[slug]` convention:
- `+page.js` — loader that calls the page's `GET` API endpoint and passes cached award data to the page. Instant load; no computation.
- `+page.svelte` — renders the awards and the refresh button.

**API endpoints:** `src/routes/api/users/[slug]/awards/+server.js`
- `GET` — calls `getCachedAwards`, returns the joined rows. Mirrors the existing `medium/+server.js` pattern.
- `POST` (refresh action):
  1. Fetch the user's current `userAwards` rows to identify which awards are already `achieved` (skip re-evaluating those, per the goal of reducing unnecessary checking)
  2. Fetch fresh game/user data via `getUserGameData`
  3. Run `evaluateAwards` over only the not-yet-achieved award ids
  4. `upsertAwardResults` with the new results
  5. Return the full updated joined list so the page can re-render in one round trip

**Components**, following the existing naming style (`WishlistEntry.svelte`, `CERoll.svelte`):
- `AwardCard.svelte` — renders one award: icon, name, description, locked/unlocked state, achieved date if unlocked, and a progress bar driven by `progress_numerator`/`progress_denominator`. Progress bars are only shown/updated post-refresh — never computed live on page load.

A grouping/sorting wrapper component (e.g. `AwardsGrid.svelte`) is optional and can be added later if `+page.svelte` markup grows unwieldy; not required for the initial version.

## Data flow

1. **Page load**: `+page.js` loader → `GET /api/users/[slug]/awards` → `getCachedAwards` → joined `userAwards`+`awards` rows rendered immediately. No computation triggered.
2. **Refresh**: user clicks "Check for new awards" → `POST /api/users/[slug]/awards` → fetch not-yet-achieved award ids + fresh user/game data → `evaluateAwards` (locked awards only) → `upsertAwardResults` → updated joined list returned → page re-renders with new state, including any newly unlocked awards and updated progress bars.

## Error handling

- **API layer**: 404 for unknown user/slug; 500 with a logged error for Supabase failures. The upsert batch is all-or-nothing — no partial-state writes, so a failed refresh leaves the previously-cached state intact.
- **Evaluation layer**: each `evaluate()` call is individually wrapped in try/catch within `evaluateAwards`. A throwing/buggy check is skipped and logged for that cycle, and simply gets retried on the next refresh — it doesn't block evaluation of the other awards.
- **UI layer**: the refresh button shows a loading state while the POST is in flight, and surfaces a simple error message if it fails, without discarding the existing cached award list.

## Testing

- `helpers.js` functions and each registry entry's `evaluate()` are pure — unit test with small fixture `userGames`/`gameDb` objects (e.g. "user with 3000 points in one category, spread across two games, returns `achieved: true`").
- `evaluate.js`'s orchestration (try/catch wrapping, filtering to not-yet-achieved ids) can be tested with a mix of passing and intentionally-throwing fake registry entries.
- API routes: integration tests against a test Supabase instance if available; otherwise manual verification through the UI is acceptable for a first pass.

## Future work (explicitly out of scope now)

- Leaderboards / "number of users who have this award" views, enabled by the `userAwards` schema
- Migrating this logic to cedb.me once the user has access to that codebase
- Visual design / layout details for `AwardCard.svelte` and the page (user has notes to work through separately)
