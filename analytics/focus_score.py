from database.activity_db import get_activities


def calculate_focus_score():
    activities = get_activities()

    productive_seconds = 0
    neutral_seconds = 0
    distracting_seconds = 0

    for activity in activities:

        duration = activity[6]
        category = activity[5]

        if duration is None:
            duration = 0

        if category == "PRODUCTIVE":
            productive_seconds += duration

        elif category == "NEUTRAL":
            neutral_seconds += duration

        elif category == "DISTRACTING":
            distracting_seconds += duration

    total_seconds = (
        productive_seconds
        + neutral_seconds
        + distracting_seconds
    )

    if total_seconds == 0:
        return {
            "score": 0,
            "productive_seconds": 0,
            "neutral_seconds": 0,
            "distracting_seconds": 0,
            "total_seconds": 0
        }

    score = (
        productive_seconds
        / total_seconds
    ) * 100

    return {
        "score": round(score),
        "productive_seconds": productive_seconds,
        "neutral_seconds": neutral_seconds,
        "distracting_seconds": distracting_seconds,
        "total_seconds": total_seconds
    }


def print_focus_score():

    result = calculate_focus_score()

    print("\n==============================")
    print("       FOCUS SCORE")
    print("==============================")

    print(
        f"Productive:   "
        f"{result['productive_seconds']} sec"
    )

    print(
        f"Neutral:      "
        f"{result['neutral_seconds']} sec"
    )

    print(
        f"Distracting:  "
        f"{result['distracting_seconds']} sec"
    )

    print(
        f"Total:        "
        f"{result['total_seconds']} sec"
    )

    print("------------------------------")

    print(
        f"Focus Score:  "
        f"{result['score']}%"
    )

    print("==============================\n")


if __name__ == "__main__":

    print_focus_score()