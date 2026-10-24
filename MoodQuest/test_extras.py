"""Run: python test_extras.py  — tests for sign-in, settings, quests and face blending."""
import os
import tempfile

import auth
import face
import settings
from mood_engine import classify, STRESSED, TIRED, EXCITED, CALM
from quests import make_quest


def test_auth():
    p = os.path.join(tempfile.mkdtemp(), "users.json")
    ok, _, u = auth.register("Me@Gmail.com", "password123", "Me", path=p)
    assert ok and u["is_dev"] and u["email"] == "me@gmail.com"
    assert not auth.register("me@gmail.com", "password123", path=p)[0]          # duplicate
    assert not auth.register("bad-email", "password123", path=p)[0]             # invalid email
    assert not auth.register("a@b.com", "short", path=p)[0]                     # short password
    ok, _, u2 = auth.register("friend@gmail.com", "password123", path=p)
    assert ok and not u2["is_dev"]                                              # only first is dev
    assert auth.login("ME@gmail.com", "password123", path=p)[0]
    assert not auth.login("me@gmail.com", "wrongpass", path=p)[0]
    assert "password123" not in open(p).read()                                  # stored hashed


def test_settings_and_custom_quest():
    p = os.path.join(tempfile.mkdtemp(), "config.json")
    cfg = settings.load(p)
    cfg["section_order"] = ["log", "diary"]
    cfg["points_per_step"] = 15
    settings.save(cfg, p)
    cfg2 = settings.load(p)
    assert cfg2["section_order"][:2] == ["log", "diary"] and len(cfg2["section_order"]) == 4
    assert cfg2["points_per_step"] == 15
    q = make_quest(CALM, "good day at school", [{"title": "Mine", "steps": ["a {topic}", "b", "c"]}], 15, 5)
    assert q["title"] == "Mine" and q["points_per_step"] == 15 and q["bonus"] == 5


def test_blend():
    text = classify("Today was fine.")
    stressed_face = {STRESSED: 0.9, TIRED: 0.05, EXCITED: 0.025, CALM: 0.025}
    # strong face signal vs weak text: face shifts the result only if weighted enough
    blended = face.blend(text, stressed_face, 0.8)
    assert blended["mood"] == STRESSED
    # no diary signal -> face decides
    assert face.blend(classify("idk"), stressed_face, 0.3)["mood"] == STRESSED
    # no face -> unchanged
    assert face.blend(text, None)["mood"] == text["mood"]
    # default expression mapping sums to 1 and maps angry to stressed
    angry = {e: (1.0 if e == "angry" else 0.0) for e in face.EXPRESSIONS}
    s = face.probs_to_moods(angry)
    assert abs(sum(s.values()) - 1) < 1e-9 and max(s, key=s.get) == STRESSED


def test_happiness_score_and_thresholds():
    def only(expr):
        return {e: (1.0 if e == expr else 0.0) for e in face.EXPRESSIONS}
    assert face.happiness_score(only("happy")) == 10.0
    assert face.happiness_score(only("neutral")) == 5.0
    assert face.happiness_score(only("angry")) == 0.0
    top = lambda s: max(s, key=s.get)
    assert top(face.probs_to_moods(only("happy"))) == CALM            # smiling is never "Stressed"
    assert top(face.probs_to_moods(only("neutral"))) == CALM          # 5.0 is not below 5
    assert top(face.probs_to_moods(only("sad"))) == STRESSED          # score 1.0 < 3
    mix = {"happy": 0, "neutral": 0.3, "sad": 0.7, "angry": 0, "fear": 0, "disgust": 0, "surprise": 0}
    assert face.happiness_score(mix) == 2.2 and top(face.probs_to_moods(mix)) == STRESSED
    mid = {"happy": 0.2, "neutral": 0.4, "sad": 0.4, "angry": 0, "fear": 0, "disgust": 0, "surprise": 0}
    assert 3 <= face.happiness_score(mid) < 5 and top(face.probs_to_moods(mid)) == TIRED
    surprised = {"happy": 0.2, "neutral": 0, "sad": 0, "angry": 0, "fear": 0, "disgust": 0, "surprise": 0.8}
    assert top(face.probs_to_moods(surprised)) == EXCITED
    # zero face scores must never decide (this used to show up as "Stressed")
    text = classify("Today was fine.")
    assert face.blend(text, {m: 0.0 for m in (STRESSED, TIRED, EXCITED, CALM)})["mood"] == text["mood"]


def test_status_and_dots_never_crash():
    st = face.status()
    assert set(st) == {"model", "face_crop", "dots", "calibration"}
    assert isinstance(face.missing(), list) and face.is_available() == (face.missing() == [])
    assert face.draw_dots(b"not an image") is None  # bad input must not raise


if __name__ == "__main__":
    test_auth(); test_settings_and_custom_quest(); test_blend(); test_happiness_score_and_thresholds(); test_status_and_dots_never_crash()
    print("extras OK")
