import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

_conn: sqlite3.Connection | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    ce_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    platform TEXT NOT NULL DEFAULT '',
    platform_id TEXT,
    category_primary TEXT,
    image_header TEXT NOT NULL DEFAULT '',
    image_icon TEXT NOT NULL DEFAULT '',
    updated_at_CE TEXT
);

CREATE TABLE IF NOT EXISTS objectives (
    ce_id TEXT PRIMARY KEY,
    game_ce_id TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    points INTEGER NOT NULL DEFAULT 0,
    points_partial INTEGER,
    updated_at_CE TEXT
);

CREATE TABLE IF NOT EXISTS objective_requirements (
    objective_ce_id TEXT NOT NULL,
    requirement_type TEXT NOT NULL,
    data TEXT NOT NULL DEFAULT '',
    updated_at_CE TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    game_id TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    "index" INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
    ce_id TEXT PRIMARY KEY,
    discord_id INTEGER,
    display_name TEXT NOT NULL DEFAULT '',
    image_avatar TEXT,
    steam_id TEXT,
    created_at_CE TEXT,
    updated_at_CE TEXT
);

CREATE TABLE IF NOT EXISTS user_games (
    user_ce_id TEXT NOT NULL,
    game_ce_id TEXT NOT NULL,
    updated_at_CE TEXT,
    PRIMARY KEY (user_ce_id, game_ce_id)
);

CREATE TABLE IF NOT EXISTS user_objectives (
    user_ce_id TEXT NOT NULL,
    objective_ce_id TEXT NOT NULL,
    user_points INTEGER,
    updated_at_CE TEXT,
    PRIMARY KEY (user_ce_id, objective_ce_id)
);

CREATE TABLE IF NOT EXISTS rolls (
    id TEXT PRIMARY KEY,
    event_name TEXT NOT NULL DEFAULT '',
    user1_ce_id TEXT NOT NULL,
    user2_ce_id TEXT,
    time_created TEXT,
    time_due TEXT,
    time_completed TEXT,
    is_lucky INTEGER NOT NULL DEFAULT 0,
    chosen_tier INTEGER,
    chosen_tier_partner INTEGER,
    status TEXT NOT NULL DEFAULT '',
    rerolls_remaining INTEGER,
    rerolls_used INTEGER NOT NULL DEFAULT 0,
    winner TEXT
);

CREATE TABLE IF NOT EXISTS roll_games (
    roll_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    "index" INTEGER NOT NULL DEFAULT 0,
    rolled_at TEXT
);

CREATE TABLE IF NOT EXISTS tier (
    ce_id TEXT PRIMARY KEY,
    price REAL,
    sh_hours REAL
);

CREATE INDEX IF NOT EXISTS idx_objectives_game ON objectives(game_ce_id);
CREATE INDEX IF NOT EXISTS idx_obj_reqs_objective ON objective_requirements(objective_ce_id);
CREATE INDEX IF NOT EXISTS idx_categories_game ON categories(game_id);
CREATE INDEX IF NOT EXISTS idx_user_games_user ON user_games(user_ce_id);
CREATE INDEX IF NOT EXISTS idx_user_objectives_user ON user_objectives(user_ce_id);
CREATE INDEX IF NOT EXISTS idx_rolls_user1 ON rolls(user1_ce_id);
CREATE INDEX IF NOT EXISTS idx_rolls_user2 ON rolls(user2_ce_id);
CREATE INDEX IF NOT EXISTS idx_rolls_status ON rolls(status);
CREATE INDEX IF NOT EXISTS idx_roll_games_roll ON roll_games(roll_id);
"""


def init(db_path: str = "data/cache.db") -> None:
    global _conn
    if _conn is not None:
        return

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    _conn = sqlite3.connect(db_path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("PRAGMA busy_timeout=5000")
    _conn.executescript(_SCHEMA)
    _conn.commit()
    logger.info("LocalCache initialized at %s", db_path)


def close() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


def get_connection() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("LocalCache not initialized. Call init() first.")
    return _conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


# === GAMES ===

def upsert_game(row: dict) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO games (ce_id, name, platform, platform_id, category_primary,
           image_header, image_icon, updated_at_CE)
           VALUES (:ce_id, :name, :platform, :platform_id, :category_primary,
           :image_header, :image_icon, :updated_at_CE)
           ON CONFLICT(ce_id) DO UPDATE SET
           name=excluded.name, platform=excluded.platform,
           platform_id=excluded.platform_id, category_primary=excluded.category_primary,
           image_header=excluded.image_header, image_icon=excluded.image_icon,
           updated_at_CE=excluded.updated_at_CE""",
        row,
    )
    conn.commit()


