import mediapipe as mp
print(f"Mediapipe version: {mp.__version__}")
try:
    import mediapipe.solutions.hands as hands
    print("Import 'mediapipe.solutions.hands' worked")
except ImportError as e:
    print(f"Import 'mediapipe.solutions.hands' failed: {e}")

try:
    from mediapipe.python.solutions import hands
    print("Import 'from mediapipe.python.solutions import hands' worked")
except ImportError as e:
    print(f"Import 'from mediapipe.python.solutions import hands' failed: {e}")

try:
    import mediapipe.python.solutions.hands as hands
    print("Import 'import mediapipe.python.solutions.hands' worked")
except ImportError as e:
    print(f"Import 'import mediapipe.python.solutions.hands' failed: {e}")
