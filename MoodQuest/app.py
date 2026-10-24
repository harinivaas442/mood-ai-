import pandas as pd
import streamlit as st

import auth
import face
import progress
import settings
import ui
from mood_engine import classify, MOODS
from quests import make_quest, MOOD_STYLE, QUESTS

st.set_page_config(page_title="AI Mood Quest+", page_icon="🧭", layout="centered")
cfg = settings.load()
# If an older settings.py is still in the folder, fill in anything it does not know about.
for _k, _v in {"palette": "Forest (green)", "points_per_step": 10, "bonus": 20, "require_photo": True,
               "face_weight": 0.3, "happy_low_below": 5.0, "stressed_below": 3.0,
               "section_order": ["stats", "diary", "quest", "log"], "custom_quests": {}}.items():
    cfg.setdefault(_k, _v)

ui.inject(cfg["palette"])


# =====================================================================
# Sign in
# =====================================================================
def google_enabled():
    """Google sign-in only shows up if you added an [auth] block to .streamlit/secrets.toml."""
    try:
        return "auth" in st.secrets and hasattr(st, "login")
    except Exception:
        return False


def sign_in_screen():
    st.title("🧭 AI Mood Quest+")
    st.caption("Sign in to start your quests.")

    if google_enabled():
        try:
            if st.user.is_logged_in:
                st.session_state["user"] = auth.get_or_create_google_user(
                    st.user.get("email", ""), st.user.get("name", ""))
                st.rerun()
        except Exception:
            pass
        if st.button("Continue with Google", type="primary"):
            st.login()
        st.markdown("or use email and password:")

    tab_in, tab_new = st.tabs(["Sign in", "Create account"])
    with tab_in:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            go = st.form_submit_button("Sign in", type="primary")
        if go:
            ok, msg, user = auth.login(email, password)
            if ok:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error(msg)
    with tab_new:
        with st.form("signup_form"):
            name = st.text_input("Your name")
            email = st.text_input("Email", key="su_email")
            password = st.text_input("Password (8+ characters)", type="password", key="su_pw")
            go = st.form_submit_button("Create account", type="primary")
        if go:
            ok, msg, user = auth.register(email, password, name)
            if ok:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error(msg)
        st.caption("The first account created on this computer becomes the developer account.")


if "user" not in st.session_state:
    sign_in_screen()
    st.stop()

user = st.session_state["user"]
student_key = user["email"]

# =====================================================================
# Sidebar
# =====================================================================
with st.sidebar:
    st.write(f"Signed in as **{user['name']}**")
    dev_mode = False
    use_hf_text = False
    if user["is_dev"]:  # settings and customization are for the developer account only
        dev_mode = st.toggle("🛠️ Developer mode")
        use_hf_text = st.checkbox("Use Hugging Face text model (needs `transformers`)", value=False)
    if st.button("Sign out"):
        try:
            if google_enabled() and st.user.is_logged_in:
                st.logout()
        except Exception:
            pass
        st.session_state.clear()
        st.rerun()

data = progress.load()
student = progress.get_student(data, student_key)


# =====================================================================
# Main sections (their order is set in Developer mode)
# =====================================================================
def reset_quest_state():
    st.session_state["done_flag"] = False
    st.session_state["cur_step"] = 0
    st.session_state["done_count"] = 0


def section_stats():
    c1, c2, c3 = st.columns(3)
    c1.metric("⭐ Points", student["points"])
    c2.metric("🔥 Streak (days)", progress.current_streak(student))
    c3.metric("✅ Quests done", sum(1 for h in student["history"] if h["completed"]))


def camera_capture(prefix, label="Take a photo"):
    """The camera runs ONLY while you are taking the photo. Returns photo bytes or None."""
    bytes_key, on_key, n_key = f"{prefix}_bytes", f"{prefix}_on", f"{prefix}_n"
    if st.session_state.get(bytes_key):
        st.image(st.session_state[bytes_key], width=220, caption="Photo taken. The camera is off.")
        if st.button("Retake photo", key=f"{prefix}_retake"):
            st.session_state[bytes_key] = None
            st.session_state[on_key] = True
            st.session_state[n_key] = st.session_state.get(n_key, 0) + 1
            st.rerun()
        return st.session_state[bytes_key]
    if st.session_state.get(on_key):
        shot = st.camera_input(label, key=f"{prefix}_cam_{st.session_state.get(n_key, 0)}")
        if shot is not None:
            st.session_state[bytes_key] = shot.getvalue()
            st.session_state[on_key] = False  # next run the camera widget is gone = camera off
            st.rerun()
        if st.button("Cancel", key=f"{prefix}_cancel"):
            st.session_state[on_key] = False
            st.rerun()
        return None
    if st.button("📷 Turn on camera", key=f"{prefix}_start"):
        st.session_state[on_key] = True
        st.rerun()
    st.caption("The camera only turns on when you press this, and turns off after the photo.")
    return None


