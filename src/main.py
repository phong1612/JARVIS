from voice.voice import record_until_toggle, Whisper_speech_to_text
from voice.speech import speak
from tools.file_index import build_file_index
from agent import run_agent, build_tool_index
from memory.memory import summarize_conversation
from rag import save_memory
import sys
import time
import signal

MAX_HISTORY_TURNS = 2
if __name__ == "__main__":
    history_chat = []

    def save_and_exit(signum=None, frame=None):
        if history_chat:
            summary = summarize_conversation(history_chat)
            if "NO_MEMORABLE_CONTENT" not in summary:
                save_memory(summary)
        print("\nSession saved. Thank you.")
        sys.exit(0)

    signal.signal(signal.SIGINT, save_and_exit)   # Ctrl+C
    signal.signal(signal.SIGQUIT, save_and_exit)  # Ctrl+\

    build_file_index()
    build_tool_index()
    

    speak("Hello, sir. I'm JARVIS, how can I help you today?")
    while (True):
        audio_data = record_until_toggle()
        if audio_data is None:
            speak("I can't hear you. Please retry...")
            continue  # skip this loop iteration, go straight back to "press Enter"
        user_text = Whisper_speech_to_text(audio_data)
        if "power down" in user_text.lower() or "powered down" in user_text.lower():
            speak('Powering down...')
            break
        print(f"You said: {user_text}")
        answer = run_agent(user_text, history_chat)
        print(f"JARVIS: {answer}")
        speak(answer) # Apply Piper voice

        # Add chat to history
        history_chat.append({"role": "user", "content": user_text})
        history_chat.append({"role": "assistant", "content": answer})

        #  save to memory
        if len(history_chat) >= MAX_HISTORY_TURNS * 2:
            summary = summarize_conversation(history_chat)
            if "NO_MEMORABLE_CONTENT" not in summary and "no_memorable_content" not in summary.lower().replace(" ", "_"):
                save_memory(summary)
            history_chat = history_chat[-MAX_HISTORY_TURNS:]

    if history_chat:
        summary = summarize_conversation(history_chat)
        if "NO_MEMORABLE_CONTENT" not in summary and "no_memorable_content" not in summary.lower().replace(" ", "_"):
            save_memory(summary)
    speak("Hope to see you later sir.")