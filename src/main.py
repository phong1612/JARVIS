from voice import record_until_toggle, Whisper_speech_to_text
from agent import run_agent
from memory import summarize_conversation
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

    print("Hello, sir. I'm JARVIS, how can I help you today?")
    while (True):
        if time.time() - last_activity > 600:
            print("No activity for 10 minutes.")
            break
        audio_data = record_until_toggle()
        if audio_data is None:
            print("I can't hear you. Please retry...")
            continue  # skip this loop iteration, go straight back to "press Enter"
        last_activity = time.time()
        user_text = Whisper_speech_to_text(audio_data)
        if "power down" in user_text.lower() or "powered down" in user_text.lower():
            print('Powering down...')
            break
        print(f"You said: {user_text}")
        answer = run_agent(user_text, history_chat)
        print(f"JARVIS: {answer}")
        history_chat.append({"role": "user", "content": user_text})
        history_chat.append({"role": "assistant", "content": answer})

        if len(history_chat) >= MAX_HISTORY_TURNS * 2:
            summary = summarize_conversation(history_chat)
            if "NO_MEMORABLE_CONTENT" not in summary and "no_memorable_content" not in summary.lower().replace(" ", "_"):
                save_memory(summary)
            history_chat = history_chat[-MAX_HISTORY_TURNS:]

    if history_chat:
        summary = summarize_conversation(history_chat)
        if "NO_MEMORABLE_CONTENT" not in summary and "no_memorable_content" not in summary.lower().replace(" ", "_"):
            save_memory(summary)
    print("Thank you.")