def section_diary():
    st.subheader("📝 How was your day so far?")
    entry = st.text_area("Diary entry", height=120, max_chars=500, label_visibility="collapsed",
                         placeholder="e.g. I have a math test tomorrow and I can't stop worrying...")

    photo = None
    needs_photo = cfg["require_photo"]
    if needs_photo or st.checkbox("Add a photo of my face (optional)"):
        st.write("📷 Your photo is only used to read your expression. It is not saved.")
        if face.is_available():
            st.caption("Face reading: ON" + ("" if face.status()["face_crop"] else
                                             " (add opencv-python for better accuracy)"))
        else:
            st.caption("Face reading: OFF, missing " + ", ".join(face.missing()) +
                       ". The photo will not change your result. Run Install Face Features.bat.")
        photo = camera_capture("diary")

    if st.button("Find my mood & start quest", type="primary"):
        if len(entry.strip()) < 5:
            st.warning("Please write a little more (at least a few words).")
        elif needs_photo and photo is None:
            st.warning("Please turn on the camera and take a photo first.")
        else:
            result = classify(entry, use_hf=use_hf_text)
            for k in ("scan", "face_match", "happiness", "expressions", "face_note"):
                st.session_state.pop(k, None)
            st.session_state["used_face"] = False
            if photo is not None:
                st.session_state["scan"] = face.draw_dots(photo)
                if not face.is_available():
                    st.session_state["face_note"] = (
                        "Face reading is OFF (missing: " + ", ".join(face.missing()) + "), so only your diary "
                        "was used. Double-click Install Face Features.bat, then restart the app.")
                else:
                    try:
                        with st.spinner("Reading your expression (the first time downloads the model)..."):
                            info = face.analyse_photo(photo, cfg["happy_low_below"], cfg["stressed_below"])
                        if not info["face_found"]:
                            st.session_state["face_note"] = ("I couldn't see a face clearly, so I used your diary "
                                                             "only. Move closer, face the light, and retake the photo.")
                        else:
                            result = face.blend(result, info["mood_scores"], cfg["face_weight"])
                            total = sum(info["mood_scores"].values()) or 1.0
                            st.session_state["face_match"] = info["mood_scores"].get(result["mood"], 0) / total
                            st.session_state["happiness"] = info["happiness"]
                            st.session_state["expressions"] = info["probs"]
                            st.session_state["used_face"] = True
                    except Exception as exc:
                        st.session_state["face_note"] = (f"Could not read the photo ({type(exc).__name__}: {exc}). "
                                                         "Used your diary only.")
            st.session_state["diary_bytes"] = None  # forget the photo after use
            st.session_state["result"] = result
            st.session_state["entry_text"] = entry
            st.session_state["quest"] = make_quest(
                result["mood"], entry, cfg["custom_quests"].get(result["mood"]),
                cfg["points_per_step"], cfg["bonus"])
            reset_quest_state()