def upsert_games_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO games (ce_id, name, platform, platform_id, category_primary,
           image_header, image_icon, updated_at_CE)
           VALUES (:ce_id, :name, :platform, :platform_id, :category_primary,
           :image_header, :image_icon, :updated_at_CE)
           ON CONFLICT(ce_id) DO UPDATE SET
           name=excluded.name, platform=excluded.platform,
           platform_id=excluded.platform_id, category_primary=excluded.category_primary,
           image_header=excluded.image_header, image_icon=excluded.image_icon,
           updated_at_CE=excluded.updated_at_CE""",
        rows,
    )
    conn.commit()


def get_game(ce_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM games WHERE ce_id = ?", (ce_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_games_all() -> list[dict]:
    conn = get_connection()
    return [_row_to_dict(r) for r in conn.execute("SELECT * FROM games").fetchall()]


def get_games_by_ids(ce_ids: list[str]) -> list[dict]:
    if not ce_ids:
        return []
    conn = get_connection()
    placeholders = ",".join("?" * len(ce_ids))
    return [
        _row_to_dict(r)
        for r in conn.execute(
            f"SELECT * FROM games WHERE ce_id IN ({placeholders})", ce_ids
        ).fetchall()
    ]


def get_game_ids() -> list[str]:
    conn = get_connection()
    return [r[0] for r in conn.execute("SELECT ce_id FROM games").fetchall()]


def delete_game(ce_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM games WHERE ce_id = ?", (ce_id,))
    conn.commit()


# === OBJECTIVES ===

def upsert_objectives_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO objectives (ce_id, game_ce_id, type, name, description,
           points, points_partial, updated_at_CE)
           VALUES (:ce_id, :game_ce_id, :type, :name, :description,
           :points, :points_partial, :updated_at_CE)
           ON CONFLICT(ce_id) DO UPDATE SET
           game_ce_id=excluded.game_ce_id, type=excluded.type, name=excluded.name,
           description=excluded.description, points=excluded.points,
           points_partial=excluded.points_partial, updated_at_CE=excluded.updated_at_CE""",
        rows,
    )
    conn.commit()


def get_objectives_by_game(game_ce_id: str) -> list[dict]:
    conn = get_connection()
    return [
        _row_to_dict(r)
        for r in conn.execute(
            "SELECT * FROM objectives WHERE game_ce_id = ?", (game_ce_id,)
        ).fetchall()
    ]


def get_objectives_by_ids(ce_ids: list[str]) -> list[dict]:
    if not ce_ids:
        return []
    conn = get_connection()
    placeholders = ",".join("?" * len(ce_ids))
    return [
        _row_to_dict(r)
        for r in conn.execute(
            f"SELECT * FROM objectives WHERE ce_id IN ({placeholders})", ce_ids
        ).fetchall()
    ]


def get_objective_ids() -> list[str]:
    conn = get_connection()
    return [r[0] for r in conn.execute("SELECT ce_id FROM objectives").fetchall()]


def delete_objectives_by_ids(ce_ids: list[str]) -> None:
    if not ce_ids:
        return
    conn = get_connection()
    placeholders = ",".join("?" * len(ce_ids))
    conn.execute(f"DELETE FROM objectives WHERE ce_id IN ({placeholders})", ce_ids)
    conn.commit()


# === OBJECTIVE REQUIREMENTS ===

def upsert_requirements_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO objective_requirements
           (objective_ce_id, requirement_type, data, updated_at_CE)
           VALUES (:objective_ce_id, :requirement_type, :data, :updated_at_CE)""",
        rows,
    )
    conn.commit()


def delete_requirements_by_objectives(objective_ce_ids: list[str]) -> None:
    if not objective_ce_ids:
        return
    conn = get_connection()
    placeholders = ",".join("?" * len(objective_ce_ids))
    conn.execute(
        f"DELETE FROM objective_requirements WHERE objective_ce_id IN ({placeholders})",
        objective_ce_ids,
    )
    conn.commit()


def get_requirements_by_objectives(objective_ce_ids: list[str]) -> list[dict]:
    if not objective_ce_ids:
        return []
    conn = get_connection()
    placeholders = ",".join("?" * len(objective_ce_ids))
    return [
        _row_to_dict(r)
        for r in conn.execute(
            f"SELECT * FROM objective_requirements WHERE objective_ce_id IN ({placeholders})",
            objective_ce_ids,
        ).fetchall()
    ]


# === CATEGORIES ===

def upsert_categories_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO categories (game_id, category, "index")
           VALUES (:game_id, :category, :index)""",
        rows,
    )
    conn.commit()


