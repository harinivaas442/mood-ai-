"""Mood classifier for short student diary entries.

Offline, dependency-free scoring engine with:
  * weighted word / phrase lexicon for four moods
  * negation handling ("not tired", "never stressed")
  * contrast handling ("exhausted BUT so excited" -> the later clause counts more)
  * intensifiers ("so", "really", "super") and softeners ("a bit", "slightly")
  * optional Hugging Face zero-shot model (use_hf=True) if `transformers` is installed
"""
import re

STRESSED = "Stressed/Overwhelmed"
TIRED = "Tired/Low Energy"
EXCITED = "Excited/Energized"
CALM = "Calm/Happy"
MOODS = [STRESSED, TIRED, EXCITED, CALM]

# (term, weight). Multi-word phrases are matched on the lowercase text.
LEXICON = {
    STRESSED: {
        "stressed": 3, "stress": 2, "stressful": 3, "overwhelmed": 3, "overwhelming": 3,
        "anxious": 3, "anxiety": 3, "nervous": 2, "worried": 2, "worry": 2, "panic": 3,
        "panicking": 3, "pressure": 2, "deadline": 2, "deadlines": 2, "exam": 1.5,
        "exams": 1.5, "pop quiz": 2.5, "quiz": 1, "test": 1, "behind": 1.5,
        "swamped": 3, "freaking out": 3, "freaked out": 3, "too much": 2,
        "can't breathe": 3, "cant breathe": 3, "can't cope": 3, "so much homework": 2.5,
        "piled up": 2, "scared": 2, "afraid": 2, "tense": 2, "falling apart": 3,
        "no time": 2, "running out of time": 3, "due tomorrow": 2.5, "due": 1,
        "homework": 1, "so much to do": 2.5, "ugh": 1, "failing": 1.5, "presentation": 1.5, "argument": 1.5, "fight": 1.5, "failed": 1.5,
    },
    TIRED: {
        "tired": 3, "exhausted": 3, "sleepy": 3, "drained": 3, "yawn": 2, "yawning": 2,
        "yawned": 2, "low energy": 3, "no energy": 3, "worn out": 3, "burnt out": 3,
        "burned out": 3, "fatigue": 3, "fatigued": 3, "slept badly": 3, "barely slept": 3,
        "stayed up": 2, "up late": 2, "bored": 2, "boring": 1.5, "drag": 1.5,
        "dragging": 2, "heavy eyes": 3, "eyes closing": 3, "need a nap": 3, "nap": 1.5,
        "lazy": 2, "sluggish": 3, "zombie": 2.5, "meh": 1.5, "slow day": 2,
        "can't keep my eyes open": 3, "fried": 2.5, "no sleep": 3, "brain fog": 3, "long day": 1.5,
    },
    EXCITED: {
        "excited": 3, "exciting": 2.5, "thrilled": 3, "can't wait": 3, "cant wait": 3,
        "amazing": 2.5, "awesome": 2.5, "pumped": 3, "hyped": 3, "energized": 3,
        "energetic": 3, "won": 2, "winning": 2, "great news": 3, "fantastic": 2.5,
        "yay": 2.5, "stoked": 3, "buzzing": 3, "field trip": 2, "tournament": 2,
        "match": 1, "party": 1.5, "celebrate": 2, "celebrating": 2, "birthday": 1.5,
        "can't stop smiling": 3, "bouncing": 2.5, "fun": 1.5, "best day": 3,
        "so ready": 2, "adventure": 2, "performance": 1, "got the part": 3,
    },
    CALM: {
        "calm": 3, "peaceful": 3, "relaxed": 3, "relaxing": 2.5, "content": 2.5,
        "happy": 2.5, "grateful": 2.5, "thankful": 2.5, "cozy": 2, "at ease": 3,
        "chill": 2.5, "chilled": 2.5, "fine": 1.5, "good": 1.5, "nice": 1.5,
        "quiet": 2, "smooth": 2, "gentle": 2, "serene": 3, "comfortable": 2,
        "laughed": 1.5, "lovely": 2, "okay": 1, "ok": 1, "steady": 2,
        "sunshine": 1.5, "reading": 1, "walked": 1, "peace": 2.5, "balanced": 2.5,
        "enjoyed": 2, "enjoying": 2, "relief": 2.5, "relieved": 2.5,
    },
}

NEGATORS = {"not", "no", "never", "n't", "without", "hardly", "barely_neg", "isnt", "wasnt",
            "dont", "didnt", "cant", "wont", "arent", "am_not"}
