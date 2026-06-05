import json
from typing import Literal

import pandas as pd
import datetime
from dataclasses import dataclass
import math
from Modules import SupabaseReader


@dataclass
class RollRepresentation:
    event_name: str
    user_name: str
    game_names: list[str]
    status: str
    game_ids: list[str] | None = None
    user_id: str | None = None
    partner_name: str | None = None
    partner_id: str | None = None
    initialized_at: datetime.datetime | None = None
    due_at: datetime.datetime | None = None
    completed_at: datetime.datetime | None = None
    rerolls_used: int | None = None
    tier_num: int | None = None
    tier_num_partner: int | None = None
    winner: int | None = None
    id: str | None = None
    # Event Name	User Name	User ID	Partner Name	Partner ID
    # Initialized At	Due At	Completed At	Status	Rerolls Used
    # Tier Num	Tier Num Partner	Winner (1 or 2)	Game Names...

    def to_supabase_dict(self) -> dict:
        return {
            "id": self.id,
            "event_name": self.event_name,
            "user1_ce_id": self.user_id,
            "time_created": None,
            "time_due": None,
            "time_completed": None,
            "is_lucky": False,
            "chosen_tier": None,
            "chosen_tier_partner": None,
            "status": self.status,
            "rerolls_used": int(self.rerolls_used)
            if self.rerolls_used in [0.0, 1.0, 2.0, 3.0]
            else None,
            "from_sheet": True,
        }

    def to_supabase_dict_games(self) -> list[dict]:
        if self.game_ids is None:
            return []

        d = []
        i = 0
        for name, id in zip(self.game_names, self.game_ids):
            d.append(
                {
                    "roll_id": self.id,
                    "game_id": id,
                    "rolled_at": datetime.datetime.min.isoformat(),
                    "index": i,
                    "game_name": name,
                }
            )
            i += 1
        return d

    def __to_csv_line_values(self) -> list:
        return [
            self.id,
            self.event_name,
            self.user_name,
            self.user_id,
            self.partner_name,
            self.partner_id,
            self.initialized_at,
            self.due_at,
            self.completed_at,
            self.status,
            self.rerolls_used,
            self.tier_num,
            self.tier_num_partner,
            self.winner,
        ] + self.game_names

    def to_csv_line(self) -> str:
        return (
            ",".join(
                f'"{str(v)}"' if v is not None else ""
                for v in self.__to_csv_line_values()
            )
            + "\n"
        )


ONE_HELL_OF_A_DAY_WINS = (15, 34, 21, 94)


def download_sheet_as_csv(sheet: Literal["ce", "mine"], page: Literal["solo", "coop"]):
    # https://docs.google.com/spreadsheets/d/1-FUFnYZwT_GoJYdi63y1UAk39XTaErtnyabTmYgaOYo/edit?gid=38405307#gid=38405307
    SOLO_ROLL_GID = 493550511
    COOP_ROLL_GID = 38405307

    if sheet == "ce":
        sheet_id = "1-FUFnYZwT_GoJYdi63y1UAk39XTaErtnyabTmYgaOYo"
        if page == "coop":
            gid = COOP_ROLL_GID
            fname = "coop"
        elif page == "solo":
            gid = SOLO_ROLL_GID
            fname = "solo"
    elif sheet == "mine":
        sheet_id = "1jvYRLshEu65s15NKLNmVxUeTFh-y73Ftd1Quy2uLs3M"
        gid = 1229725517
        fname = "mine"

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"

    # The "mine" sheet has a summary row in row 1 that concatenates all column values;
    # skip it so the CSV only contains the actual roll rows.
    skiprows = [0] if sheet == "mine" else None
    df = pd.read_csv(url, skiprows=skiprows)
    df.to_csv(f"my_downloaded_data_{fname}.csv", index=False)


def pull_range(
    start_column: int,
    start_row: int,
    end_column: int,
    end_row: int,
    sheet: Literal["solo"] | Literal["coop"] = "solo",
):
    # Load without a header since the file has no clean header row
    df = pd.read_csv(f"my_downloaded_data_{sheet}.csv", header=None)

    # D6:H40 → columns D-H (indices 3-7), rows 6-40 (indices 5-39)
    if sheet == "solo":
        result = df.iloc[
            (start_row - 3) : (end_row - 2), (start_column - 1) : (end_column)
        ]
    elif sheet == "coop":
        result = df.iloc[
            (start_row - 23) : (end_row - 22), (start_column - 1) : (end_column)
        ]

    return result.values.tolist()


