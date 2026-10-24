"""Look and feel: color palettes, quotes, glow, swipe cards and the happiness gauge."""
import datetime
import html
import json

import streamlit as st
import streamlit.components.v1 as components

PALETTES = {
    "Forest (green)": {"main": "#2d6a4f", "accent": "#95d5b2", "bg": "#0f1f17", "card": "#1b3a2b", "text": "#e9f5ee"},
    "Ocean (blue)":   {"main": "#1d6fa5", "accent": "#90cdf4", "bg": "#0b1b2b", "card": "#14324d", "text": "#e8f3fb"},
    "Earth (brown)":  {"main": "#8a5a3c", "accent": "#e0b48f", "bg": "#1e1510", "card": "#33241a", "text": "#f6ebe0"},
}

QUOTES = [
    "Small steps every day beat big plans someday.",
    "You don't have to feel ready to begin.",
    "A hard day is still a day you showed up.",
    "Progress is quiet. Keep going anyway.",
    "Your mood is weather, not your whole sky.",
    "Rest is part of the work, not the opposite of it.",
    "One breath, one step, one quest.",
    "Be kind to the person you are today.",
    "You are allowed to be a work in progress.",
    "Today's effort is tomorrow's confidence.",
    "Courage is just doing the next small thing.",
    "Not perfect, just moving forward.",
]


def quote_of_the_day():
    return QUOTES[datetime.date.today().toordinal() % len(QUOTES)]


def inject(palette_name):
    p = PALETTES.get(palette_name) or PALETTES["Forest (green)"]
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
:root {{ --main:{p['main']}; --accent:{p['accent']}; --card:{p['card']}; --txt:{p['text']}; --bg:{p['bg']}; }}
html, body, h1, h2, h3, p, label, button, textarea, input, li {{ font-family: 'Poppins', system-ui, sans-serif; }}
.stApp {{ background: radial-gradient(circle at 15% 0%, {p['main']}55 0%, transparent 45%),
          radial-gradient(circle at 90% 100%, {p['accent']}22 0%, transparent 40%), var(--bg);
          color: var(--txt); }}
