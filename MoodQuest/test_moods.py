"""Run: python test_moods.py   (or: pytest -q)
12 sample diary entries, including challenging ones (negation, mixed feelings,
sarcasm, very short, no emotion words)."""
from mood_engine import classify, STRESSED, TIRED, EXCITED, CALM
from quests import make_quest
import progress
from datetime import date, timedelta

# (entry, expected mood, why it's interesting)
SAMPLES = [
    ("I have a math test tomorrow and so much homework piled up. I can't breathe.", STRESSED, "clear"),
    ("I stayed up late and I'm so tired. I kept yawning in every class.", TIRED, "clear"),
    ("We won the football match today! I'm so pumped and can't stop smiling!", EXCITED, "clear"),
    ("Quiet, peaceful day. I read in the library and felt really relaxed.", CALM, "clear"),
    ("I'm not tired at all, I'm super hyped for the field trip tomorrow!", EXCITED, "negation"),
    ("I'm exhausted but the tournament this weekend has me so excited.", EXCITED, "contrast: later clause wins"),
    ("I'm not stressed about the exam, I studied and feel pretty calm.", CALM, "negation"),
    ("Oh great, another pop quiz. Just what I needed today.", STRESSED, "sarcasm (caught via 'pop quiz')"),
    ("Presentation, two deadlines and an argument with my friend. Too much.", STRESSED, "no direct mood word"),
    ("Today was a bit boring and I felt sluggish, no energy after lunch.", TIRED, "softener + mood words"),
    ("Today was okay. Nothing special, just a nice normal day.", CALM, "neutral entry"),
    ("I am not feeling very calm today, I feel nervous about the presentation.", STRESSED, "negated 'calm'"),
    ("Ugh my brain is fried, so much to do and no sleep.", TIRED, "ambiguous: tired vs stressed, both defensible"),
]

# Known limitation (documented, not counted in accuracy): pure sarcasm with positive words.
KNOWN_LIMITS = [
    ("I just love failing quizzes, so fun.", STRESSED, "sarcasm using positive words"),
]


def run():
    ok = 0
    for text, expected, why in SAMPLES:
        r = classify(text)
        passed = r["mood"] == expected
        ok += passed
        print(f"[{'PASS' if passed else 'FAIL'}] ({why}) expected={expected} got={r['mood']} "
              f"conf={r['confidence']}\n        {text}")
    for text, expected, why in KNOWN_LIMITS:
        got = classify(text)["mood"]
        print(f"[KNOWN LIMIT] ({why}) expected={expected} got={got}\n        {text}")
    print(f"\nAccuracy: {ok}/{len(SAMPLES)} = {ok / len(SAMPLES):.0%}")
    return ok, len(SAMPLES)


def test_samples():
    ok, total = run()
    assert ok >= 10, f"only {ok}/{total} correct"


def test_quest_has_three_steps_for_every_mood():
    for mood in (STRESSED, TIRED, EXCITED, CALM):
        q = make_quest(mood, "I have a math test")
        assert len(q["steps"]) == 3 and all(q["steps"])


def test_points_and_streak():
    data = {}
    d0 = date(2026, 10, 18)
    progress.complete_quest(data, "A", CALM, "q", 3, today=d0)
    progress.complete_quest(data, "A", CALM, "q", 3, today=d0 + timedelta(days=1))
    s = data["A"]
    assert s["points"] == 100 and s["streak"] == 2
    # missing a day resets streak; partial quest gives points but no streak
    progress.complete_quest(data, "A", CALM, "q", 2, today=d0 + timedelta(days=3))
    assert s["streak"] == 2 and s["points"] == 120
    progress.complete_quest(data, "A", CALM, "q", 3, today=d0 + timedelta(days=3))
    assert s["streak"] == 1 and s["best_streak"] == 2


if __name__ == "__main__":
    run()
