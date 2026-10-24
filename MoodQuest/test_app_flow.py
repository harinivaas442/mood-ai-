"""Flow tests for app.py using a SIMULATED Streamlit (no browser needed).

It acts like a user: signs up, takes photos, writes diary entries, swipes cards, uses
Developer mode. It also raises the same errors real Streamlit does for duplicate widgets
and out-of-range progress bars. It cannot check how things LOOK; it checks that the logic
never crashes and does the right thing.

Run: python test_app_flow.py
"""
import json
import os
import random
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


class StopScript(Exception):
    pass


class RerunScript(Exception):
    pass


class Photo:
    def __init__(self, data):
        self.data = data

    def getvalue(self):
        return self.data


class Ctx:
    def __init__(self, st):
        self._st = st

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __getattr__(self, name):
        return getattr(self._st, name)


class FakeSt:
    def __init__(self):
        self.session_state = {}
        self.inputs = {}
        self.clicks = []
        self.camera_next = None
        self.secrets = {}
        self.sidebar = Ctx(self)
        self.user = types.SimpleNamespace(is_logged_in=False, get=lambda k, d="": d)
        self.reset_run()

    def reset_run(self):
        self.log = []
        self.buttons = []
        self.toggles = []
        self.checkboxes = []
        self.cameras = []
        self._ids = set()

    # ---- helpers
    def _id(self, kind, label, key):
        ident = (kind, key if key else label)
        if ident in self._ids:
            raise AssertionError(f"DuplicateWidgetID: {ident}")
        self._ids.add(ident)

    def _val(self, label, key, default):
        if key is not None and key in self.inputs:
            return self.inputs[key]
        return self.inputs.get(label, default)

    def _say(self, kind, text=""):
        self.log.append((kind, str(text)))

    def has(self, kind, sub=""):
        return any(k == kind and sub in t for k, t in self.log)

    # ---- widgets
    def button(self, label, key=None, type=None, **kw):
        self._id("button", label, key)
        self.buttons.append(label)
        for c in list(self.clicks):
            if c == label or c == key:
                self.clicks.remove(c)
                return True
        return False

    form_submit_button = button

    def text_input(self, label, value="", key=None, **kw):
        self._id("text", label, key)
        return self._val(label, key, value)

    def text_area(self, label, value="", key=None, **kw):
        self._id("area", label, key)
        return self._val(label, key, value)

    def checkbox(self, label, value=False, key=None, **kw):
        self._id("check", label, key)
        self.checkboxes.append(label)
        return self._val(label, key, value)

    def toggle(self, label, value=False, key=None, **kw):
        self._id("toggle", label, key)
        self.toggles.append(label)
        return self._val(label, key, value)

    def radio(self, label, options, index=0, key=None, **kw):
        return self._val(label, key, options[index])

    def selectbox(self, label, options, index=0, key=None, **kw):
        return self._val(label, key, list(options)[index])

    def multiselect(self, label, options, default=None, **kw):
        return self._val(label, None, default or [])

    def number_input(self, label, min_value=None, max_value=None, value=0, step=None, **kw):
        return self._val(label, None, value)

    def slider(self, label, min_value=0, max_value=1, value=0, step=None, **kw):
        return self._val(label, None, value)

    def camera_input(self, label, key=None, **kw):
        self._id("camera", label, key)
        self.cameras.append(key)
        if self.camera_next is not None:
            data, self.camera_next = self.camera_next, None
            return Photo(data)
        return None

    # ---- layout
    def columns(self, spec, **kw):
        n = spec if isinstance(spec, int) else len(spec)
        return [Ctx(self) for _ in range(n)]

    def tabs(self, labels):
        return [Ctx(self) for _ in labels]

    def expander(self, *a, **k):
        return Ctx(self)

    def form(self, *a, **k):
        return Ctx(self)

    def spinner(self, *a, **k):
        return Ctx(self)

    def container(self, *a, **k):
        return Ctx(self)

    # ---- output
    def title(self, t, **k): self._say("title", t)
    def subheader(self, t, **k): self._say("subheader", t)
    def caption(self, t, **k): self._say("caption", t)
    def write(self, t="", **k): self._say("write", t)
    def markdown(self, t="", **k): self._say("markdown", t)
    def info(self, t, **k): self._say("info", t)
    def warning(self, t, **k): self._say("warning", t)
    def error(self, t, **k): self._say("error", t)
    def success(self, t, **k): self._say("success", t)
    def balloons(self): self._say("balloons")
    def divider(self): pass
    def set_page_config(self, **k): pass
    def metric(self, label, value, **k): self._say("metric", f"{label}={value}")
    def dataframe(self, df, **k): self._say("dataframe", len(df))
    def bar_chart(self, d, **k): self._say("chart")
    def image(self, img, **k): self._say("image")

    def progress(self, value, text=None):
        assert 0.0 <= value <= 1.0, f"progress value out of range: {value}"
        self._say("progress", text)

    def stop(self): raise StopScript()
    def rerun(self): raise RerunScript()
    def login(self): self._say("login")
    def logout(self): self._say("logout")


