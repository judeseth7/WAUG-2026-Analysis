import csv
from pathlib import Path


# ==================================================
# 1. LOAD DATA
# ==================================================

file_path = Path("data/raw-reports/football-matches.csv")

with file_path.open("r", newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    required_columns = [
        "match_date", "stage", "team_home", "team_away",
        "home_goals", "away_goals", "went_to_penalties",
        "home_penalties", "away_penalties", "winner",
        "source_url", "verification_status",
        "home_shots", "away_shots",
        "home_shots_on_target", "away_shots_on_target"
    ]

    missing_columns = [
        column for column in required_columns
        if column not in (reader.fieldnames or [])
    ]

    if missing_columns:
        raise ValueError(
            f"Missing CSV columns: {', '.join(missing_columns)}"
        )

    matches = list(reader)

print(f"Total matches: {len(matches)}")


def get_value(match, field):
    """Get a stripped string, handling missing values."""
    return str(match.get(field) or "").strip()


def parse_nonnegative_int(value):
    """Convert a value to a non-negative integer."""
    number = int(value)
    if number < 0:
        raise ValueError("Value cannot be negative")
    return number


# 2. VALIDATE DATA


required_values = [
    "match_date", "stage", "team_home", "team_away",
    "home_goals", "away_goals", "went_to_penalties",
    "winner", "source_url", "verification_status"
]

errors = []
seen = set()
valid_scores = {}
valid_penalties = {}


for row_number, match in enumerate(matches, start=2):

    # Required values
    for field in required_values:
        if not get_value(match, field):
            errors.append(f"Row {row_number}: missing {field}")

    home = get_value(match, "team_home")
    away = get_value(match, "team_away")

    # Check duplicate fixtures
    fixture = (
        get_value(match, "match_date"),
        get_value(match, "stage").casefold(),
        home.casefold(),
        away.casefold()
    )

    if fixture in seen:
        errors.append(
            f"Row {row_number}: possible duplicate fixture"
        )
    seen.add(fixture)

    # Check match scores
    try:
        home_goals = parse_nonnegative_int(
            get_value(match, "home_goals")
        )
        away_goals = parse_nonnegative_int(
            get_value(match, "away_goals")
        )
        valid_scores[row_number] = (home_goals, away_goals)

    except ValueError:
        errors.append(
            f"Row {row_number}: invalid home or away goals"
        )

    # Check penalty indicator and scores
    penalty_status = get_value(
        match, "went_to_penalties"
    ).casefold()

    if penalty_status not in ("yes", "no"):
        errors.append(
            f"Row {row_number}: went_to_penalties must be Yes or No"
        )

    elif penalty_status == "yes":
        try:
            home_pens = parse_nonnegative_int(
                get_value(match, "home_penalties")
            )
            away_pens = parse_nonnegative_int(
                get_value(match, "away_penalties")
            )

            if home_pens == away_pens:
                errors.append(
                    f"Row {row_number}: penalty scores are tied"
                )
            else:
                valid_penalties[row_number] = (
                    home_pens, away_pens
                )

        except ValueError:
            errors.append(
                f"Row {row_number}: missing or invalid penalty scores"
            )

    # Check shooting statistics.
    # All four values must be present together or all be blank.
    shooting_fields = [
        "home_shots", "away_shots",
        "home_shots_on_target", "away_shots_on_target"
    ]

    shooting_values = [
        get_value(match, field)
        for field in shooting_fields
    ]

    any_shooting_data = any(shooting_values)
    all_shooting_data = all(shooting_values)

    if any_shooting_data and not all_shooting_data:
        errors.append(
            f"Row {row_number}: incomplete shooting statistics; "
            "fill all four fields or leave all four blank"
        )

    elif all_shooting_data:
        try:
            home_shots = parse_nonnegative_int(
                get_value(match, "home_shots")
            )
            away_shots = parse_nonnegative_int(
                get_value(match, "away_shots")
            )
            home_sot = parse_nonnegative_int(
                get_value(match, "home_shots_on_target")
            )
            away_sot = parse_nonnegative_int(
                get_value(match, "away_shots_on_target")
            )

            if home_sot > home_shots:
                raise ValueError(
                    "home shots on target exceed total shots"
                )

            if away_sot > away_shots:
                raise ValueError(
                    "away shots on target exceed total shots"
                )

        except ValueError as error:
            errors.append(
                f"Row {row_number}: invalid shooting statistics "
                f"({error})"
            )

    # Check verification label
    if get_value(
        match, "verification_status"
    ).casefold() != "verified":
        errors.append(
            f"Row {row_number}: result is not marked Verified"
        )


# ==================================================
# 3. VALIDATE WINNER
# ==================================================

for row_number, match in enumerate(matches, start=2):

    if row_number not in valid_scores:
        continue

    home_goals, away_goals = valid_scores[row_number]

    home = get_value(match, "team_home")
    away = get_value(match, "team_away")
    winner = get_value(match, "winner")

    penalty_status = get_value(
        match, "went_to_penalties"
    ).casefold()

    if not home or not away or not winner:
        continue

    if home_goals > away_goals:
        expected_winner = home

    elif away_goals > home_goals:
        expected_winner = away

    elif penalty_status == "yes":
        if row_number not in valid_penalties:
            continue

        home_pens, away_pens = valid_penalties[row_number]
        expected_winner = (
            home if home_pens > away_pens else away
        )

    elif penalty_status == "no":
        expected_winner = "Draw"

    else:
        continue

    if winner.casefold() != expected_winner.casefold():
        errors.append(
            f"Row {row_number}: winner mismatch — "
            f"expected {expected_winner}, got {winner}"
        )


# ==================================================
# 4. VALIDATION REPORT
# ==================================================

print("\nVALIDATION RESULTS")

if errors:
    for error in errors:
        print("-", error)

    print(f"\nFound {len(errors)} issue(s).")
    print("Fix these issues before running the analysis.")

else:
    print("No issues found by these checks.")


# ==================================================
# 5. ANALYSIS — ONLY IF VALIDATION PASSES
# ==================================================

if not errors:

    # ----------------------------------------------
    # TOURNAMENT SUMMARY
    # ----------------------------------------------

    total_matches = len(matches)
    total_goals = 0
    penalty_matches = 0

    for match in matches:
        home_goals = int(get_value(match, "home_goals"))
        away_goals = int(get_value(match, "away_goals"))

        total_goals += home_goals + away_goals

        if get_value(
            match, "went_to_penalties"
        ).casefold() == "yes":
            penalty_matches += 1

    average_goals = (
        total_goals / total_matches if total_matches else 0
    )

    print("\nTOURNAMENT SUMMARY")
    print(f"Total matches: {total_matches}")
    print(f"Total goals: {total_goals}")
    print(f"Average goals per match: {average_goals:.2f}")
    print(f"Matches decided by penalties: {penalty_matches}")

    # ----------------------------------------------
    # INITIALISE TEAM STATISTICS
    # ----------------------------------------------

    teams = {}
    penalty_stats = {}

    for match in matches:
        home = get_value(match, "team_home")
        away = get_value(match, "team_away")

        for team in (home, away):
            if team not in teams:
                teams[team] = {
                    "MP": 0,
                    "W": 0,
                    "D": 0,
                    "L": 0,
                    "GF": 0,
                    "GA": 0,
                    "GD": 0,
                    "Pts": 0,
                    "WinPct": 0.0,
                    "Shots": 0,
                    "ShotsOnTarget": 0,
                    "GoalsFromShotMatches": 0,
                    "ShootingMatches": 0,
                    "ShotAccuracyPct": None,
                    "ConversionPct": None
                }

                penalty_stats[team] = {
                    "Played": 0,
                    "Won": 0,
                    "Lost": 0
                }

    # ----------------------------------------------
    # PROCESS MATCHES
    # ----------------------------------------------

    for row_number, match in enumerate(matches, start=2):

        home = get_value(match, "team_home")
        away = get_value(match, "team_away")

        home_goals = int(get_value(match, "home_goals"))
        away_goals = int(get_value(match, "away_goals"))

        # Update matches and goals
        teams[home]["MP"] += 1
        teams[home]["GF"] += home_goals
        teams[home]["GA"] += away_goals

        teams[away]["MP"] += 1
        teams[away]["GF"] += away_goals
        teams[away]["GA"] += home_goals

        # Regular match result (shootouts are separate)
        if home_goals > away_goals:
            teams[home]["W"] += 1
            teams[away]["L"] += 1

        elif away_goals > home_goals:
            teams[away]["W"] += 1
            teams[home]["L"] += 1

        else:
            teams[home]["D"] += 1
            teams[away]["D"] += 1

        # Penalty shootout results
        if row_number in valid_penalties:
            home_pens, away_pens = valid_penalties[row_number]

            penalty_stats[home]["Played"] += 1
            penalty_stats[away]["Played"] += 1

            if home_pens > away_pens:
                penalty_stats[home]["Won"] += 1
                penalty_stats[away]["Lost"] += 1
            else:
                penalty_stats[away]["Won"] += 1
                penalty_stats[home]["Lost"] += 1

        # Shooting analysis only when all four stats are present
        shooting_fields = [
            "home_shots", "away_shots",
            "home_shots_on_target", "away_shots_on_target"
        ]

        if all(get_value(match, field) for field in shooting_fields):

            home_shots = int(get_value(match, "home_shots"))
            away_shots = int(get_value(match, "away_shots"))
            home_sot = int(get_value(match, "home_shots_on_target"))
            away_sot = int(get_value(match, "away_shots_on_target"))

            teams[home]["Shots"] += home_shots
            teams[home]["ShotsOnTarget"] += home_sot
            teams[home]["GoalsFromShotMatches"] += home_goals
            teams[home]["ShootingMatches"] += 1

            teams[away]["Shots"] += away_shots
            teams[away]["ShotsOnTarget"] += away_sot
            teams[away]["GoalsFromShotMatches"] += away_goals
            teams[away]["ShootingMatches"] += 1

    # ----------------------------------------------
    # CALCULATE METRICS
    # ----------------------------------------------

    for team, stats in teams.items():

        stats["GD"] = stats["GF"] - stats["GA"]
        stats["Pts"] = stats["W"] * 3 + stats["D"]

        stats["WinPct"] = round(
            stats["W"] / stats["MP"] * 100, 1
        ) if stats["MP"] else 0.0

        # Rates are calculated from totals, not average match percentages.
        # None means no usable shooting data or no attempts.
        if stats["Shots"] > 0:
            stats["ShotAccuracyPct"] = round(
                stats["ShotsOnTarget"] / stats["Shots"] * 100, 1
            )

            stats["ConversionPct"] = round(
                stats["GoalsFromShotMatches"] / stats["Shots"] * 100, 1
            )

    # ----------------------------------------------
    # TEAM PERFORMANCE TABLE
    # ----------------------------------------------

    sorted_teams = sorted(
        teams.items(),
        key=lambda item: (
            item[1]["Pts"],
            item[1]["GD"],
            item[1]["GF"]
        ),
        reverse=True
    )

    print("\nTEAM PERFORMANCE")
    print(
        f"{'Team':43} {'MP':>2} {'W':>2} {'D':>2} "
        f"{'L':>2} {'GF':>3} {'GA':>3} {'GD':>3} "
        f"{'Pts':>4} {'Win%':>6}"
    )

    for team, stats in sorted_teams:
        print(
            f"{team:43} "
            f"{stats['MP']:>2} "
            f"{stats['W']:>2} "
            f"{stats['D']:>2} "
            f"{stats['L']:>2} "
            f"{stats['GF']:>3} "
            f"{stats['GA']:>3} "
            f"{stats['GD']:>3} "
            f"{stats['Pts']:>4} "
            f"{stats['WinPct']:>5.1f}%"
        )

    # ----------------------------------------------
    # SHOOTING ANALYSIS
    # ----------------------------------------------

    shooting_matches = sum(
        1 for match in matches
        if all(
            get_value(match, field)
            for field in [
                "home_shots", "away_shots",
                "home_shots_on_target", "away_shots_on_target"
            ]
        )
    )

    print("\nSHOOTING ANALYSIS")
    print(
        f"Matches with shooting statistics: "
        f"{shooting_matches} of {total_matches}"
    )
    print("Rates use only matches with complete shooting data.")
    print(
        f"{'Team':43} {'Matches':>7} {'Shots':>7} "
        f"{'On Target':>10} {'Accuracy%':>10} {'Conversion%':>12}"
    )

    for team, stats in sorted_teams:
        accuracy = (
            f"{stats['ShotAccuracyPct']:.1f}"
            if stats["ShotAccuracyPct"] is not None
            else "N/A"
        )

        conversion = (
            f"{stats['ConversionPct']:.1f}"
            if stats["ConversionPct"] is not None
            else "N/A"
        )

        print(
            f"{team:43} "
            f"{stats['ShootingMatches']:>7} "
            f"{stats['Shots']:>7} "
            f"{stats['ShotsOnTarget']:>10} "
            f"{accuracy:>10} "
            f"{conversion:>12}"
        )

    # ----------------------------------------------
    # PENALTY SHOOTOUT TABLE
    # ----------------------------------------------

    print("\nPENALTY SHOOTOUT PERFORMANCE")
    print(
        f"{'Team':43} {'Played':>6} {'Won':>5} {'Lost':>5}"
    )

    sorted_penalties = sorted(
        penalty_stats.items(),
        key=lambda item: (
            item[1]["Won"],
            -item[1]["Lost"]
        ),
        reverse=True
    )

    for team, stats in sorted_penalties:
        print(
            f"{team:43} "
            f"{stats['Played']:>6} "
            f"{stats['Won']:>5} "
            f"{stats['Lost']:>5}"
        )

    # ----------------------------------------------
    # EXPORT TEAM PERFORMANCE
    # ----------------------------------------------

    output_dir = Path("reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    team_output = output_dir / "team-performances.csv"

    team_columns = [
        "Team", "MP", "W", "D", "L",
        "GF", "GA", "GD", "Pts", "WinPct",
        "ShootingMatches", "Shots", "ShotsOnTarget",
        "ShotAccuracyPct", "ConversionPct"
    ]

    with team_output.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=team_columns
        )

        writer.writeheader()

        for team, stats in sorted_teams:
            writer.writerow({
                "Team": team,
                **{
                    column: stats[column]
                    for column in team_columns
                    if column != "Team"
                }
            })

    print(f"\nTeam performance exported to: {team_output}")

    # ----------------------------------------------
    # EXPORT MATCH-LEVEL SHOOTING DATA
    # ----------------------------------------------

    match_output = output_dir / "match-shooting-analysis.csv"

    with match_output.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:

        match_columns = [
            "match_date", "stage", "team_home", "team_away",
            "home_goals", "away_goals",
            "home_shots", "away_shots",
            "home_shots_on_target", "away_shots_on_target",
            "home_shot_accuracy_pct", "away_shot_accuracy_pct",
            "home_conversion_pct", "away_conversion_pct"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=match_columns
        )

        writer.writeheader()

        for match in matches:
            row = {
                field: get_value(match, field)
                for field in [
                    "match_date", "stage", "team_home", "team_away",
                    "home_goals", "away_goals",
                    "home_shots", "away_shots",
                    "home_shots_on_target", "away_shots_on_target"
                ]
            }

            if all(
                get_value(match, field)
                for field in [
                    "home_shots", "away_shots",
                    "home_shots_on_target", "away_shots_on_target"
                ]
            ):
                home_shots = int(get_value(match, "home_shots"))
                away_shots = int(get_value(match, "away_shots"))
                home_sot = int(get_value(match, "home_shots_on_target"))
                away_sot = int(get_value(match, "away_shots_on_target"))

                row["home_shot_accuracy_pct"] = (
                    round(home_sot / home_shots * 100, 1)
                    if home_shots else ""
                )

                row["away_shot_accuracy_pct"] = (
                    round(away_sot / away_shots * 100, 1)
                    if away_shots else ""
                )

                home_goals = int(get_value(match, "home_goals"))
                away_goals = int(get_value(match, "away_goals"))

                row["home_conversion_pct"] = (
                    round(home_goals / home_shots * 100, 1)
                    if home_shots else ""
                )

                row["away_conversion_pct"] = (
                    round(away_goals / away_shots * 100, 1)
                    if away_shots else ""
                )

            else:
                row["home_shot_accuracy_pct"] = ""
                row["away_shot_accuracy_pct"] = ""
                row["home_conversion_pct"] = ""
                row["away_conversion_pct"] = ""

            writer.writerow(row)

    print(f"Match shooting analysis exported to: {match_output}")