def delete_categories_by_game(game_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM categories WHERE game_id = ?", (game_id,))
    conn.commit()


def delete_categories_by_games(game_ids: list[str]) -> None:
    if not game_ids:
        return
    conn = get_connection()
    placeholders = ",".join("?" * len(game_ids))
    conn.execute(f"DELETE FROM categories WHERE game_id IN ({placeholders})", game_ids)
    conn.commit()


def get_categories_by_game(game_id: str) -> list[dict]:
    conn = get_connection()
    return [
        _row_to_dict(r)
        for r in conn.execute(
            'SELECT * FROM categories WHERE game_id = ? ORDER BY "index" ASC',
            (game_id,),
        ).fetchall()
    ]


# === USERS ===

def upsert_user(row: dict) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO users (ce_id, discord_id, display_name, image_avatar,
           steam_id, created_at_CE, updated_at_CE)
           VALUES (:ce_id, :discord_id, :display_name, :image_avatar,
           :steam_id, :created_at_CE, :updated_at_CE)
           ON CONFLICT(ce_id) DO UPDATE SET
           discord_id=excluded.discord_id, display_name=excluded.display_name,
           image_avatar=excluded.image_avatar, steam_id=excluded.steam_id,
           created_at_CE=excluded.created_at_CE, updated_at_CE=excluded.updated_at_CE""",
        row,
    )
    conn.commit()


def upsert_users_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO users (ce_id, discord_id, display_name, image_avatar,
           steam_id, created_at_CE, updated_at_CE)
           VALUES (:ce_id, :discord_id, :display_name, :image_avatar,
           :steam_id, :created_at_CE, :updated_at_CE)
           ON CONFLICT(ce_id) DO UPDATE SET
           discord_id=excluded.discord_id, display_name=excluded.display_name,
           image_avatar=excluded.image_avatar, steam_id=excluded.steam_id,
           created_at_CE=excluded.created_at_CE, updated_at_CE=excluded.updated_at_CE""",
        rows,
    )
    conn.commit()


def get_user(ce_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE ce_id = ?", (ce_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_user_by_discord_id(discord_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
    ).fetchone()
    return _row_to_dict(row) if row else None


def get_users_all() -> list[dict]:
    conn = get_connection()
    return [_row_to_dict(r) for r in conn.execute("SELECT * FROM users").fetchall()]


def get_users_by_ids(ce_ids: list[str]) -> list[dict]:
    if not ce_ids:
        return []
    conn = get_connection()
    placeholders = ",".join("?" * len(ce_ids))
    return [
        _row_to_dict(r)
        for r in conn.execute(
            f"SELECT * FROM users WHERE ce_id IN ({placeholders})", ce_ids
        ).fetchall()
    ]


def get_user_ids() -> list[str]:
    conn = get_connection()
    return [r[0] for r in conn.execute("SELECT ce_id FROM users").fetchall()]


def delete_user(ce_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE ce_id = ?", (ce_id,))
    conn.commit()


# === USER GAMES ===

def upsert_user_games_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO user_games (user_ce_id, game_ce_id, updated_at_CE)
           VALUES (:user_ce_id, :game_ce_id, :updated_at_CE)
           ON CONFLICT(user_ce_id, game_ce_id) DO UPDATE SET
           updated_at_CE=excluded.updated_at_CE""",
        rows,
    )
    conn.commit()


def get_user_games(user_ce_id: str) -> list[dict]:
    conn = get_connection()
    return [
        _row_to_dict(r)
        for r in conn.execute(
            "SELECT * FROM user_games WHERE user_ce_id = ?", (user_ce_id,)
        ).fetchall()
    ]


def delete_user_games(user_ce_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM user_games WHERE user_ce_id = ?", (user_ce_id,))
    conn.commit()


# === USER OBJECTIVES ===

def upsert_user_objectives_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO user_objectives (user_ce_id, objective_ce_id, user_points, updated_at_CE)
           VALUES (:user_ce_id, :objective_ce_id, :user_points, :updated_at_CE)
           ON CONFLICT(user_ce_id, objective_ce_id) DO UPDATE SET
           user_points=excluded.user_points, updated_at_CE=excluded.updated_at_CE""",
        rows,
    )
    conn.commit()


def get_user_objectives(user_ce_id: str) -> list[dict]:
    conn = get_connection()
    return [
        _row_to_dict(r)
        for r in conn.execute(
            "SELECT * FROM user_objectives WHERE user_ce_id = ?", (user_ce_id,)
        ).fetchall()
    ]