# ---- solo roll win getters ---------------------------------------------------------------------


def _all() -> list[RollRepresentation]:
    return (
        one_hell_of_a_day_wins()
        + one_hell_of_a_week_wins()
        + one_hell_of_a_month_wins()
        + two_week_t2_streak_wins()
        + two_two_two_two_two_wins()
        + never_lucky_wins()
        + triple_threat_wins()
        + let_fate_decide_wins()
        + fourward_thinking_wins()
        + destiny_alignment_wins()
    )


def one_hell_of_a_day_wins() -> list[RollRepresentation]:
    x = pull_range(15, 35, 22, 94)

    rolls = []
    for item in x:
        name = item[0]
        for _value in item[1:]:
            if isinstance(_value, float) and math.isnan(_value):
                break
            rolls.append(
                RollRepresentation(
                    event_name="One Hell of a Day",
                    user_name=name,
                    game_names=[_value],  # type: ignore
                    status="won",
                )
            )

    return rolls


def one_hell_of_a_week_wins() -> list[RollRepresentation]:
    x = pull_range(24, 23, 33, 49)

    rolls = []
    for item in x:
        name = item[0]
        games = []
        for i in range(5):
            games.append(item[1 + i * 2])
        rolls.append(
            RollRepresentation(
                event_name="One Hell of a Week",
                user_name=name,
                game_names=games,
                status="won",
            )
        )
    return rolls


def one_hell_of_a_month_wins() -> list[RollRepresentation]:
    x = pull_range(39, 104, 48, 254)

    rolls = []
    for i, line in enumerate(x):
        if line[0] != "Name":
            continue
        name = x[i + 1][0]
        games = []

        for row in range(5):
            for col in range(5):
                games.append(x[i + 2 + row][1 + col * 2])
        rolls.append(
            RollRepresentation(
                event_name="One Hell of a Month",
                user_name=name,
                game_names=games,
                status="won",
            )
        )
    return rolls


def two_week_t2_streak_wins() -> list[RollRepresentation]:
    x = pull_range(54, 27, 57, 51)

    rolls = []
    for item in x:
        rolls.append(
            RollRepresentation(
                event_name="Two Week T2 Streak",
                user_name=item[0],
                game_names=[item[1], item[3]],
                status="won",
            )
        )
    return rolls


def two_two_two_two_two_wins() -> list[RollRepresentation]:
    x = pull_range(63, 33, 70, 41)

    rolls = []
    for item in x:
        rolls.append(
            RollRepresentation(
                event_name='Two "Two Week T2 Streak" Streak',
                user_name=item[0],
                game_names=[item[1], item[3], item[5], item[7]],
                status="won",
            )
        )
    return rolls


def never_lucky_wins() -> list[RollRepresentation]:
    x = pull_range(77, 96, 82, 130)

    rolls = []
    for item in x:
        name = item[0]
        for _value in item[1:]:
            if isinstance(_value, float) and math.isnan(_value):
                break
            rolls.append(
                RollRepresentation(
                    event_name="Never Lucky",
                    user_name=name,
                    game_names=[_value],  # type: ignore
                    status="won",
                )
            )
    return rolls


def triple_threat_wins() -> list[RollRepresentation]:
    x = pull_range(86, 28, 91, 40)

    rolls = []
    for item in x:
        rolls.append(
            RollRepresentation(
                event_name="Triple Threat",
                user_name=item[0],
                game_names=[item[1], item[3], item[5]],
                status="won",
            )
        )
    return rolls


def let_fate_decide_wins() -> list[RollRepresentation]:
    x = pull_range(97, 115, 102, 150)

    rolls = []
    for item in x:
        name = item[0]
        for _value in item[1:]:
            if isinstance(_value, float) and math.isnan(_value):
                break
            rolls.append(
                RollRepresentation(
                    event_name="Let Fate Decide",
                    user_name=name,
                    game_names=[_value],  # type: ignore
                    status="won",
                )
            )
    return rolls