def section_quest():
    if "result" not in st.session_state:
        return
    result, quest = st.session_state["result"], st.session_state["quest"]
    entry = st.session_state.get("entry_text", "")
    style = MOOD_STYLE[result["mood"]]
    st.subheader(f"{style['emoji']} Mood: {result['mood']}")
    st.progress(result["confidence"], text=f"Confidence: {int(result['confidence'] * 100)}%")
    if result["note"]:
        st.info(result["note"])

    with st.expander("Not quite right? Pick your mood yourself"):
        choice = st.radio("My mood is:", MOODS, index=MOODS.index(result["mood"]))
        if choice != result["mood"] and st.button("Update my quest"):
            st.session_state["result"] = {**result, "mood": choice, "confidence": 1.0,
                                          "note": "Mood chosen by you."}
            st.session_state["quest"] = make_quest(
                choice, entry, cfg["custom_quests"].get(choice),
                cfg["points_per_step"], cfg["bonus"])
            reset_quest_state()
            st.rerun()

    st.caption("Mood based on: " + ("your diary + your face" if st.session_state.get("used_face")
                                    else "your diary only"))
    if st.session_state.get("face_note"):
        st.warning(st.session_state["face_note"])
    if st.session_state.get("happiness") is not None:
        ui.gauge(st.session_state["happiness"], cfg["happy_low_below"], cfg["stressed_below"])
        with st.expander("What the camera saw"):
            for name, prob in sorted(st.session_state.get("expressions", {}).items(), key=lambda x: -x[1]):
                st.progress(min(1.0, max(0.0, prob)), text=f"{name}: {int(prob * 100)}%")
    if st.session_state.get("scan") is not None:
        st.image(st.session_state["scan"], caption="Scan view (decorative dots)", width=260)
    if "face_match" in st.session_state:
        st.metric("Face match with this mood", f"{int(st.session_state['face_match'] * 100)}%")

    st.markdown(f"### 🗺️ {quest['title']}")
    cur = st.session_state.get("cur_step", 0)
    done = st.session_state.get("done_count", 0)
    finished = st.session_state.get("done_flag", False)
    st.progress(min(cur, 3) / 3, text=f"Card {min(cur + 1, 3)} of 3  ·  {done} done")

    if cur < 3 and not finished:
        ui.step_card(f"Step {cur + 1}", quest["steps"][cur], st.session_state.get("last_dir", "right"))
        ui.swipe_script()
        st.caption("Swipe the card, use ← → keys, or press the buttons.")
        c1, c2 = st.columns(2)
        if c1.button("⏭️ Skip", key=f"skip{cur}"):
            st.session_state["cur_step"] = cur + 1
            st.session_state["last_dir"] = "left"
            st.rerun()
        if c2.button("✅ Done", key=f"done{cur}", type="primary"):
            st.session_state["cur_step"] = cur + 1
            st.session_state["done_count"] = done + 1
            st.session_state["last_dir"] = "right"
            st.rerun()
    elif not finished:
        st.write(f"All cards swiped. You completed {done} of 3 steps.")
        if st.button("🏁 Finish quest", type="primary"):
            earned = progress.complete_quest(data, student_key, result["mood"], quest["title"],
                                             done, quest["points_per_step"], quest["bonus"])
            progress.save(data)
            st.session_state["done_flag"] = True
            st.session_state["earned"] = (earned, done == 3)
            st.rerun()
    else:
        earned, full = st.session_state["earned"]
        if full:
            st.success(f"Quest complete! +{earned} points (includes +{quest['bonus']} bonus). Streak updated 🔥")
            st.balloons()
        else:
            st.success(f"Nice effort! +{earned} points. Finish all 3 steps next time for the bonus and streak.")


def section_log():
    st.subheader("📈 My quest log")
    if student["history"]:
        df = pd.DataFrame(student["history"])
        st.dataframe(df[["time", "mood", "quest", "steps_done", "points"]], hide_index=True)
        st.bar_chart(df["mood"].value_counts())
    else:
        st.write("No quests yet. Write your first entry above!")


SECTION_FUNCS = {"stats": section_stats, "diary": section_diary,
                 "quest": section_quest, "log": section_log}


def render_app():
    st.title("🧭 AI Mood Quest+")
    ui.quote_banner()
    for key in cfg["section_order"]:
        with st.container(border=True):
            SECTION_FUNCS[key]()


# =====================================================================
# Developer mode
# =====================================================================
def dev_customize():
    st.subheader("Look, points and layout")
    palette = st.selectbox("Color theme", list(ui.PALETTES), index=list(ui.PALETTES).index(cfg["palette"]) if cfg["palette"] in ui.PALETTES else 0)
    c1, c2 = st.columns(2)
    pps = c1.number_input("Points per step", 1, 100, int(cfg["points_per_step"]))
    bonus = c2.number_input("Bonus for finishing all 3 steps", 0, 200, int(cfg["bonus"]))
    req = st.checkbox("Require a camera photo with every diary entry", value=cfg["require_photo"])
    fw = st.slider("How much the face counts vs. the diary text", 0.0, 0.8, float(cfg["face_weight"]), 0.05)
    c3, c4 = st.columns(2)
    low = c3.number_input("Happiness score below this = sad / low energy", 1.0, 9.0, float(cfg["happy_low_below"]), 0.5)
    stress = c4.number_input("Happiness score below this = stressed / overwhelmed", 0.5, 8.0,
                             float(cfg["stressed_below"]), 0.5)

    st.markdown("**Page layout:** drag the blocks to reorder the page.")
    labels = [settings.SECTIONS[k] for k in cfg["section_order"]]
    try:
        from streamlit_sortables import sort_items
        new_labels = sort_items(labels)
    except ImportError:
        st.caption("Drag and drop needs one extra install: `python -m pip install streamlit-sortables`. "
                   "Until then, pick the order below.")
        new_labels = st.multiselect("Order (first = top)", list(settings.SECTIONS.values()),
                                    default=labels)
        for lab in settings.SECTIONS.values():
            if lab not in new_labels:
                new_labels.append(lab)
    inv = {v: k for k, v in settings.SECTIONS.items()}

    if st.button("Save settings", type="primary"):
        cfg.update({"palette": palette, "points_per_step": int(pps), "bonus": int(bonus),
                    "require_photo": req, "face_weight": float(fw),
                    "happy_low_below": float(low), "stressed_below": float(min(stress, low)),
                    "section_order": [inv[l] for l in new_labels if l in inv]})
        settings.save(cfg)
        st.session_state["saved_msg"] = True
        st.rerun()
    if st.session_state.pop("saved_msg", False):
        st.success("Saved! Switch Developer mode off to see the result.")