INTENSIFIERS = {"so", "really", "very", "super", "extremely", "totally", "incredibly",
                "completely", "absolutely", "too", "quite"}
SOFTENERS = {"slightly", "little", "bit", "kinda", "somewhat", "mildly", "sorta"}
CONTRAST = {"but", "however", "although", "though", "yet", "except"}

# When a mood word is negated, which mood gets a small boost instead?
NEGATION_SHIFT = {
    STRESSED: CALM,
    TIRED: EXCITED,
    EXCITED: TIRED,
    CALM: STRESSED,
}


def _normalise(text):
    t = text.lower().replace("\u2019", "'")
    t = re.sub(r"(\w)n't\b", r"\1 not", t)       # isn't -> is not, can't -> ca not
    t = t.replace("ca not", "can't").replace("wo not", "will not")
    t = re.sub(r"[^a-z' ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _terms_sorted():
    items = []
    for mood, words in LEXICON.items():
        for term, w in words.items():
            norm = _normalise(term)
            items.append((norm, mood, w))
    # longest phrase first so "pop quiz" wins over "quiz"
    items.sort(key=lambda x: -len(x[0].split()))
    return items


_TERMS = _terms_sorted()


def _score_clause(clause):
    """Return {mood: score} for one clause."""
    tokens = clause.split()
    scores = {m: 0.0 for m in MOODS}
    used = set()
    for term, mood, weight in _TERMS:
        parts = term.split()
        n = len(parts)
        for i in range(len(tokens) - n + 1):
            if any(j in used for j in range(i, i + n)):
                continue
            if tokens[i:i + n] != parts:
                continue
            used.update(range(i, i + n))
            window = tokens[max(0, i - 3):i]
            mult = 1.0
            if any(w in INTENSIFIERS for w in window):
                mult = 1.4
            if any(w in SOFTENERS for w in window):
                mult = 0.6
            if any(w in NEGATORS for w in window):
                scores[NEGATION_SHIFT[mood]] += weight * 0.6
            else:
                scores[mood] += weight * mult
    return scores


def classify(text, use_hf=False):
    """Classify a diary entry.

    Returns dict: mood, confidence (0-1), scores (per mood), note (str).
    """
    if not text or not text.strip():
        return {"mood": CALM, "confidence": 0.0, "scores": {m: 0 for m in MOODS},
                "note": "Empty entry."}

    if use_hf:
        try:
            return _classify_hf(text)
        except Exception as exc:  # fall back quietly
            fallback = classify(text, use_hf=False)
            fallback["note"] = f"HF model unavailable ({type(exc).__name__}); used offline engine."
            return fallback

    norm = _normalise(text)
    # Split on contrast words; the last clause is what the student is feeling "now".
    clauses, current = [], []
    for tok in norm.split():
        if tok in CONTRAST:
            clauses.append(" ".join(current))
            current = []
        else:
            current.append(tok)
    clauses.append(" ".join(current))
    clauses = [c for c in clauses if c]

    total = {m: 0.0 for m in MOODS}
    for idx, clause in enumerate(clauses):
        weight = 1.0 if idx < len(clauses) - 1 or len(clauses) == 1 else 1.6
        for m, s in _score_clause(clause).items():
            total[m] += s * weight

    ranked = sorted(total.items(), key=lambda x: -x[1])
    top, second = ranked[0], ranked[1]
    if top[1] == 0:
        return {"mood": CALM, "confidence": 0.2, "scores": total,
                "note": "No strong mood words found, so we guessed Calm/Happy. Tell us more!"}

    confidence = min(0.99, 0.4 + 0.6 * (top[1] - second[1]) / (top[1] + 1e-9))
    note = ""
    if second[1] > 0 and (top[1] - second[1]) < 1.5:
        note = f"Mixed feelings: also a hint of {second[0]}."
    return {"mood": top[0], "confidence": round(confidence, 2), "scores": total, "note": note}


_hf_pipe = None


def _classify_hf(text):
    global _hf_pipe
    if _hf_pipe is None:
        from transformers import pipeline
        _hf_pipe = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    labels = {
        STRESSED: "stressed or overwhelmed",
        TIRED: "tired or low energy",
        EXCITED: "excited or energized",
        CALM: "calm or happy",
    }
    out = _hf_pipe(text, list(labels.values()))
    inv = {v: k for k, v in labels.items()}
    scores = {inv[l]: s for l, s in zip(out["labels"], out["scores"])}
    top = max(scores, key=scores.get)
    return {"mood": top, "confidence": round(scores[top], 2), "scores": scores,
            "note": "Classified with Hugging Face zero-shot model."}
