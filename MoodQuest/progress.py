"""Progress tracking: points, daily streak, quest history. Stored in a JSON file."""
import json
import os
from datetime import date, datetime, timedelta

DEFAULT_PATH = "progress.json"


def load(path=DEFAULT_PATH):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save(data, path=DEFAULT_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_student(data, name):
    return data.setdefault(name, {"points": 0, "streak": 0, "best_streak": 0,
                                  "last_date": None, "history": []})


def update_streak(student, today):
    """Streak counts consecutive days with at least one completed quest."""
    last = student["last_date"]
    if last == today.isoformat():
        return  # already counted today
    if last == (today - timedelta(days=1)).isoformat():
        student["streak"] += 1
    else:
        student["streak"] = 1
    student["best_streak"] = max(student["best_streak"], student["streak"])
    student["last_date"] = today.isoformat()


def complete_quest(data, name, mood, title, steps_done, points_per_step=10, bonus=20,
                   today=None):
    """Record a quest. Full completion (3/3) earns the bonus and counts toward the streak."""
    today = today or date.today()
    student = get_student(data, name)
    earned = steps_done * points_per_step
    full = steps_done == 3
    if full:
        earned += bonus
        update_streak(student, today)
    student["points"] += earned
    student["history"].append({"time": datetime.now().isoformat(timespec="seconds"),
                               "mood": mood, "quest": title, "steps_done": steps_done,
                               "completed": full, "points": earned})
    return earned


def current_streak(student, today=None):
    """Streak shown to the user: resets to 0 if yesterday was missed."""
    today = today or date.today()
    last = student.get("last_date")
    if last in (today.isoformat(), (today - timedelta(days=1)).isoformat()):
        return student["streak"]
    return 0
