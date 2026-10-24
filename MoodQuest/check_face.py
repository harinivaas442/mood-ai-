"""Check the face feature. Run:  python check_face.py            (takes a webcam snapshot)
                              or python check_face.py photo.jpg (uses your photo)
It prints what is installed, what the model sees, and your happiness score."""
import sys

import face

ok = lambda v: "OK     " if v else "MISSING"
st = face.status()
print("Face model packages :", ok(st["model"]), "" if st["model"] else "-> missing: " + ", ".join(face.missing()))
print("Face crop (opencv)  :", ok(st["face_crop"]))
print("Scan dots           :", ok(st["dots"]))
if not st["model"]:
    print("\nDouble-click 'Install Face Features.bat' (or run: python -m pip install " + " ".join(face.missing()) + ")")
    sys.exit(1)

path = sys.argv[1] if len(sys.argv) > 1 else None
if path is None:
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        good, frame = cap.read()
        cap.release()
        if good:
            path = "check_photo.jpg"
            cv2.imwrite(path, frame)
            print("\nTook a webcam photo:", path, "(smile at the camera!)")
        else:
            print("\nCould not open the webcam. Run: python check_face.py yourphoto.jpg")
    except ImportError:
        print("\nopencv-python is missing, so no webcam snapshot. Run: python check_face.py yourphoto.jpg")
if path is None:
    sys.exit(1)

data = open(path, "rb").read()
print("Loading the model (first time downloads it, needs internet)...")
try:
    labels = face._get_pipe().model.config.id2label
    print("Model labels:", list(labels.values()))
    info = face.analyse_photo(data)
except Exception as exc:
    print("FAILED:", type(exc).__name__, exc)
    sys.exit(1)
if not info["face_found"]:
    print("No face found in the photo. Move closer, face the light, and try again.")
else:
    print("\nWhat the model sees:")
    for name, p in sorted(info["probs"].items(), key=lambda x: -x[1]):
        print(f"  {name:9} {p * 100:5.1f}%")
    print(f"\nHappiness score: {info['happiness']} / 10")
    print("Mood scores:", {k: round(v, 2) for k, v in info["mood_scores"].items()})
img = face.draw_dots(data)
if img is not None:
    img.save("check_dots.jpg")
    print("Saved the scan dots picture: check_dots.jpg")
else:
    print("No dots picture (no face found, or opencv/mediapipe missing).")
