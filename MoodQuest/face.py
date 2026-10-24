"""Face-expression helper (optional). Everything stays on your own computer.

How it works
  1. The app finds your face in the photo and crops it (needs opencv). Expression models are
     trained on tightly cropped faces, so reading the whole webcam frame gives poor results.
  2. A pretrained expression model (Hugging Face `trpakov/vit-face-expression`, trained on
     thousands of different faces) reads the crop (and its mirror image) and gives 7
     expression probabilities. This is what lets the app work for strangers.
  3. Those probabilities become a HAPPINESS SCORE from 0 to 10:
        10 x ( happy 1.0 + surprise 0.6 + neutral 0.5 + sad 0.1 + fear 0.1 )
     so a clear smile is near 10, a neutral face is about 5 and an angry or upset face is near 0.
  4. The score maps to a mood (limits can be changed in Developer mode):
        below 3  -> Stressed/Overwhelmed
        3 to 5   -> Tired/Low Energy (sad / low)
        5 and up -> Calm/Happy (Excited if you look surprised)
  5. In Face Lab you can save photos of yourself labelled with a mood and press Train. That fits
     a small calibration model on top, so the mapping matches how YOUR face shows moods.

Needs (optional): pip install transformers torch pillow scikit-learn opencv-python
If they are missing, the app still works using the diary text only.
"""
import io
import os
import pickle
import re
import time

from mood_engine import STRESSED, TIRED, EXCITED, CALM, MOODS

FACE_DIR = "face_data"
MODEL_NAME = "trpakov/vit-face-expression"
EXPRESSIONS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
SYNONYMS = {"anger": "angry", "happiness": "happy", "joy": "happy", "sadness": "sad",
            "surprised": "surprise", "fearful": "fear", "disgusted": "disgust", "calm": "neutral"}
HAPPY_WEIGHTS = {"happy": 1.0, "surprise": 0.6, "neutral": 0.5, "sad": 0.1,
                 "fear": 0.1, "angry": 0.0, "disgust": 0.0}

_pipe = None


def _has(module):
    import importlib.util
    try:
        return importlib.util.find_spec(module) is not None
    except Exception:
        return False


def missing():
    """Names of packages (to pip install) that the face model still needs."""
    need = {"transformers": "transformers", "torch": "torch", "PIL": "pillow"}
    return [pip for mod, pip in need.items() if not _has(mod)]


def is_available():
    """True if everything the pretrained face model needs is installed."""
    return not missing()


def status():
    """What works right now, for the status line and check_face.py."""
    return {"model": is_available(), "face_crop": _has("cv2"),
            "dots": _has("mediapipe") or _has("cv2"), "calibration": has_calibration()}


def _get_pipe():
    global _pipe
    if _pipe is None:
        from transformers import pipeline
        _pipe = pipeline("image-classification", model=MODEL_NAME, top_k=None)
    return _pipe


# ---------------------------------------------------------------- reading a photo

