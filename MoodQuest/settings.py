"""App settings that Developer mode can change. Stored in config.json."""
import json
import os

CONFIG_PATH = "config.json"

SECTIONS = {"stats": "📊 Stats", "diary": "📝 Diary + camera", "quest": "🗺️ Quest", "log": "📈 Quest log"}

DEFAULTS = {
    "palette": "Forest (green)",
    "points_per_step": 10,
    "bonus": 20,
    "require_photo": True,      # diary needs a camera photo before analysis
    "face_weight": 0.3,         # how much the face counts vs. the diary text (0 to 1)
    "happy_low_below": 5.0,     # happiness score below this = sad / low energy
    "stressed_below": 3.0,      # happiness score below this = stressed / overwhelmed
    "section_order": list(SECTIONS),
    "custom_quests": {},        # {mood: [{"title": str, "steps": [3 strings]}]}
}


def load(path=CONFIG_PATH):
    cfg = json.loads(json.dumps(DEFAULTS))
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass
    # keep section order valid even if sections were added/removed
    order = [s for s in cfg["section_order"] if s in SECTIONS]
    order += [s for s in SECTIONS if s not in order]
    cfg["section_order"] = order
    return cfg


def save(cfg, path=CONFIG_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
