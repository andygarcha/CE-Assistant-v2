import json
import logging
import os
import sqlite3
import typing

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
    updated_at_CE TEXT,
    ping_casino_fail INTEGER NOT NULL DEFAULT 0,
    ping_casino_win INTEGER NOT NULL DEFAULT 0,
    ping_user_log INTEGER NOT NULL DEFAULT 0
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
    partial INTEGER,
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
    rerolls_used INTEGER DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS banned_games (
    game_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL DEFAULT '',
    banned_by TEXT
);

CREATE TABLE IF NOT EXISTS bounty_color (
    user_id TEXT NOT NULL,
    color_name TEXT NOT NULL,
    PRIMARY KEY (user_id, color_name)
);

CREATE INDEX IF NOT EXISTS idx_objectives_game ON objectives(game_ce_id);
CREATE INDEX IF NOT EXISTS idx_bounty_color_user ON bounty_color(user_id);
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
    _conn = sqlite3.connect(db_path)
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


def is_initialized() -> bool:
    return _conn is not None


def get_connection() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("LocalCache not initialized. Call init() first.")
    return _conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _json_ids(ids: list) -> str:
    """
    Serializes a list of IDs as a JSON array string, for binding into a
    query that matches against it with `IN (SELECT value FROM json_each(?))`.

    This keeps the query text fully static (no dynamically-sized placeholder
    string spliced in) regardless of how many IDs are being matched, since
    sqlite3 has no native way to bind a variable-length list into an IN(...)
    clause otherwise.
    """
    return json.dumps(ids)


_ROLL_DEFAULTS = {
    "id": None,
    "event_name": "",
    "user1_ce_id": "",
    "user2_ce_id": None,
    "time_created": None,
    "time_due": None,
    "time_completed": None,
    "is_lucky": 0,
    "chosen_tier": None,
    "chosen_tier_partner": None,
    "status": "",
    "rerolls_remaining": None,
    "rerolls_used": 0,
    "winner": None,
}


def _normalize_roll(row: dict) -> dict:
    return {**_ROLL_DEFAULTS, **row}


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
    return [
        _row_to_dict(r)
        for r in conn.execute(
            "SELECT * FROM games WHERE ce_id IN (SELECT value FROM json_each(?))",
            (_json_ids(ce_ids),),
        ).fetchall()
    ]


def get_game_ids() -> list[str]:
    conn = get_connection()
    return [r[0] for r in conn.execute("SELECT ce_id FROM games").fetchall()]


def get_game_id_by_name(name: str) -> list[dict]:
    """
    Takes in a name and returns a list of `CEGame`s whose name contains the parameter.

    Parameters
    ---
    name: `str`
        The name of the game we're trying to match.

    Returns
    ---
    games: `list[CEGame]`
        A list of games that match the name. Empty if none match.
    """

    conn = get_connection()
    escaped_name = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return conn.execute(
        "SELECT * FROM games WHERE name LIKE ? ESCAPE '\\' LIMIT 25;",
        (f"%{escaped_name}%",),
    ).fetchall()