def dev_quests():
    st.subheader("Edit quests")
    st.caption("Write your own quest for a mood. It replaces the built-in quests for that mood. "
               "Use {topic} in a step to insert a word from the diary (e.g. math).")
    mood = st.selectbox("Mood", MOODS)
    current = (cfg["custom_quests"].get(mood) or QUESTS[mood])[0]
    title = st.text_input("Quest title", current["title"], key=f"t_{mood}")
    steps = [st.text_area(f"Step {i + 1}", current["steps"][i], key=f"s_{mood}_{i}", height=70)
             for i in range(3)]
    c1, c2 = st.columns(2)
    if c1.button("Save my quest"):
        cfg["custom_quests"][mood] = [{"title": title, "steps": steps}]
        settings.save(cfg)
        st.success("Quest saved.")
    if c2.button("Back to built-in quests"):
        cfg["custom_quests"].pop(mood, None)
        settings.save(cfg)
        for k in [f"t_{mood}"] + [f"s_{mood}_{i}" for i in range(3)]:
            st.session_state.pop(k, None)  # so the boxes show the built-in text again
        st.rerun()


def dev_face_lab():
    st.subheader("Face Lab")
    st.info(
        "Save photos of your face showing different moods, then press Train. "
        "The app already uses a pretrained expression model that learned from thousands of "
        "different faces, and that is what lets it work for strangers. Your photos tune how "
        "expressions map to the 4 moods for YOUR face. They cannot make the app understand "
        "everyone, because photos of one person are not enough for that. "
        "Photos stay in the `face_data` folder on this computer. Only photograph people who agree "
        "to it (and get a parent's permission for under-18s).")
    if not face.is_available():
        st.warning("The face model is not installed yet. Run: "
                   "`python -m pip install transformers torch pillow scikit-learn`")

    mood = st.selectbox("Which mood are you showing?", MOODS)
    note = st.text_input("Expression note (optional), e.g. sad, angry, confused")
    shot = camera_capture("lab")
    if shot is not None and st.button("Save this photo", type="primary"):
        face.save_sample(mood, shot, note)
        st.session_state["lab_bytes"] = None
        st.session_state["lab_saved"] = st.session_state.get("lab_saved", 0) + 1
        st.rerun()
    if st.session_state.get("lab_saved"):
        st.caption(f"Saved {st.session_state['lab_saved']} photo(s) this session.")

    counts = face.count_samples()
    st.write("**Saved photos per mood** (aim for 10+ each, with different lighting and angles):")
    st.dataframe(pd.DataFrame({"Mood": list(counts), "Photos": list(counts.values())}),
                 hide_index=True)
    st.write(f"Calibration trained: **{'yes' if face.has_calibration() else 'no'}**")
    c1, c2 = st.columns(2)
    if c1.button("Train on my photos"):
        with st.spinner("Training..."):
            ok, msg = face.train()
        (st.success if ok else st.error)(msg)
    if c2.button("Delete all saved photos"):
        face.delete_all_samples()
        st.rerun()


if dev_mode and user["is_dev"]:
    t_app, t_custom, t_quests, t_face = st.tabs(["App", "Customize", "Quests", "Face Lab"])
    with t_app:
        render_app()
    with t_custom:
        dev_customize()
    with t_quests:
        dev_quests()
    with t_face:
        dev_face_lab()
else:
    render_app()
