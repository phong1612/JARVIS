# User Input Voice
from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np
import time

duration = 5
SAMPLE_RATE = 16000

is_recording = False
frames = []

model_size = "base"
model = WhisperModel(model_size, device="cpu", compute_type="int8")



def callback(indata, frame_count, time_info, status):
    if is_recording:
        frames.append(indata.copy())

def record_until_toggle():
    input("Press Enter to start talking...")
    print("Recording... press Enter again to stop")

    frames_local = []
    def callback(indata, frame_count, time_info, status):
        frames_local.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback):
        time.sleep(1)
        input()

    if not frames_local:
        print("No audio captured — try again.")
        return None  # signal to main.py that nothing was recorded
    
    audio = np.concatenate(frames_local, axis=0)
    return audio.flatten()

def Whisper_speech_to_text(audio_data):
    # Faster-Whisper
    segments, info = model.transcribe(audio_data, beam_size=5)
    segments = list(segments)

    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

    user_text = " ".join([seg.text for seg in segments])
    return user_text