def _crop_face(img):
    """Return (cropped_image, status). status: True = face found, False = no face,
    None = opencv missing (the whole photo is used)."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return img, None
    try:
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    except Exception:  # broken / incomplete opencv install: use the whole photo instead
        return img, None
    if len(faces) == 0:
        return None, False
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    pad = int(0.15 * w)
    box = (max(0, x - pad), max(0, y - pad), min(img.width, x + w + pad), min(img.height, y + h + pad))
    return img.crop(box), True


def _model_probs(img):
    out = _get_pipe()(img)
    probs = {e: 0.0 for e in EXPRESSIONS}
    for item in out:
        label = item["label"].lower()
        label = SYNONYMS.get(label, label)
        if label in probs:
            probs[label] += float(item["score"])
    total = sum(probs.values())
    if total < 0.5:  # never silently return zeros (that used to look like "Stressed")
        raise ValueError("unexpected model labels: " + ", ".join(i["label"] for i in out))
    return {k: v / total for k, v in probs.items()}


def expression_probs(image_bytes):
    """Return (probs, face_found). probs is None when no face was found."""
    from PIL import Image, ImageOps
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    crop, status = _crop_face(img)
    if status is False:
        return None, False
    p1 = _model_probs(crop)
    p2 = _model_probs(ImageOps.mirror(crop))  # average with the mirror image for stability
    return {e: (p1[e] + p2[e]) / 2 for e in EXPRESSIONS}, True


def happiness_score(probs):
    """0 to 10, rounded to one decimal."""
    return round(10 * sum(probs[e] * HAPPY_WEIGHTS[e] for e in EXPRESSIONS), 1)


def happiness_to_moods(score, probs=None, low=5.0, stressed=3.0):
    """Turn the happiness score into mood scores that add up to 1."""
    scores = {m: 0.05 for m in MOODS}
    if score < stressed:
        scores[STRESSED] = 0.8
    elif score < low:
        scores[TIRED] = 0.8
    elif probs and probs.get("surprise", 0) > 0.4:
        scores[EXCITED], scores[CALM] = 0.6, 0.3
    else:
        scores[CALM] = 0.8
    total = sum(scores.values())
    return {m: v / total for m, v in scores.items()}


def analyse_photo(image_bytes, low=5.0, stressed=3.0):
    """Main entry point for the app. Returns a dict:
    face_found, happiness (0-10), probs (expressions), mood_scores (4 moods)."""
    probs, found = expression_probs(image_bytes)
    if not found:
        return {"face_found": False, "happiness": None, "probs": None, "mood_scores": None}
    score = happiness_score(probs)
    return {"face_found": True, "happiness": score, "probs": probs,
            "mood_scores": probs_to_moods(probs, low, stressed)}


def probs_to_moods(probs, low=5.0, stressed=3.0):
    """Mood scores from expression probabilities: your trained calibration if it exists,
    otherwise the happiness-score rules."""
    if has_calibration():
        try:
            with open(_calibration_path(), "rb") as f:
                clf = pickle.load(f)
            p = clf.predict_proba([[probs[e] for e in EXPRESSIONS]])[0]
            scores = {m: 0.0 for m in MOODS}
            for cls, val in zip(clf.classes_, p):
                scores[cls] = float(val)
            return scores
        except Exception:
            pass
    return happiness_to_moods(happiness_score(probs), probs, low, stressed)


def blend(text_result, face_scores, weight=0.3):
    """Combine the diary result with face scores. Returns a result dict like classify()."""
    ftotal = sum(face_scores.values()) if face_scores else 0
    if not face_scores or ftotal <= 0:
        return text_result  # no usable face signal: never guess
    tscores = text_result.get("scores", {})
    ttotal = sum(tscores.get(m, 0) for m in MOODS)
    fp = {m: face_scores.get(m, 0) / ftotal for m in MOODS}
    if ttotal <= 0:
        final = fp  # diary had no mood words: rely on the face
    else:
        tp = {m: tscores.get(m, 0) / ttotal for m in MOODS}
        final = {m: (1 - weight) * tp[m] + weight * fp[m] for m in MOODS}
    ranked = sorted(final.items(), key=lambda x: -x[1])
    mood = ranked[0][0]
    face_top = max(fp, key=fp.get)
    text_top = max(MOODS, key=lambda m: tscores.get(m, 0)) if ttotal > 0 else None
    if text_top is None:
        note = f"Diary had no clear mood words, so your face decided ({face_top})."
    elif text_top == face_top:
        note = "Your diary and your face agree."
    else:
        note = f"Diary says {text_top}, face says {face_top}. We blended them."
    conf = min(0.99, 0.4 + 0.6 * (ranked[0][1] - ranked[1][1]) / (ranked[0][1] + 1e-9))
    return {"mood": mood, "confidence": round(conf, 2), "scores": final, "note": note}


def _dots_mediapipe(image_bytes):
    try:
        import mediapipe as mp
        import numpy as np
        from PIL import Image, ImageDraw
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1)
        res = mesh.process(np.array(img))
        mesh.close()
        if not res.multi_face_landmarks:
            return None
        draw = ImageDraw.Draw(img)
        w, h = img.size
        for lm in res.multi_face_landmarks[0].landmark:
            x, y = lm.x * w, lm.y * h
            draw.ellipse((x - 1.6, y - 1.6, x + 1.6, y + 1.6), fill=(130, 255, 180))
        return img
    except Exception:
        return None


def _dots_opencv(image_bytes):
    """Decorative scan view using only OpenCV: a dot grid over the face, rings on the eyes
    and a ring on the smile if one is detected. Not real facial landmarks."""
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageDraw
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        base = cv2.data.haarcascades
        faces = cv2.CascadeClassifier(base + "haarcascade_frontalface_default.xml").detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(faces) == 0:
            return None
        x, y, w, h = [int(v) for v in max(faces, key=lambda f: f[2] * f[3])]
        draw = ImageDraw.Draw(img)
        cx, cy, step = x + w / 2, y + h / 2, max(8, w // 16)
        for gy in range(y, y + h, step):
            for gx in range(x, x + w, step):
                if ((gx - cx) / (w / 2)) ** 2 + ((gy - cy) / (h / 2)) ** 2 <= 1:
                    draw.ellipse((gx - 1.5, gy - 1.5, gx + 1.5, gy + 1.5), fill=(130, 255, 180))
        roi = gray[y:y + h, x:x + w]
        for (ex, ey, ew, eh) in cv2.CascadeClassifier(base + "haarcascade_eye.xml").detectMultiScale(
                roi[: h // 2], 1.1, 5):
            px, py, r = x + ex + ew / 2, y + ey + eh / 2, max(ew, eh) / 2
            draw.ellipse((px - r, py - r, px + r, py + r), outline=(255, 255, 255), width=2)
        for (sx, sy, sw, sh) in cv2.CascadeClassifier(base + "haarcascade_smile.xml").detectMultiScale(
                roi[h // 2:], 1.7, 20)[:1]:
            px, py = x + sx + sw / 2, y + h // 2 + sy + sh / 2
            draw.ellipse((px - sw / 2, py - sh / 2, px + sw / 2, py + sh / 2), outline=(255, 220, 120), width=2)
        return img
    except Exception:
        return None


def draw_dots(image_bytes):
    """Photo with scan dots drawn on it, or None if no face / needed package is missing.
    Uses mediapipe landmarks if available, otherwise the OpenCV scan view."""
    return _dots_mediapipe(image_bytes) or _dots_opencv(image_bytes)


# ---------------- Face Lab: saving and training on your own photos ----------------

def _calibration_path():
    return os.path.join(FACE_DIR, "calibration.pkl")


def has_calibration():
    return os.path.exists(_calibration_path())


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "photo"


def mood_folder(mood):
    return os.path.join(FACE_DIR, _slug(mood))


def save_sample(mood, image_bytes, note=""):
    folder = mood_folder(mood)
    os.makedirs(folder, exist_ok=True)
    name = f"{int(time.time() * 1000)}_{_slug(note)}.jpg"
    with open(os.path.join(folder, name), "wb") as f:
        f.write(image_bytes)
    return name


def count_samples():
    counts = {}
    for m in MOODS:
        folder = mood_folder(m)
        counts[m] = len([f for f in os.listdir(folder) if f.endswith(".jpg")]) if os.path.isdir(folder) else 0
    return counts


def delete_all_samples():
    import shutil
    if os.path.isdir(FACE_DIR):
        shutil.rmtree(FACE_DIR)


def train(min_per_mood=3):
    """Fit the calibration model on saved photos. Returns (ok, message)."""
    try:
        from sklearn.linear_model import LogisticRegression
    except ImportError:
        return False, "scikit-learn is not installed. Run: pip install scikit-learn"
    if not is_available():
        return False, "transformers/torch/pillow are not installed. See the README."
    X, y, skipped = [], [], 0
    for mood in MOODS:
        folder = mood_folder(mood)
        if not os.path.isdir(folder):
            continue
        files = [f for f in os.listdir(folder) if f.endswith(".jpg")]
        if len(files) < min_per_mood:
            continue
        for fn in files:
            with open(os.path.join(folder, fn), "rb") as f:
                probs, found = expression_probs(f.read())
            if not found:
                skipped += 1
                continue
            X.append([probs[e] for e in EXPRESSIONS])
            y.append(mood)
    if len(set(y)) < 2:
        return False, f"Save at least {min_per_mood} clear face photos for at least 2 different moods first."
    clf = LogisticRegression(max_iter=1000).fit(X, y)
    os.makedirs(FACE_DIR, exist_ok=True)
    with open(_calibration_path(), "wb") as f:
        pickle.dump(clf, f)
    extra = f" ({skipped} photos skipped: no face found)" if skipped else ""
    return True, f"Trained on {len(y)} photos across {len(set(y))} moods.{extra}"