def fourward_thinking_wins() -> list[RollRepresentation]:
    x = pull_range(106, 63, 113, 141)

    rolls = []
    for i, line in enumerate(x):
        if line[0] != "Name":
            continue
        name = x[i + 1][0]
        games = []
        rerolls_used = 0

        for row in range(4):
            games.append(x[row + i + 2][2])

            _value = x[row + i + 2][7]
            if isinstance(_value, float) and math.isnan(_value):
                continue

            if "Yes" in x[row + i + 2][7]:
                rerolls_used += 1

        rolls.append(
            RollRepresentation(
                event_name="Fourward Thinking",
                user_name=name,
                game_names=games,
                status="won",
                rerolls_used=rerolls_used,
            )
        )
    return rolls


# ---- co op roll win getters ---------------------------------------------------------------------


def destiny_alignment_wins() -> list[RollRepresentation]:
    x = pull_range(5, 102, 10, 119, "coop")

    rolls = []
    for item in x:
        user = item[0]
        partner = item[1]
        rolls.append(
            RollRepresentation(
                event_name="Destiny Alignment",
                user_name=user,
                game_names=[item[3], item[5]],
                status="won",
                partner_name=partner,
            )
        )
    return rolls


def soul_mates_wins() -> list[RollRepresentation]:
    x = pull_range(16, 88, 19, 99, "coop")

    rolls = []
    for item in x:
        rolls.append(
            RollRepresentation(
                event_name="Soul Mates",
                user_name=item[0],
                game_names=[item[3]],
                status="won",
                partner_name=item[1],
            )
        )
    return rolls


# ---- conglomerate functions ---------------------------------------------------------------------


def dumpwins(lst: list[RollRepresentation]):
    with open("my_friendly_data.csv", "w") as f:
        for item in lst:
            f.write(item.to_csv_line())


def write_mappings_users():
    return
    with open("namemappings.json", "w") as f:
        json.dump(SupabaseReader.id_to_name_mappings(True), f, indent=4)


def write_mappings_games():
    with open("namemappings_games.json", "w") as f:
        json.dump(SupabaseReader.game_to_id_mappings(True), f, indent=4)


def insert_user_ids(partner: bool = False):
    "Inserts user IDs if it can find a match"
    with open("namemappings.json", "r") as f:
        mappings = json.load(f)

    lower_names = set([t.lower() for t in mappings])

    max_cols = 50
    df = pd.read_csv("my_friendly_data.csv", header=None, names=range(max_cols))
    data = df.values.tolist()

    for item in data:
        user_name: str = item[1]
        if user_name.lower() in lower_names:
            item[2] = mappings[user_name.lower()]

        partner_name = item[3]
        if not isinstance(partner_name, str):
            continue

        if partner_name.lower() in lower_names:
            item[4] = mappings[partner_name.lower()]

    df_out = pd.DataFrame(data)
    df_out.to_csv("my_friendly_data.csv", index=False, header=False)


def collect_unknown_names() -> set[str]:
    max_cols = 50
    df = pd.read_csv("my_friendly_data.csv", header=None, names=range(max_cols))
    data = df.values.tolist()

    unknown_names: set[str] = set()
    for item in data:
        if not isinstance(item[2], str):
            unknown_names.add(item[1])

        if not isinstance(item[4], str) and isinstance(item[3], str):
            unknown_names.add(item[3])

    return unknown_names


def dump_to_supabase(rolls: list[RollRepresentation]):
    rolls_payload = [r.to_supabase_dict() for r in rolls]
    rollgames_payload = [d for r in rolls for d in r.to_supabase_dict_games()]
    SupabaseReader.dump_sheet_rolls(rolls_payload, rollgames_payload)


def collect_game_names() -> set[str]:
    max_cols = 50
    df = pd.read_csv("my_downloaded_data_mine.csv", header=None, names=range(max_cols))
    data = df.values.tolist()

    game_names = set()

    for line in data:
        index = 14
        while 1:
            _value = line[index]
            if isinstance(_value, float) and math.isnan(_value):
                break

            game_names.add(_value.lower())
            index += 1

    return game_names


