# AI Mood Quest Plus

A student mood app built with Python and Streamlit. A student writes a short diary entry and can add a camera photo. The app finds the mood, gives a personalised 3-step quest, and tracks points and a daily streak.

## Features

- **Diary AI:** reads a short entry and sorts it into 4 moods: Stressed/Overwhelmed, Tired/Low Energy, Excited/Energized, Calm/Happy. It handles negation ("not tired") and mixed feelings ("exhausted but excited").
- **Face happiness score:** the camera photo is turned into a score from 0 to 10.
  - Below 3 = Stressed/Overwhelmed
  - 3 to 5 = Tired/Low Energy
  - 5 and up = Calm/Happy
  - The limits can be changed in Developer mode.
- **Camera on demand:** the camera only turns on when you press the button, and turns off after the photo. The photo is not kept.
- **Swipe quest cards:** each quest has 3 steps. Swipe or use the buttons or arrow keys (right = Done, left = Skip).
- **Points and streaks:** 10 points per step, plus a bonus and a streak day for finishing all 3 steps.
- **Quest log:** history of completed quests and a mood chart.
- **Sign-in:** email + password (stored hashed). Google sign-in is optional.
- **Motivational quotes** on the start page.
- **Themes:** Forest (green), Ocean (blue), Earth (brown), with a cursor glow.
- **Developer mode (developer account only):**
  - **Customize:** color theme, points, bonus, camera requirement, face weight, happiness limits, drag-to-reorder layout.
  - **Quests:** write your own 3-step quest for any mood.
  - **Face Lab:** save labelled photos of yourself (sad, angry, confused...) and train the face mapping.

## What you need

| Item | Required? | Notes |
|---|---|---|
| Python 3.10 or newer | Yes | Download from python.org. On Windows, tick "Add Python to PATH" during install. |
| streamlit, pandas | Yes | Small and quick to install. |
| Face packages | Optional | transformers, torch, pillow, scikit-learn, opencv-python. The download is large (several GB) and takes a few minutes. Without them the app still works from the diary text only. |
| A webcam and a browser | Only for the camera | The browser asks for camera permission. |
| Internet | First face use | The face model downloads once. |

**Is it easy?** The basic app is easy: about 5 minutes. The face features are moderate, because the install is big and can fail on newer Python versions.

## Install and run (Windows)

1. Put all the project files in one folder.
2. Open a terminal in that folder: click the folder's address bar, type `cmd`, press Enter.
3. Install the basics:
```
python -m pip install streamlit pandas
```
4. Start the app:
```
python -m streamlit run app.py
```
5. Your browser opens at `http://localhost:8501`. Keep the terminal window open while you use the app. If Streamlit asks for an email the first time, press Enter to skip.

**Shortcut:** double-click `Start Mood Quest.bat` instead of steps 2 to 4.

If `python` is not recognized, use `py` instead: `py -m pip install streamlit pandas` and `py -m streamlit run app.py`.

## Install the face features (optional)

Double-click `Install Face Features.bat`, or run:
```
python -m pip install transformers torch pillow scikit-learn opencv-python streamlit-sortables Authlib
```
Optional face dots with real landmarks (may fail on some Python versions; the app has a fallback):
```
python -m pip install mediapipe
```
Check that it works:
```
python check_face.py
```
It lists what is installed, takes a webcam snapshot, and prints what the model sees and your happiness score.

## First use

1. Open the app and choose **Create account**. The first account you create becomes the developer account.
2. Write a diary entry, press **Turn on camera**, take a photo, then press **Find my mood & start quest**.
3. Swipe through the 3 quest cards and press **Finish quest**.

## Developer account

```
python make_developer.py                  (lists accounts)
python make_developer.py you@gmail.com    (makes that account the only developer)
```
Run these in the app folder, where `users.json` is.

## Google sign-in (optional)

Add an `[auth]` block to `.streamlit/secrets.toml` with your Google credentials (see the Streamlit `st.login` docs) and run `python -m pip install Authlib`. Without this, email + password is used.

## Troubleshooting

| Problem | Fix |
|---|---|
| `streamlit is not recognized` | Use `python -m streamlit run app.py` |
| `requirements.txt` not found | The terminal is in the wrong folder. Type `dir` to check, or run `python -m pip install streamlit pandas` directly. |
| `KeyError: 'palette'` | An old `settings.py` is mixed with new files. Copy ALL files from the latest version into a fresh folder. |
| "Connection error" in the browser | The app stopped. Close old terminal windows, start the app again, and open a new browser tab. |
| Face reading says OFF | Install the face features (above), then restart the app. |
| Photo always gives the same mood | Run `python check_face.py`. In the app, open "What the camera saw" to see the raw expression percentages. Face the light and move closer. |

## Tests

```
python test_moods.py       # 13 diary entries
python test_extras.py      # sign-in, settings, face scoring
python test_app_flow.py    # 8 simulated user-flow rounds (no browser needed)
```
13 of 13 sample diary entries are classified correctly. Known limit: sarcasm that uses positive words ("I just love failing quizzes") can fool the offline engine.

## Privacy and safety

- Photos are not kept after a diary entry. Face Lab photos are saved only in the `face_data` folder on your own computer.
- Only photograph people who agree. Get a parent's permission for anyone under 18.
- Facial expression is an imperfect clue to how someone feels, so the diary text stays the main input (the face counts 30% by default).
- Face Lab tunes the mapping for your face. It cannot teach the app about everyone, because the pretrained model does that part.

## Credits

Made by **Harinivas and Vijay**, Classes **7B1 and 7B2**, **Gems Millennium School, Sharjah**.