def build_env(sortables=False):
    """Fresh simulated Streamlit + fresh temp folder."""
    for m in ["app", "ui", "face", "auth", "settings", "progress", "quests", "mood_engine",
              "streamlit", "streamlit.components", "streamlit.components.v1", "streamlit_sortables"]:
        sys.modules.pop(m, None)
    fake = FakeSt()
    comp, v1 = types.ModuleType("streamlit.components"), types.ModuleType("streamlit.components.v1")
    v1.html = lambda *a, **k: None
    comp.v1 = v1
    fake.components = comp
    sys.modules.update({"streamlit": fake, "streamlit.components": comp, "streamlit.components.v1": v1})
    if sortables:
        ss = types.ModuleType("streamlit_sortables")
        ss.sort_items = lambda labels: list(reversed(labels))
        sys.modules["streamlit_sortables"] = ss
    os.chdir(tempfile.mkdtemp())
    return fake


def run(fake, clicks=(), inputs=None, camera=None):
    """One user action = one script run (plus automatic reruns, like Streamlit)."""
    fake.clicks = list(clicks)
    fake.inputs.update(inputs or {})
    fake.camera_next = camera
    src = open(os.path.join(HERE, "app.py"), encoding="utf-8").read()
    for _ in range(25):
        fake.reset_run()
        try:
            exec(compile(src, "app.py", "exec"), {"__name__": "__main__"})
        except RerunScript:
            continue
        except StopScript:
            return fake
        return fake
    raise AssertionError("rerun loop never settled")


def sign_up(fake, name, email, pw="password123"):
    run(fake, ["Create account"], {"Your name": name, "su_email": email, "su_pw": pw})


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


def take_photo(fake, prefix="diary"):
    run(fake, [f"{prefix}_start"])
    need(fake.cameras, "camera did not turn on after pressing the button")
    run(fake, [], camera=b"JPEGDATA")
    need(not fake.cameras, "camera is still ON after the photo was taken")
    need(fake.session_state.get(f"{prefix}_bytes") == b"JPEGDATA", "photo not stored")


def analyse(fake, text):
    run(fake, ["Find my mood & start quest"], {"Diary entry": text})


# ============================== the 7 rounds ==============================

def round1_sign_in_screen():
    f = build_env()
    run(f)
    need(f.has("title", "Mood Quest"), "no title on sign-in screen")
    need("Sign in" in f.buttons and "Create account" in f.buttons, "sign-in buttons missing")
    need("user" not in f.session_state, "logged in without signing in")
    need(not f.has("metric"), "app content visible before signing in")


def round2_first_account_is_developer():
    f = build_env()
    sign_up(f, "Hari", "hari@gmail.com")
    need(f.session_state["user"]["is_dev"], "first account is not developer")
    need("🛠️ Developer mode" in f.toggles, "developer toggle missing for developer")
    need("Use Hugging Face text model (needs `transformers`)" in f.checkboxes, "dev checkbox missing")
    need(f.has("metric", "Points=0"), "stats missing")
    need(f.has("subheader", "How was your day"), "diary missing")


def round3_normal_user_has_no_settings():
    f = build_env()
    sign_up(f, "Hari", "hari@gmail.com")
    run(f, ["Sign out"])
    need("user" not in f.session_state and f.has("title"), "sign out failed")
    sign_up(f, "Student", "student@gmail.com")
    need(not f.session_state["user"]["is_dev"], "second account became developer")
    need(f.toggles == [], "developer toggle visible to a normal user")
    need("Use Hugging Face text model (needs `transformers`)" not in f.checkboxes, "dev setting visible")
    run(f, [], {"🛠️ Developer mode": True})  # even forcing it must not open dev tabs
    need(not f.has("subheader", "Face Lab") and not f.has("subheader", "Edit quests"), "dev tabs opened")
    need(f.session_state["user"]["is_dev"] is False, "state tampered")


