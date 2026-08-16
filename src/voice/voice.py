# VAD
from silero_vad import load_silero_vad, VADIterator
from collections import deque
# User Input Voice
from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np
import time
import torch
import queue

SAMPLE_RATE = 16000
CHUNK_SIZE = 512 # 32ms at 16kHz
MAX_RECORD_SECONDS = 30
max_chunk = int(MAX_RECORD_SECONDS * SAMPLE_RATE / CHUNK_SIZE)

is_recording = False
frames = []

vad_model = load_silero_vad()
vad_iterator = VADIterator(
    vad_model,
    threshold=0.5,
    sampling_rate=SAMPLE_RATE,
    min_silence_duration_ms=500,
    speech_pad_ms=100
)


model_size = "base"
model = WhisperModel(model_size, device="cpu", compute_type="int8")



def callback(indata, frame_count, time_info, status):
    if is_recording:
        frames.append(indata.copy())

def record_until_silence():
    audio_queue = queue.Queue()

    def callback(indata, frame_count, time_info, status):
        if status:
            print(status)
        audio_queue.put(indata[:, 0].copy())

    frames = []

    pre_buffer_chunks = int(0.5 * SAMPLE_RATE / CHUNK_SIZE)
    pre_buffer = deque(maxlen=pre_buffer_chunks)

    speech_started = False
    chunk_count = 0

    vad_iterator.reset_states()

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=CHUNK_SIZE, callback=callback):
        print("Listening...")
        while True:
            chunk_count += 1
            if chunk_count >= max_chunk:
                print("Max recording leangth allowed - stopping")
                break
            chunk = audio_queue.get()
            pre_buffer.append(chunk)

            speech_dict = vad_iterator(torch.from_numpy(chunk), return_seconds=True)
            if speech_dict:
                print("VAD:", speech_dict)

            if speech_dict and "start" in speech_dict:
                speech_started = True
                frames.extend(list(pre_buffer))
                pre_buffer.clear()
            if speech_started:
                frames.append(chunk)

            if speech_started and speech_dict and "end" in speech_dict:
                break
    vad_iterator.reset_states()

    if not frames:
        print("No speech detected — try again.")
        return None  # signal to main.py that nothing was recorded
    
    audio = np.concatenate(frames)
    return audio

def Whisper_speech_to_text(audio_data):
    # Faster-Whisper
    segments, info = model.transcribe(audio_data, beam_size=5)
    segments = list(segments)

    # print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

    user_text = " ".join([seg.text for seg in segments])
    return user_text