h1, h2, h3, label, p, span, li {{ color: var(--txt); }}
h1 {{ font-weight: 700; background: linear-gradient(90deg, var(--accent), #ffffff); -webkit-background-clip: text;
     background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: .5px; }}
h2, h3 {{ font-weight: 600; }}
footer, #MainMenu, .stDeployButton {{ visibility: hidden; }}
section[data-testid="stSidebar"] {{ background: var(--card); border-right: 1px solid {p['accent']}33; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ background: rgba(255,255,255,.04); backdrop-filter: blur(8px);
     border: 1px solid {p['accent']}33; border-radius: 22px; box-shadow: 0 10px 30px #0004; }}
div[data-testid="stMetric"] {{ background: var(--card); border: 1px solid {p['accent']}44; border-radius: 16px;
     padding: 12px 16px; }}
div[data-testid="stMetricValue"] {{ color: var(--accent); font-weight: 700; }}
.stTextArea textarea, .stTextInput input {{ background: rgba(0,0,0,.28) !important; color: var(--txt) !important;
     border-radius: 14px !important; border: 1px solid {p['accent']}44 !important; }}
button[data-baseweb="tab"] {{ border-radius: 999px; }}
.stButton > button {{
  border-radius: 999px; border: 1px solid var(--accent); background: var(--card); color: var(--txt);
  padding: .55rem 1.4rem; font-weight: 600; transition: transform .15s ease, box-shadow .15s ease;
}}
.stButton > button:hover {{ transform: translateY(-2px) scale(1.04); box-shadow: 0 8px 22px {p['main']}99; border-color: var(--accent); }}
.stButton > button[kind="primary"] {{ background: linear-gradient(135deg, var(--main), {p['accent']}88); border: none; }}
.quote-card {{ border-left: 4px solid var(--accent); background: linear-gradient(90deg, var(--card), transparent);
  border-radius: 14px; padding: 14px 18px; margin: 4px 0 18px; font-size: 1.05rem; font-style: italic; }}
.step-card {{ background: linear-gradient(160deg, var(--card), {p['main']}66); border: 1px solid var(--accent);
  border-radius: 24px; padding: 30px 24px; margin: 10px 0 14px; text-align: center; font-size: 1.2rem;
  box-shadow: 0 14px 34px #0007; cursor: grab; user-select: none; touch-action: pan-y; }}
.step-card.from-right {{ animation: popR .35s ease; }}
.step-card.from-left {{ animation: popL .35s ease; }}
@keyframes popR {{ from {{ transform: translateX(60px) rotate(4deg); opacity: 0; }} to {{ transform: none; opacity: 1; }} }}
@keyframes popL {{ from {{ transform: translateX(-60px) rotate(-4deg); opacity: 0; }} to {{ transform: none; opacity: 1; }} }}
div[data-testid="stHorizontalBlock"] .stButton > button {{ width: 100%; }}
.gauge {{ background: var(--card); border: 1px solid {p['accent']}44; border-radius: 18px; padding: 14px 18px; margin: 8px 0 12px; }}
.gauge-top {{ display: flex; justify-content: space-between; font-size: 1rem; margin-bottom: 8px; }}
.gauge-bar {{ height: 14px; background: #0006; border-radius: 999px; overflow: hidden; }}
.gauge-fill {{ height: 100%; border-radius: 999px; transition: width .6s ease; }}
.gauge-label {{ margin-top: 8px; font-size: .9rem; opacity: .85; }}
#cursor-glow {{ position: fixed; width: 220px; height: 220px; border-radius: 50%; pointer-events: none; z-index: 0;
  background: radial-gradient(circle, {p['accent']}40 0%, transparent 70%); transform: translate(-50%, -50%);
  transition: left .08s linear, top .08s linear; }}
</style>""", unsafe_allow_html=True)

    # Cursor glow: the script is installed into the main page (not the tiny iframe),
    # so it keeps working when Streamlit re-renders.
    _install_js("glow-js", """
if (!document.getElementById('cursor-glow')) {
  const g = document.createElement('div'); g.id = 'cursor-glow'; document.body.appendChild(g);
  document.addEventListener('mousemove', e => { g.style.left = e.clientX + 'px'; g.style.top = e.clientY + 'px'; });
}""")


def quote_banner():
    st.markdown(f'<div class="quote-card">“{html.escape(quote_of_the_day())}”</div>', unsafe_allow_html=True)


def gauge(score, low=5.0, stressed=3.0):
    """Happiness score bar, 0 to 10."""
    score = max(0.0, min(10.0, float(score)))
    if score < stressed:
        color, label = "#e76f51", "Very low: stressed / overwhelmed"
    elif score < low:
        color, label = "#f4a261", "Low: sad / low energy"
    else:
        color, label = "#52b788", "Good: happy / okay"
    st.markdown(
        f'<div class="gauge"><div class="gauge-top"><span>Happiness score</span><b>{score:.1f} / 10</b></div>'
        f'<div class="gauge-bar"><div class="gauge-fill" style="width:{score * 10:.0f}%;background:{color}"></div></div>'
        f'<div class="gauge-label">{label}</div></div>', unsafe_allow_html=True)


def step_card(title, body, direction="right"):
    cls = "from-right" if direction == "right" else "from-left"
    st.markdown(f'<div class="step-card {cls}"><b>{html.escape(title)}</b><br>{html.escape(body)}</div>',
                unsafe_allow_html=True)


def swipe_script():
    """Swipe the card (finger or mouse) or use the arrow keys: right = Done, left = Skip."""
    _install_js("swipe-js", """
const click = (label) => {
  if (!document.querySelector('.step-card')) return;
  for (const b of document.querySelectorAll('button')) { if (b.innerText.includes(label)) { b.click(); return; } }
};
document.addEventListener('keydown', e => {
  const t = e.target.tagName; if (t === 'INPUT' || t === 'TEXTAREA') return;
  if (e.key === 'ArrowRight') click('Done');
  if (e.key === 'ArrowLeft') click('Skip');
});
let x0 = null;
const start = x => { x0 = x; };
const end = x => { if (x0 === null) return; const dx = x - x0; x0 = null; if (Math.abs(dx) > 70) click(dx > 0 ? 'Done' : 'Skip'); };
document.addEventListener('touchstart', e => { if (e.target.closest('.step-card')) start(e.touches[0].clientX); }, {passive: true});
document.addEventListener('touchend', e => end(e.changedTouches[0].clientX), {passive: true});
document.addEventListener('mousedown', e => { if (e.target.closest('.step-card')) start(e.clientX); });
document.addEventListener('mouseup', e => end(e.clientX));""")


def _install_js(script_id, code):
    """Add a script to the main page once. Never crashes the app if the embed is unavailable."""
    wrapper = ("<script>const d = window.parent.document;"
               f"if (!d.getElementById('{script_id}')) {{"
               "const s = d.createElement('script'); s.id = '" + script_id + "';"
               "s.textContent = " + _js_string(code) + "; d.head.appendChild(s); }</script>")
    try:
        components.html(wrapper, height=0)
    except Exception:
        pass


def _js_string(text):
    return json.dumps(text).replace("</", "<\\/")