def round4_camera_on_demand_and_diary():
    f = build_env()
    sign_up(f, "Hari", "hari@gmail.com")
    need(not f.cameras, "camera ON before the user asked")
    analyse(f, "I have a math test tomorrow and I am so stressed")
    need(f.has("warning", "turn on the camera"), "no warning when photo missing")
    need("result" not in f.session_state, "analysed without the required photo")
    take_photo(f)
    analyse(f, "x")
    need(f.has("warning", "more"), "short entry not rejected")
    analyse(f, "I have a math test tomorrow and I am so stressed")
    need(f.session_state["result"]["mood"] == "Stressed/Overwhelmed", "wrong mood")
    need("OFF" in f.session_state.get("face_note", ""), "no message that face reading is off")
    need(f.has("warning", "Face reading is OFF"), "face-off warning not shown")
    need(f.session_state.get("diary_bytes") in (None, b""), "photo kept after use")
    need(not f.cameras, "camera on after analysis")
    need(f.has("subheader", "Quest of") or "quest" in f.session_state, "no quest created")
    # face model available: blending path
    import face
    face.is_available = lambda: True
    happy = {"Stressed/Overwhelmed": 0.05, "Tired/Low Energy": 0.05, "Excited/Energized": 0.1, "Calm/Happy": 0.8}
    face.analyse_photo = lambda b, low=5.0, stressed=3.0: {
        "face_found": True, "happiness": 8.6, "mood_scores": happy,
        "probs": {"happy": 0.8, "neutral": 0.1, "sad": 0.05, "angry": 0.02, "fear": 0.01,
                  "disgust": 0.01, "surprise": 0.01}}
    face.draw_dots = lambda b: None
    take_photo(f)
    analyse(f, "whatever happened today")
    need(f.session_state["result"]["mood"] == "Calm/Happy", "face did not decide with empty diary")
    need("face_match" in f.session_state, "face match missing")
    need(f.session_state.get("happiness") == 8.6, "happiness score not stored")
    need(f.has("caption", "diary + your face"), "basis caption should say face was used")
    need(f.has("markdown", "Happiness score"), "happiness gauge not shown")
    # no face found: say so, fall back to the diary, never guess
    face.analyse_photo = lambda b, low=5.0, stressed=3.0: {"face_found": False, "happiness": None,
                                                           "probs": None, "mood_scores": None}
    take_photo(f)
    analyse(f, "I am so excited, we won the football match")
    need(f.has("warning", "couldn't see a face"), "no-face message missing")
    need(f.has("caption", "diary only"), "basis caption missing")
    need(f.session_state["result"]["mood"] == "Excited/Energized", "diary not used when no face")
    need("happiness" not in f.session_state, "stale happiness score kept")
    # retake flow
    take_photo(f)
    run(f, ["diary_retake"])
    need(f.cameras, "retake did not turn camera on")


def round5_swipe_points_streak():
    f = build_env()
    sign_up(f, "Hari", "hari@gmail.com")
    take_photo(f)
    analyse(f, "I stayed up late and I am so tired")
    need(f.session_state["result"]["mood"] == "Tired/Low Energy", "wrong mood")
    run(f, ["done0"]); run(f, ["skip1"]); run(f, ["done2"])
    need("🏁 Finish quest" in f.buttons, "finish button missing after 3 cards")
    run(f, ["🏁 Finish quest"])
    need(f.has("success", "+20"), "partial quest points wrong")
    need(f.has("metric", "Points=20"), "points not shown")
    need(f.has("metric", "Streak (days)=0"), "streak counted for partial quest")
    take_photo(f)
    analyse(f, "I am so excited, we won the football match")
    run(f, ["done0"]); run(f, ["done1"]); run(f, ["done2"]); run(f, ["🏁 Finish quest"])
    need(f.has("success", "+50") and f.has("balloons"), "full quest points/bonus wrong")
    need(f.has("metric", "Points=70") and f.has("metric", "Streak (days)=1"), "totals wrong")
    need(f.has("metric", "Quests done=1"), "quest count wrong")
    need(f.has("dataframe"), "history table missing")
    data = json.load(open("progress.json"))
    need(data["hari@gmail.com"]["points"] == 70, "progress not saved")
    # manual mood correction
    take_photo(f)
    analyse(f, "I am so excited, we won the football match")
    run(f, ["Update my quest"], {"My mood is:": "Calm/Happy"})
    need(f.session_state["result"]["mood"] == "Calm/Happy", "mood correction failed")
    need(f.session_state["cur_step"] == 0, "quest not reset after correction")