def delete_game(ce_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM games WHERE ce_id = ?", (ce_id,))
    conn.commit()


def delete_game_cascade(ce_id: str) -> None:
    conn = get_connection()
    obj_ids = [
        r[0]
        for r in conn.execute(
            "SELECT ce_id FROM objectives WHERE game_ce_id = ?", (ce_id,)
        ).fetchall()
    ]
    if obj_ids:
        conn.execute(
            "DELETE FROM objective_requirements "
            "WHERE objective_ce_id IN (SELECT value FROM json_each(?))",
            (_json_ids(obj_ids),),
        )
    conn.execute("DELETE FROM objectives WHERE game_ce_id = ?", (ce_id,))
    conn.execute("DELETE FROM categories WHERE game_id = ?", (ce_id,))
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
    return [
        _row_to_dict(r)
        for r in conn.execute(
            "SELECT * FROM objectives WHERE ce_id IN (SELECT value FROM json_each(?))",
            (_json_ids(ce_ids),),
        ).fetchall()
    ]


def get_objective_ids() -> list[str]:
    conn = get_connection()
    return [r[0] for r in conn.execute("SELECT ce_id FROM objectives").fetchall()]


def delete_objectives_by_ids(ce_ids: list[str]) -> None:
    if not ce_ids:
        return
    conn = get_connection()
    conn.execute(
        "DELETE FROM objectives WHERE ce_id IN (SELECT value FROM json_each(?))",
        (_json_ids(ce_ids),),
    )
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
    conn.execute(
        "DELETE FROM objective_requirements "
        "WHERE objective_ce_id IN (SELECT value FROM json_each(?))",
        (_json_ids(objective_ce_ids),),
    )
    conn.commit()


def get_requirements_by_objectives(objective_ce_ids: list[str]) -> list[dict]:
    if not objective_ce_ids:
        return []
    conn = get_connection()
    return [
        _row_to_dict(r)
        for r in conn.execute(
            "SELECT * FROM objective_requirements "
            "WHERE objective_ce_id IN (SELECT value FROM json_each(?))",
            (_json_ids(objective_ce_ids),),
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
    conn.execute(
        "DELETE FROM categories WHERE game_id IN (SELECT value FROM json_each(?))",
        (_json_ids(game_ids),),
    )
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


_PING_COLUMNS = {"ping_casino_fail", "ping_casino_win", "ping_user_log"}

_UPSERT_USER_SQL = """INSERT INTO users (ce_id, discord_id, display_name, image_avatar,
   steam_id, created_at_CE, updated_at_CE, ping_casino_fail, ping_casino_win, ping_user_log)
   VALUES (:ce_id, :discord_id, :display_name, :image_avatar,
   :steam_id, :created_at_CE, :updated_at_CE, COALESCE(:ping_casino_fail, 0),
   COALESCE(:ping_casino_win, 0), COALESCE(:ping_user_log, 0))
   ON CONFLICT(ce_id) DO UPDATE SET
   discord_id=excluded.discord_id, display_name=excluded.display_name,
   image_avatar=excluded.image_avatar, steam_id=excluded.steam_id,
   created_at_CE=excluded.created_at_CE, updated_at_CE=excluded.updated_at_CE,
   ping_casino_fail=COALESCE(:ping_casino_fail, ping_casino_fail),
   ping_casino_win=COALESCE(:ping_casino_win, ping_casino_win),
   ping_user_log=COALESCE(:ping_user_log, ping_user_log)"""


def upsert_user(row: dict) -> None:
    conn = get_connection()
    # dump_user/bulk_dump_users intentionally omit the ping_* keys so they
    # never clobber a preference set elsewhere -- _fill_missing_columns backs
    # them with None so sqlite3's named-param binding doesn't ProgrammingError,
    # and the SQL above's COALESCE(:param, existing_column) preserves whatever
    # was already stored (or defaults to 0 on first insert).
    conn.execute(_UPSERT_USER_SQL, _fill_missing_columns([row], _PING_COLUMNS)[0])
    conn.commit()


def upsert_users_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(_UPSERT_USER_SQL, _fill_missing_columns(rows, _PING_COLUMNS))
    conn.commit()


def set_user_ping_prefs(
    ce_id: str, ping_casino_fail: bool, ping_casino_win: bool, ping_user_log: bool
) -> None:
    """
    Sets a user's ping preferences directly, unlike upsert_user/upsert_users_bulk
    which always preserve them unless explicitly given -- this is the one write
    path meant to actually change them (e.g. from the preferences modal).
    """
    conn = get_connection()
    conn.execute(
        "UPDATE users SET ping_casino_fail = ?, ping_casino_win = ?, ping_user_log = ? "
        "WHERE ce_id = ?",
        (ping_casino_fail, ping_casino_win, ping_user_log, ce_id),
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
    return [
        _row_to_dict(r)
        for r in conn.execute(
            "SELECT * FROM users WHERE ce_id IN (SELECT value FROM json_each(?))",
            (_json_ids(ce_ids),),
        ).fetchall()
    ]


def get_user_ids() -> list[str]:
    conn = get_connection()
    return [r[0] for r in conn.execute("SELECT ce_id FROM users").fetchall()]


def delete_user(ce_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE ce_id = ?", (ce_id,))
    conn.commit()


def delete_user_cascade(ce_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM user_games WHERE user_ce_id = ?", (ce_id,))
    conn.execute("DELETE FROM user_objectives WHERE user_ce_id = ?", (ce_id,))
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


def delete_user_games_by_game_ids(game_ids: list[str]) -> None:
    if not game_ids:
        return
    conn = get_connection()
    conn.execute(
        "DELETE FROM user_games WHERE game_ce_id IN (SELECT value FROM json_each(?))",
        (_json_ids(game_ids),),
    )
    conn.commit()


# === USER OBJECTIVES ===


def upsert_user_objectives_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO user_objectives (user_ce_id, objective_ce_id, partial, updated_at_CE)
           VALUES (:user_ce_id, :objective_ce_id, :partial, :updated_at_CE)
           ON CONFLICT(user_ce_id, objective_ce_id) DO UPDATE SET
           partial=excluded.partial, updated_at_CE=excluded.updated_at_CE""",
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


def delete_user_objectives_by_objective_ids(objective_ids: list[str]) -> None:
    if not objective_ids:
        return
    conn = get_connection()
    conn.execute(
        "DELETE FROM user_objectives "
        "WHERE objective_ce_id IN (SELECT value FROM json_each(?))",
        (_json_ids(objective_ids),),
    )
    conn.commit()


# === ROLLS ===


def upsert_roll(row: dict) -> None:
    row = _normalize_roll(row)
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
    rows = [_normalize_roll(r) for r in rows]
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


def get_rolls_by_event_names(event_names: list[str]) -> list[dict]:
    if not event_names:
        return []
    conn = get_connection()
    return [
        _row_to_dict(r)
        for r in conn.execute(
            "SELECT * FROM rolls WHERE event_name IN (SELECT value FROM json_each(?))",
            (_json_ids(event_names),),
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
    ids_json = _json_ids(roll_ids)
    conn.execute(
        "DELETE FROM roll_games WHERE roll_id IN (SELECT value FROM json_each(?))",
        (ids_json,),
    )
    conn.execute(
        "DELETE FROM rolls WHERE id IN (SELECT value FROM json_each(?))",
        (ids_json,),
    )
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
    return [
        _row_to_dict(r)
        for r in conn.execute(
            "SELECT * FROM roll_games WHERE roll_id IN (SELECT value FROM json_each(?)) "
            'ORDER BY "index" ASC',
            (_json_ids(roll_ids),),
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
    conn.execute(
        "DELETE FROM roll_games WHERE roll_id IN (SELECT value FROM json_each(?))",
        (_json_ids(roll_ids),),
    )
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


# === BANNED GAMES ===


def upsert_banned_games_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO banned_games (game_id, reason, banned_by)
           VALUES (:game_id, :reason, :banned_by)
           ON CONFLICT(game_id) DO UPDATE SET
           reason=excluded.reason, banned_by=excluded.banned_by""",
        rows,
    )
    conn.commit()


def get_banned_game(game_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM banned_games WHERE game_id = ?", (game_id,)
    ).fetchone()
    return _row_to_dict(row) if row else None


def get_banned_games_all() -> list[dict]:
    conn = get_connection()
    return [
        _row_to_dict(r) for r in conn.execute("SELECT * FROM banned_games").fetchall()
    ]


def delete_banned_game(game_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM banned_games WHERE game_id = ?", (game_id,))
    conn.commit()


# === BOUNTY COLOR ===


def upsert_bounty_colors_bulk(rows: list[dict]) -> None:
    if not rows:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT INTO bounty_color (user_id, color_name)
           VALUES (:user_id, :color_name)
           ON CONFLICT(user_id, color_name) DO NOTHING""",
        rows,
    )
    conn.commit()


def get_bounty_colors(user_id: str) -> list[str]:
    conn = get_connection()
    return [
        r[0]
        for r in conn.execute(
            "SELECT color_name FROM bounty_color WHERE user_id = ?", (user_id,)
        ).fetchall()
    ]


def delete_bounty_color(user_id: str, color_name: str) -> None:
    conn = get_connection()
    conn.execute(
        "DELETE FROM bounty_color WHERE user_id = ? AND color_name = ?",
        (user_id, color_name),
    )
    conn.commit()


# === REBUILD ===

_SUPABASE_PAGE_SIZE = 1000

# Dispatch table mapping each local table name to its fully-static, parameterized
# bulk-upsert function. Using these instead of dynamically building INSERT
# statements from whatever columns a Supabase response happens to contain keeps
# every rebuild/sync query text 100% static -- no dynamic column-list f-strings.
_UPSERT_BULK_FUNCS: dict[str, typing.Callable[[list[dict]], None]] = {
    "games": upsert_games_bulk,
    "objectives": upsert_objectives_bulk,
    "objective_requirements": upsert_requirements_bulk,
    "categories": upsert_categories_bulk,
    "users": upsert_users_bulk,
    "user_games": upsert_user_games_bulk,
    "user_objectives": upsert_user_objectives_bulk,
    "rolls": upsert_rolls_bulk,
    "roll_games": upsert_roll_games_bulk,
    "tier": upsert_tier_bulk,
    "banned_games": upsert_banned_games_bulk,
    "bounty_color": upsert_bounty_colors_bulk,
}

# Child tables to sync when new parent rows are inserted by the integrity check.
# Format: parent_local_table -> [(supabase_child_table, fk_col, local_child_table), ...]
_CHILD_SYNCS: dict[str, list[tuple[str, str, str]]] = {
    "games": [("categories", "game_id", "categories")],
    "objectives": [
        ("objectiveRequirements", "objective_ce_id", "objective_requirements")
    ],
    "rolls": [("rollGames", "roll_id", "roll_games")],
    "users": [
        ("userGames", "user_ce_id", "user_games"),
        ("userObjectives", "user_ce_id", "user_objectives"),
        ("bounty_color", "user_id", "bounty_color"),
    ],
}


def _fetch_all_rows(sb_client, table_name: str) -> list[dict]:
    """Fetch all rows from a Supabase table with pagination to avoid the 1000-row default limit."""
    all_rows: list[dict] = []
    offset = 0
    while True:
        data = (
            sb_client.table(table_name)
            .select()
            .range(offset, offset + _SUPABASE_PAGE_SIZE - 1)
            .execute()
            .data
        ) or []
        all_rows.extend(data)
        if len(data) < _SUPABASE_PAGE_SIZE:
            break
        offset += _SUPABASE_PAGE_SIZE
    return all_rows


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    """
    Returns the set of column names defined on `table_name` in the local
    schema. `table_name` must always be a hardcoded literal from this
    module's own table-name constants (`table_map`, `checks`, `_CHILD_SYNCS`)
    -- never a value derived from Supabase or any other external input.
    """
    return {
        row[1] for row in conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    }


def _fill_missing_columns(rows: list[dict], columns: set[str]) -> list[dict]:
    """
    Ensures every row has a key for each column name in `columns`, defaulting
    any missing ones to None. The upsert_*_bulk functions bind named
    parameters for every column they declare, so a row missing an expected
    key would otherwise raise `sqlite3.ProgrammingError` -- this keeps that
    contract safe even if a Supabase response is ever missing a column that
    a `SELECT *` would normally include (e.g. a schema still catching up).
    """
    return [{**dict.fromkeys(columns), **row} for row in rows]


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
        ("bannedGames", "banned_games"),
        ("bounty_color", "bounty_color"),
    ]

    conn = get_connection()

    for sb_table, local_table in table_map:
        data = _fetch_all_rows(sb, sb_table)
        counts[local_table] = len(data)
        if not data:
            continue

        # Warn about any Supabase columns this table doesn't track locally.
        # This is diagnostic only -- upsert_*_bulk below only ever binds the
        # columns it explicitly declares, via named parameters, so extra
        # keys in `data` are simply ignored, not dropped as a side effect
        # of dynamically-built SQL.
        local_cols = _table_columns(conn, local_table)
        dropped = set(data[0].keys()) - local_cols
        if dropped:
            logger.warning(
                "Supabase table '%s' has columns not in local schema: %s. "
                "If your code uses these, add them to _SCHEMA in LocalCache.py.",
                sb_table,
                ", ".join(sorted(dropped)),
            )

        conn.execute(
            f'DELETE FROM "{local_table}"'  # noqa: S608 -- local_table is always a hardcoded entry from table_map above, never external input
        )
        _UPSERT_BULK_FUNCS[local_table](_fill_missing_columns(data, local_cols))

    conn.commit()
    logger.info("Rebuild complete: %s", counts)
    return counts


# === INTEGRITY CHECK ===


def run_integrity_check() -> dict:
    from Modules.SupabaseReader import supabase as sb

    report: dict[str, list[str]] = {"synced": [], "removed": [], "schema": []}

    checks = [
        ("games", "games", "ce_id"),
        ("users", "users", "ce_id"),
        ("objectives", "objectives", "ce_id"),
        ("rolls", "rolls", "id"),
        ("bannedGames", "banned_games", "game_id"),
    ]

    conn = get_connection()

    for sb_table, local_table, id_col in checks:
        all_id_rows: list[dict] = []
        offset = 0
        while True:
            page = (
                sb.table(sb_table)
                .select(id_col)
                .range(offset, offset + _SUPABASE_PAGE_SIZE - 1)
                .execute()
                .data
            ) or []
            all_id_rows.extend(page)
            if len(page) < _SUPABASE_PAGE_SIZE:
                break
            offset += _SUPABASE_PAGE_SIZE
        sb_ids = {row[id_col] for row in all_id_rows}
        local_ids = {
            row[0]
            for row in conn.execute(
                f'SELECT "{id_col}" FROM "{local_table}"'  # noqa: S608 -- id_col/local_table are hardcoded entries from `checks` above, never external input
            ).fetchall()
        }

        missing_locally = sb_ids - local_ids
        stale_locally = local_ids - sb_ids

        if missing_locally:
            missing_list = list(missing_locally)
            for i in range(0, len(missing_list), 100):
                chunk = missing_list[i : i + 100]
                data = (
                    sb.table(sb_table).select().in_(id_col, chunk).execute().data or []
                )
                if data:
                    local_cols = _table_columns(conn, local_table)
                    dropped = set(data[0].keys()) - local_cols
                    if dropped:
                        logger.warning(
                            "Supabase table '%s' has columns not in local schema: %s. "
                            "If your code uses these, add them to _SCHEMA in LocalCache.py.",
                            sb_table,
                            ", ".join(sorted(dropped)),
                        )
                    _UPSERT_BULK_FUNCS[local_table](
                        _fill_missing_columns(data, local_cols)
                    )
            # Sync child tables whose rows were not included in the parent select above.
            for sb_child, fk_col, child_local in _CHILD_SYNCS.get(local_table, []):
                child_rows: list[dict] = []
                for j in range(0, len(missing_list), 100):
                    parent_chunk = missing_list[j : j + 100]
                    offset = 0
                    while True:
                        page = (
                            sb.table(sb_child)
                            .select()
                            .in_(fk_col, parent_chunk)
                            .range(offset, offset + _SUPABASE_PAGE_SIZE - 1)
                            .execute()
                            .data
                        ) or []
                        child_rows.extend(page)
                        if len(page) < _SUPABASE_PAGE_SIZE:
                            break
                        offset += _SUPABASE_PAGE_SIZE

                if not child_rows:
                    continue

                child_local_cols = _table_columns(conn, child_local)
                dropped = set(child_rows[0].keys()) - child_local_cols
                if dropped:
                    logger.warning(
                        "Supabase table '%s' has columns not in local schema: %s.",
                        sb_child,
                        ", ".join(sorted(dropped)),
                    )
                # Clear any orphaned rows before inserting
                for j in range(0, len(missing_list), 100):
                    parent_chunk = missing_list[j : j + 100]
                    conn.execute(
                        f'DELETE FROM "{child_local}" '  # noqa: S608 -- child_local/fk_col come from the hardcoded _CHILD_SYNCS constant above, never external input
                        f'WHERE "{fk_col}" IN (SELECT value FROM json_each(?))',
                        (_json_ids(parent_chunk),),
                    )
                _UPSERT_BULK_FUNCS[child_local](
                    _fill_missing_columns(child_rows, child_local_cols)
                )
                report["synced"].append(f"{len(child_rows)} {child_local}")

            report["synced"].append(f"{len(missing_locally)} {local_table}")

        if stale_locally:
            stale_list = list(stale_locally)
            stale_json = _json_ids(stale_list)
            conn.execute(
                f'DELETE FROM "{local_table}" '  # noqa: S608 -- local_table/id_col come from the hardcoded `checks` constant above, never external input
                f'WHERE "{id_col}" IN (SELECT value FROM json_each(?))',
                (stale_json,),
            )

            # Cascade to child tables
            if local_table == "games":
                obj_ids = [
                    r[0]
                    for r in conn.execute(
                        "SELECT ce_id FROM objectives "
                        "WHERE game_ce_id IN (SELECT value FROM json_each(?))",
                        (stale_json,),
                    ).fetchall()
                ]
                conn.execute(
                    "DELETE FROM objectives "
                    "WHERE game_ce_id IN (SELECT value FROM json_each(?))",
                    (stale_json,),
                )
                if obj_ids:
                    conn.execute(
                        "DELETE FROM objective_requirements "
                        "WHERE objective_ce_id IN (SELECT value FROM json_each(?))",
                        (_json_ids(obj_ids),),
                    )
                conn.execute(
                    "DELETE FROM categories "
                    "WHERE game_id IN (SELECT value FROM json_each(?))",
                    (stale_json,),
                )
            elif local_table == "users":
                conn.execute(
                    "DELETE FROM user_games "
                    "WHERE user_ce_id IN (SELECT value FROM json_each(?))",
                    (stale_json,),
                )
                conn.execute(
                    "DELETE FROM user_objectives "
                    "WHERE user_ce_id IN (SELECT value FROM json_each(?))",
                    (stale_json,),
                )
                conn.execute(
                    "DELETE FROM bounty_color "
                    "WHERE user_id IN (SELECT value FROM json_each(?))",
                    (stale_json,),
                )
            elif local_table == "rolls":
                conn.execute(
                    "DELETE FROM roll_games "
                    "WHERE roll_id IN (SELECT value FROM json_each(?))",
                    (stale_json,),
                )
            elif local_table == "objectives":
                conn.execute(
                    "DELETE FROM objective_requirements "
                    "WHERE objective_ce_id IN (SELECT value FROM json_each(?))",
                    (stale_json,),
                )

            report["removed"].append(f"{len(stale_locally)} {local_table}")

    # Rebuild categories if empty while games are present (categories may have been
    # added to Supabase after the initial cache build, and they have no primary key
    # so they can't be tracked by the id-based checks above).
    game_count = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    cat_count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if game_count > 0 and cat_count == 0:
        data = _fetch_all_rows(sb, "categories")
        if data:
            conn.execute("DELETE FROM categories")
            upsert_categories_bulk(
                _fill_missing_columns(data, _table_columns(conn, "categories"))
            )
            report["synced"].append(f"{len(data)} categories (rebuilt)")

    # Schema validation
    report["schema"] = _validate_schema(conn)

    conn.commit()
    return report


def _validate_schema(conn: sqlite3.Connection) -> list[str]:
    """Compare expected schema columns against actual table columns.
    Auto-add missing columns via ALTER TABLE."""
    import re

    fixes: list[str] = []

    for statement in _SCHEMA.split(";"):
        statement = statement.strip()
        if not statement.startswith("CREATE TABLE"):
            continue

        match = re.search(r"CREATE TABLE IF NOT EXISTS (\w+)", statement)
        if not match:
            continue
        table_name = match.group(1)

        existing_cols = {
            row[1]
            for row in conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        }

        col_defs = re.findall(r'^\s+"?(\w+)"?\s+\w+', statement, re.MULTILINE)
        if not col_defs:
            col_defs = re.findall(r"^\s+(\w+)\s+\w+", statement, re.MULTILINE)

        for col in col_defs:
            if col.upper() in ("PRIMARY", "CREATE", "TABLE", "IF", "NOT", "EXISTS"):
                continue
            if col not in existing_cols:
                col_line = re.search(
                    rf'^\s+"?{col}"?\s+(.+?)(?:,\s*$|\s*$|\s*\))',
                    statement,
                    re.MULTILINE,
                )
                if col_line:
                    col_type = col_line.group(1).rstrip(",").strip()
                    try:
                        conn.execute(
                            f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" {col_type}'
                        )
                        fixes.append(f"added {col} to {table_name}")
                        logger.info(
                            "Schema fix: added column %s to %s", col, table_name
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to add column %s to %s: %s", col, table_name, e
                        )

    return fixes
