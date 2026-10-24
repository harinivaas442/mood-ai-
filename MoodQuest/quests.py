"""Three-step quest generator. Each mood has several quest lines; one is picked
deterministically from the entry text so the same entry gives the same quest,
and a topic from the diary (e.g. "math", "football") is woven into the steps."""
import hashlib
import re

from mood_engine import STRESSED, TIRED, EXCITED, CALM

MOOD_STYLE = {
    STRESSED: {"emoji": "😰", "color": "#e76f51"},
    TIRED: {"emoji": "😴", "color": "#6c757d"},
    EXCITED: {"emoji": "🤩", "color": "#f4a261"},
    CALM: {"emoji": "😊", "color": "#2a9d8f"},
}

QUESTS = {
    STRESSED: [
        {"title": "Quest of the Steady Breath", "steps": [
            "Box breathing: breathe in for 4, hold 4, out 4, hold 4. Repeat 4 times.",
            "Brain dump: write every worry on paper, then circle the ONE you can act on today{topic}.",
            "Do a 10-minute focus sprint on that one thing, then stand up and stretch."]},
        {"title": "Quest of the Tiny Steps", "steps": [
            "Name 5 things you can see, 4 you can touch, 3 you can hear to ground yourself.",
            "Split the biggest task{topic} into three tiny pieces and write them down.",
            "Finish only the first piece, then reward yourself with a glass of water and a short walk."]},
    ],
    TIRED: [
        {"title": "Quest of the Energy Spark", "steps": [
            "Drink a full glass of water and open a window or step outside for fresh air.",
            "Do 20 seconds each of jumping jacks, shoulder rolls and a big stretch.",
            "Pick one small, easy task{topic} and do it for 10 minutes. Plan an early bedtime tonight."]},
        {"title": "Quest of the Gentle Recharge", "steps": [
            "Splash cool water on your face and take 5 slow deep breaths.",
            "Take a 5-minute walk, no phone, just notice what's around you.",
            "Eat a small snack with protein (nuts, yogurt, fruit) and write down one thing that would help you sleep better."]},
    ],
    EXCITED: [
        {"title": "Quest of the Energy Channel", "steps": [
            "Write down what you're excited about{topic} in 3 sentences, capture the feeling!",
            "Channel the energy: 2 minutes of your favorite movement or dance.",
            "Share the good news with a friend or family member, and set one goal to make it even better."]},
        {"title": "Quest of the Bright Idea", "steps": [
            "Take 3 deep breaths so the excitement is focused, not scattered.",
            "List 3 things you could do while you ride this wave{topic}.",
            "Start the first one for 15 minutes, then celebrate with a high five (real or imaginary)."]},
    ],
    CALM: [
        {"title": "Quest of the Gratitude Garden", "steps": [
            "Write down 3 things from today that made you feel good{topic}.",
            "Send a kind message or compliment to someone in your life.",
            "Use this calm energy for a 15-minute goal: read, draw, or practice something you enjoy."]},
        {"title": "Quest of the Peaceful Planner", "steps": [
            "Sit quietly for 2 minutes and notice what is making today feel good.",
            "Plan tomorrow: write your top 3 priorities while your mind is clear.",
            "Do one kind thing for yourself (music, a walk, a hobby) to lock in this feeling."]},
    ],
}

TOPICS = ["math", "science", "english", "history", "homework", "exam", "test", "quiz",
          "project", "presentation", "football", "soccer", "basketball", "match", "game",
          "trip", "party", "friends", "family", "music", "art", "reading"]


def find_topic(text):
    words = set(re.findall(r"[a-z]+", text.lower()))
    for t in TOPICS:
        if t in words:
            return t
    return None


def make_quest(mood, text, custom=None, points_per_step=10, bonus=20):
    """Return {title, steps[3], points_per_step, bonus}.

    `custom` is an optional list of quests (from Developer mode) that replaces the defaults."""
    options = custom or QUESTS[mood]
    digest = int(hashlib.md5(text.strip().lower().encode()).hexdigest(), 16)
    quest = options[digest % len(options)]
    topic = find_topic(text)
    suffix = f" (for your {topic})" if topic else ""
    steps = [s.replace("{topic}", suffix) for s in quest["steps"]]
    return {"title": quest["title"], "steps": steps,
            "points_per_step": points_per_step, "bonus": bonus}