def round6_developer_mode():
    f = build_env(sortables=True)
    sign_up(f, "Hari", "hari@gmail.com")
    run(f, [], {"🛠️ Developer mode": True})
    for name in ["Look, points and layout", "Edit quests", "Face Lab"]:
        need(f.has("subheader", name), f"{name} tab missing")
    run(f, ["Save settings"], {"Color theme": "Ocean (blue)", "Points per step": 15,
                               "Require a camera photo with every diary entry": False})
    cfg = json.load(open("config.json"))
    need(cfg["palette"] == "Ocean (blue)" and cfg["points_per_step"] == 15, "settings not saved")
    need(f.has("success", "Saved"), "no saved message")
    need(cfg["section_order"][0] == "log", "drag order not applied")
    # custom quest
    run(f, ["Save my quest"], {"Mood": "Tired/Low Energy", "t_Tired/Low Energy": "My Tired Quest",
                               "s_Tired/Low Energy_0": "a", "s_Tired/Low Energy_1": "b",
                               "s_Tired/Low Energy_2": "c"})
    need(json.load(open("config.json"))["custom_quests"], "custom quest not saved")
    run(f, [], {"Diary entry": "I am so tired and sleepy today"})
    analyse(f, "I am so tired and sleepy today")
    need(f.session_state["quest"]["title"] == "My Tired Quest", "custom quest not used")
    need(f.session_state["quest"]["points_per_step"] == 15, "custom points not used")
    run(f, ["Back to built-in quests"])
    need(not json.load(open("config.json"))["custom_quests"], "custom quest not removed")
    # Face Lab capture + save
    run(f, ["lab_start"])
    run(f, [], camera=b"LABPHOTO")
    need(f.session_state.get("lab_bytes") == b"LABPHOTO", "lab photo not stored")
    need(not any(k and k.startswith("lab_cam") for k in f.cameras), "lab camera left on")
    run(f, ["Save this photo"], {"Which mood are you showing?": "Stressed/Overwhelmed",
                                 "Expression note (optional), e.g. sad, angry, confused": "angry"})
    files = [x for _, _, fs in os.walk("face_data") for x in fs]
    need(len(files) == 1 and files[0].endswith("angry.jpg"), f"lab photo not saved: {files}")
    need(f.has("caption", "Saved 1 photo"), "lab saved note missing")
    run(f, ["Train on my photos"])
    need(f.has("error"), "training should explain missing packages / data")
    run(f, ["Delete all saved photos"])
    need(not os.path.exists("face_data"), "photos not deleted")


def round7_edge_cases():
    f = build_env()
    sign_up(f, "Hari", "hari@gmail.com")
    run(f, ["Sign out"])
    run(f, ["Sign in"], {"Email": "hari@gmail.com", "Password": "nope"})
    need(f.has("error", "Wrong email"), "wrong password accepted")
    run(f, ["Sign in"], {"Email": "HARI@gmail.com", "Password": "password123"})
    need("user" in f.session_state, "login with different email case failed")
    run(f, ["Sign out"])
    sign_up(f, "Dup", "hari@gmail.com")
    need(f.has("error", "already"), "duplicate email allowed")
    sign_up(f, "Bad", "not-an-email")
    need(f.has("error", "valid email"), "bad email allowed")
    run(f, ["Create account"], {"su_email": "a@b.com", "su_pw": "short"})
    need(f.has("error", "8 characters"), "short password allowed")
    # broken config file must not crash the app
    open("config.json", "w").write("{ not json")
    run(f, ["Sign in"], {"Email": "hari@gmail.com", "Password": "password123"})
    need("user" in f.session_state, "app crashed on broken config")
    # unusual section order from an old config
    import settings
    cfg = settings.load()
    cfg["section_order"] = ["log", "bogus"]
    settings.save(cfg)
    run(f)
    need(f.has("subheader", "How was your day"), "layout broke with odd section order")
    # Google sign-in path
    g = build_env()
    g.secrets = {"auth": {}}
    g.user = types.SimpleNamespace(is_logged_in=True, get=lambda k, d="": {"email": "G@x.com", "name": "G"}.get(k, d))
    run(g)
    need(g.session_state.get("user", {}).get("email") == "g@x.com", "google sign-in failed")
    # first account via Google is developer, tools for choosing a developer
    import auth
    need(auth.set_developer("g@x.com") and auth.list_users()[0][1], "set_developer failed")
    need(not auth.set_developer("missing@x.com"), "set_developer accepted unknown email")


def round8_old_settings_file():
    f = build_env()
    import settings
    settings.load = lambda *a, **k: {"theme_color": "#2a9d8f", "require_photo": True}  # an old settings.py
    sign_up(f, "Hari", "hari@gmail.com")
    need(f.session_state["user"]["email"] == "hari@gmail.com" and f.has("metric", "Points"),
         "app crashed with an old settings file")


ROUNDS = [round1_sign_in_screen, round2_first_account_is_developer, round3_normal_user_has_no_settings,
          round4_camera_on_demand_and_diary, round5_swipe_points_streak, round6_developer_mode,
          round7_edge_cases, round8_old_settings_file]


if __name__ == "__main__":
    import traceback
    failures = 0
    for n, fn in enumerate(ROUNDS, 1):
        try:
            fn()
            print(f"Round {n} PASS  {fn.__name__}")
        except Exception as exc:
            failures += 1
            print(f"Round {n} FAIL  {fn.__name__}: {type(exc).__name__}: {exc}")
            traceback.print_exc(limit=4)
    sys.exit(1 if failures else 0)