def delete_user_objectives(user_ce_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM user_objectives WHERE user_ce_id = ?", (user_ce_id,))
    conn.commit()


# === ROLLS ===

def upsert_roll(row: dict) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO rolls (id, event_name, user1_ce_id, user2_ce_id,
           time_created, time_due, time_completed, is_lucky, chosen_tier,
           chosen_tier_partner, status, rerolls_remaining, rerolls_used, winner)
           VALUES (:id, :event_name, :user1_ce_id, :user2_ce_id,
           :time_created, :time_due, :time_completed, :is_lucky, :chosen_tier,
           :chosen_tier_partner, :status, :rerolls_remaining, :rerolls_used, :winner)
           ON CONFLICT(id) DO UPDATE SET
           event_name=excluded.event_name, user1_ce_id=excluded.user1_ce_id,
           user2_ce_id=excluded.user2_ce_id, time_created=excluded.time_created,
           time_due=excluded.time_due, time_completed=excluded.time_completed,
           is_lucky=excluded.is_lucky, chosen_tier=excluded.chosen_tier,
           chosen_tier_partner=excluded.chosen_tier_partner, status=excluded.status,
           rerolls_remaining=excluded.rerolls_remaining, rerolls_used=excluded.rerolls_used,
           winner=excluded.winner""",
        row,
    )
    conn.commit()


def upsert_rolls_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO rolls (id, event_name, user1_ce_id, user2_ce_id,
           time_created, time_due, time_completed, is_lucky, chosen_tier,
           chosen_tier_partner, status, rerolls_remaining, rerolls_used, winner)
           VALUES (:id, :event_name, :user1_ce_id, :user2_ce_id,
           :time_created, :time_due, :time_completed, :is_lucky, :chosen_tier,
           :chosen_tier_partner, :status, :rerolls_remaining, :rerolls_used, :winner)
           ON CONFLICT(id) DO UPDATE SET
           event_name=excluded.event_name, user1_ce_id=excluded.user1_ce_id,
           user2_ce_id=excluded.user2_ce_id, time_created=excluded.time_created,
           time_due=excluded.time_due, time_completed=excluded.time_completed,
           is_lucky=excluded.is_lucky, chosen_tier=excluded.chosen_tier,
           chosen_tier_partner=excluded.chosen_tier_partner, status=excluded.status,
           rerolls_remaining=excluded.rerolls_remaining, rerolls_used=excluded.rerolls_used,
           winner=excluded.winner""",
        rows,
    )
    conn.commit()