def generate_gamename_mapping():
    with open("namemappings_games.json", "r") as f:
        mappings = json.load(f)

    with open("namemappings_games_redirect.json", "r") as f:
        mappings_backup = json.load(f)

    for key, value in mappings_backup.items():
        if value == "":
            continue
        if value.lower() in mappings:
            mappings[key] = mappings[value.lower()]

    return mappings


def names_to_ids(names: list[str], mappings: dict[str, str]):
    ids = []
    for name in names:
        if name.lower() in mappings:
            ids.append(mappings[name.lower()])
        else:
            ids.append("00000000-0000-0000-0000-000000000000")
    return ids


def local_csv_to_roll():
    max_cols = 50
    df = pd.read_csv("my_downloaded_data_mine.csv", header=None, names=range(max_cols))
    data = df.values.tolist()

    mapping = generate_gamename_mapping()

    rolls: list[RollRepresentation] = []
    for line in data:
        game_names = []
        index = 14
        while 1:
            _value = line[index]
            if isinstance(_value, float) and math.isnan(_value):
                break
            game_names.append(_value)
            index += 1
        rolls.append(
            RollRepresentation(
                event_name=line[1],
                user_name=line[2],
                game_names=game_names,
                status=line[9],
                game_ids=names_to_ids(game_names, mapping),
                user_id=line[3],
                partner_name=line[4],
                partner_id=line[5],
                initialized_at=None,
                due_at=None,
                completed_at=None,
                rerolls_used=line[10],
                id=line[0],
            )
        )
    return rolls


def verify_sheet_rolls():
    local_rolls = {r.id: r for r in local_csv_to_roll()}
    db_rolls = {r["id"]: r for r in SupabaseReader.get_sheet_rolls()}

    missing_from_db = local_rolls.keys() - db_rolls.keys()
    unexpected_in_db = db_rolls.keys() - local_rolls.keys()

    mismatches: list[str] = []
    for roll_id in local_rolls.keys() & db_rolls.keys():
        local = local_rolls[roll_id]
        db = db_rolls[roll_id]
        diffs = []
        if local.event_name != db["event_name"]:
            diffs.append(
                f"event_name: local={local.event_name!r} db={db['event_name']!r}"
            )
        if local.user_id != db["user1_ce_id"]:
            diffs.append(f"user_id: local={local.user_id!r} db={db['user1_ce_id']!r}")
        if local.status != db["status"]:
            diffs.append(f"status: local={local.status!r} db={db['status']!r}")
        local_game_ids = local.game_ids or []
        db_game_ids = db["game_ids"]
        if local_game_ids != db_game_ids:
            diffs.append(f"game_ids: local={local_game_ids} db={db_game_ids}")
        if diffs:
            mismatches.append(f"  {roll_id}: " + ", ".join(diffs))

    print(f"Total local: {len(local_rolls)}  |  Total in DB: {len(db_rolls)}")
    if missing_from_db:
        print(f"\nMissing from DB ({len(missing_from_db)}):")
        for rid in missing_from_db:
            r = local_rolls[rid]
            print(f"  {rid}  [{r.event_name}] {r.user_name}")
    if unexpected_in_db:
        print(f"\nIn DB but not in local CSV ({len(unexpected_in_db)}):")
        for rid in unexpected_in_db:
            print(f"  {rid}  [{db_rolls[rid]['event_name']}]")
    if mismatches:
        print(f"\nField mismatches ({len(mismatches)}):")
        for m in mismatches:
            print(m)
    if not missing_from_db and not unexpected_in_db and not mismatches:
        print("All good — local and DB match perfectly.")


dump_to_supabase(local_csv_to_roll())

KNOWN_REMOVED = [
    "find you",
    "big neon tower vs. tiny square",
    "Laserboy",
    "UBERMOSH:OMEGA",
    "Nongunz",
    "Apple Slash",
    "Let's Worm",
    "C-4",
    "Clutchball",
    "DSY",
    "Q.U.B.E.",
    "Aerial Platforms",
    "Find You",
    "Big Flappy Tower vs Tiny Square",
    "Big Neon Tower vs Tiny Square",
    "Pixboy",
    "Jubilee",
    "Philophobia",
    "Super Gravity Ball",
]
known_lower = [f.lower() for f in KNOWN_REMOVED]
