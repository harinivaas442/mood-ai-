# AI Mood Quest+

Sign in -> write a diary entry -> take a camera photo -> the app finds your mood from the diary AND your face -> you get a 3-step quest -> earn points and a streak.

## Run (Windows)
```
python -m pip install streamlit pandas
python -m streamlit run app.py
python test_moods.py        # 13 diary samples
python test_extras.py       # sign-in, settings, face blending
```

## Sign in
- Email + password works out of the box. Passwords are stored hashed in `users.json`.
- The FIRST account you create becomes the developer account (it gets the Developer mode switch).
- "Continue with Google" appears only if you add Google credentials in `.streamlit/secrets.toml` (an `[auth]` block) and run `python -m pip install Authlib`. See Streamlit's st.login docs. Without that, use email + password.

## Camera
Press "Allow camera and take my photo" in the diary. Your browser then asks for camera permission. The photo is read for expression and not saved. Developer mode can turn the camera requirement off.

## Developer mode (sidebar switch, developer account only)
- **Customize:** color theme (green, blue, brown), motivational quotes, cursor glow, points, bonus, camera requirement, face weight, and page layout. Drag and drop needs `python -m pip install streamlit-sortables`; without it you pick the order from a list.
- **Quests:** write your own 3-step quest for any mood.
- **Face Lab:** save labelled photos of yourself (sad, angry, confused...) and press Train.

## Face model (optional)
`python -m pip install transformers torch pillow scikit-learn`
Uses the pretrained `trpakov/vit-face-expression` model (first run downloads it). It learned from many people, which is why it can work on strangers. Face Lab only tunes how expressions map to the 4 moods for your face; photos of one person cannot teach the app about everyone. Facial expression is also an imperfect signal for how someone feels, so the diary text stays the main input (face weight defaults to 30%). Photos stay in the `face_data` folder on your computer. Only photograph people who agree, and get a parent's permission for under-18s.

## Developer account
Only the developer account sees Developer mode and the settings. To check who the developer is, or to choose it:
```
python make_developer.py                   (lists accounts)
python make_developer.py you@gmail.com     (makes that account the only developer)
```
Run these in the app folder, where `users.json` is.

## Camera
The camera turns on only when you press "Turn on camera" and turns off as soon as the photo is taken. The diary photo is forgotten after each entry.

## Swipe cards
Swipe the quest card with finger or mouse (right = Done, left = Skip), use the arrow keys, or press the buttons.

## Tests
```
python test_moods.py       # 13 diary entries
python test_extras.py      # sign-in, settings, face blending
python test_app_flow.py    # 7 simulated user-flow rounds (simulated Streamlit, no browser)
```

## Happiness score (face)
The app finds your face, crops it (needs `opencv-python`), reads your expression and turns it into a happiness score from 0 to 10. Below 3 counts as Stressed/Overwhelmed, 3 to 5 as Tired/Low Energy (sad), 5 and up as Calm/Happy. The limits can be changed in Developer mode. "What the camera saw" shows the raw expression percentages so you can see why you got a score. If no face is found, the app says so and uses your diary only. If you updated some files but not others, copy ALL the files from the latest delivery.

## If the face reading says OFF or the score looks wrong
Run `python check_face.py` in the app folder. It shows which packages are missing, takes a webcam snapshot, and prints what the model sees and your happiness score. In the app, the line under the mood says whether it used "your diary only" or "your diary + your face", and a yellow note explains why the face was not used.