def get_roll(roll_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM rolls WHERE id = ?", (roll_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_rolls_all() -> list[dict]:
    conn = get_connection()
    return [_row_to_dict(r) for r in conn.execute("SELECT * FROM rolls").fetchall()]


def get_rolls_by_user(user_ce_id: str) -> list[dict]:
    conn = get_connection()
    return [
        _row_to_dict(r)
        for r in conn.execute(
            "SELECT * FROM rolls WHERE user1_ce_id = ? OR user2_ce_id = ?",
            (user_ce_id, user_ce_id),
        ).fetchall()
    ]


def get_checkable_rolls() -> list[dict]:
    conn = get_connection()
    return [
        _row_to_dict(r)
        for r in conn.execute(
            "SELECT * FROM rolls WHERE status IN ('current', 'pending')"
        ).fetchall()
    ]


def get_roll_ids() -> list[str]:
    conn = get_connection()
    return [r[0] for r in conn.execute("SELECT id FROM rolls").fetchall()]


def delete_roll(roll_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM roll_games WHERE roll_id = ?", (roll_id,))
    conn.execute("DELETE FROM rolls WHERE id = ?", (roll_id,))
    conn.commit()


def delete_rolls_by_ids(roll_ids: list[str]) -> None:
    if not roll_ids:
        return
    conn = get_connection()
    placeholders = ",".join("?" * len(roll_ids))
    conn.execute(f"DELETE FROM roll_games WHERE roll_id IN ({placeholders})", roll_ids)
    conn.execute(f"DELETE FROM rolls WHERE id IN ({placeholders})", roll_ids)
    conn.commit()


# === ROLL GAMES ===

def upsert_roll_games_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO roll_games (roll_id, game_id, "index", rolled_at)
           VALUES (:roll_id, :game_id, :index, :rolled_at)""",
        rows,
    )
    conn.commit()


def get_roll_games(roll_id: str) -> list[dict]:
    conn = get_connection()
    return [
        _row_to_dict(r)
        for r in conn.execute(
            'SELECT * FROM roll_games WHERE roll_id = ? ORDER BY "index" ASC',
            (roll_id,),
        ).fetchall()
    ]


def get_roll_games_by_ids(roll_ids: list[str]) -> list[dict]:
    if not roll_ids:
        return []
    conn = get_connection()
    placeholders = ",".join("?" * len(roll_ids))
    return [
        _row_to_dict(r)
        for r in conn.execute(
            f"SELECT * FROM roll_games WHERE roll_id IN ({placeholders})", roll_ids
        ).fetchall()
    ]


def delete_roll_games_by_roll(roll_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM roll_games WHERE roll_id = ?", (roll_id,))
    conn.commit()


def delete_roll_games_by_rolls(roll_ids: list[str]) -> None:
    if not roll_ids:
        return
    conn = get_connection()
    placeholders = ",".join("?" * len(roll_ids))
    conn.execute(f"DELETE FROM roll_games WHERE roll_id IN ({placeholders})", roll_ids)
    conn.commit()


# === TIER ===

def upsert_tier_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO tier (ce_id, price, sh_hours)
           VALUES (:ce_id, :price, :sh_hours)
           ON CONFLICT(ce_id) DO UPDATE SET
           price=excluded.price, sh_hours=excluded.sh_hours""",
        rows,
    )
    conn.commit()


def get_tier_all() -> list[dict]:
    conn = get_connection()
    return [_row_to_dict(r) for r in conn.execute("SELECT * FROM tier").fetchall()]


# === REBUILD ===

def rebuild_from_supabase() -> dict:
    from Modules.SupabaseReader import supabase as sb

    logger.info("Rebuilding local cache from Supabase...")
    counts = {}

    table_map = [
        ("games", "games"),
        ("objectives", "objectives"),
        ("objectiveRequirements", "objective_requirements"),
        ("categories", "categories"),
        ("users", "users"),
        ("userGames", "user_games"),
        ("userObjectives", "user_objectives"),
        ("rolls", "rolls"),
        ("rollGames", "roll_games"),
        ("tier", "tier"),
    ]

    conn = get_connection()

    for sb_table, local_table in table_map:
        data = sb.table(sb_table).select().execute().data or []
        counts[local_table] = len(data)
        if not data:
            continue

        cols = list(data[0].keys())
        col_names = ",".join(f'"{c}"' for c in cols)
        params = ",".join(f":{c}" for c in cols)

        conn.execute(f'DELETE FROM "{local_table}"')
        conn.executemany(
            f'INSERT INTO "{local_table}" ({col_names}) VALUES ({params})',
            data,
        )

    conn.commit()
    logger.info("Rebuild complete: %s", counts)
    return counts


# === INTEGRITY CHECK ===

def run_integrity_check() -> dict:
    from Modules.SupabaseReader import supabase as sb

    report: dict[str, list[str]] = {"synced": [], "removed": []}

    checks = [
        ("games", "games", "ce_id"),
        ("users", "users", "ce_id"),
        ("objectives", "objectives", "ce_id"),
        ("rolls", "rolls", "id"),
    ]

    conn = get_connection()

    for sb_table, local_table, id_col in checks:
        sb_ids = {
            row[id_col]
            for row in sb.table(sb_table).select(id_col).execute().data or []
        }
        local_ids = {
            row[0]
            for row in conn.execute(
                f'SELECT "{id_col}" FROM "{local_table}"'
            ).fetchall()
        }

        missing_locally = sb_ids - local_ids
        stale_locally = local_ids - sb_ids

        if missing_locally:
            missing_list = list(missing_locally)
            for i in range(0, len(missing_list), 100):
                chunk = missing_list[i : i + 100]
                data = sb.table(sb_table).select().in_(id_col, chunk).execute().data or []
                if data:
                    cols = list(data[0].keys())
                    col_names = ",".join(f'"{c}"' for c in cols)
                    params = ",".join(f":{c}" for c in cols)
                    conn.executemany(
                        f'INSERT OR REPLACE INTO "{local_table}" ({col_names}) VALUES ({params})',
                        data,
                    )
            report["synced"].append(f"{len(missing_locally)} {local_table}")

        if stale_locally:
            stale_list = list(stale_locally)
            placeholders = ",".join("?" * len(stale_list))
            conn.execute(
                f'DELETE FROM "{local_table}" WHERE "{id_col}" IN ({placeholders})',
                stale_list,
            )
            report["removed"].append(f"{len(stale_locally)} {local_table}")

    conn.commit()
    return report
