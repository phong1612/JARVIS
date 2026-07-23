ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMEIQ3KpzJBQ3i4RmEC/iQnb035+b76LZ/kUtS4KlRG6

# J.A.R.V.I.S

A local-first, voice-driven personal AI assistant that runs entirely on your own hardware — retrieval-augmented question answering, persistent long-term memory, and safe, whitelisted control over your macOS apps, browser, and files.

Built as a hands-on exploration of the core architecture behind modern AI agents: RAG, embeddings, tool-calling, and dynamic context management, all running locally on a memory-constrained laptop rather than a cloud GPU.

> 📹 **Demo video:** <iframe width="560" height="315" src="https://youtu.be/Be0ic9Q66lM" frameborder="0" allowfullscreen></iframe>   

---

## What it does

- **Talk to it.** Push-to-talk voice input, transcribed locally via Whisper — no cloud speech API.
- **Ask it things.** Answers grounded in a local knowledge base (RAG over ChromaDB), not just the model's raw training data.
- **It remembers you.** Conversations are periodically summarized and saved to long-term memory, retrievable in future sessions — JARVIS can recall facts, preferences, and past decisions across restarts.
- **It acts on your behalf.** Opens and closes whitelisted apps and websites, launches preset "workspaces" (e.g. "open my coding workspace"), sets reminders that sync to Apple Reminders, checks system status, and finds/opens files in your own documents — all gated behind explicit safety checks.
- **It speaks back.** Replies are read aloud via a local neural TTS voice (Piper) — no audio ever leaves your machine.
- **It scales.** As the tool library grows, JARVIS doesn't cram every tool description into every request — it semantically retrieves only the handful of tools relevant to what you just asked, keeping the model's context window bounded regardless of how many capabilities are added.

---

## Why local-first

JARVIS runs its LLM (via [Ollama](https://ollama.com)), speech-to-text, text-to-speech, and vector storage entirely on-device. No conversation, file content, or personal data is sent anywhere by default.

This isn't a purity stance — it's a deliberate design choice with real tradeoffs, made explicit rather than hidden:

- **Pro:** works with no internet connection, no per-request cost, no data leaving the machine.
- **Con:** capped by local hardware — this build targets an 8GB unified-memory MacBook Pro M1, which shaped nearly every architectural decision below.
- **Exception, by design:** a small number of tools (e.g. web search) are allowed to reach the internet when the task genuinely requires it. JARVIS is local-first, not offline-only.

---

## Architecture

```
                Voice input (push-to-talk)
                        │
                        ▼
                faster-whisper (local STT)
                        │
                        ▼
                Ollama LLM (llama3.2:3b) ──► decides: answer directly, or call a tool?
                        │                            │
                        │                    ┌───────┴────────┐
                        │                    ▼                ▼
                        │            RAG retrieval      Tool dispatch
                        │          (ChromaDB: notes,   (whitelist-checked
                        │           memory, files,      subprocess/osascript
                        │           tool descriptions)  execution)
                        │                    │                │
                        │                    └───────┬────────┘
                        ▼                            ▼
                Final reply  ◄──────── Ollama synthesizes result
                        │
                        ▼
                Piper (local TTS) ──► spoken response
```

**Key design decisions:**

- **Tool-calling, not free-form execution.** The LLM never runs arbitrary commands. It selects from a fixed set of Python functions with typed parameters; every function independently validates its own inputs (whitelists, path sandboxing, extension restrictions) before doing anything irreversible.
- **Dynamic tool retrieval.** Tool descriptions are embedded once and indexed in ChromaDB. Each request is matched against that index to pull in only the ~4-6 most relevant tools, rather than sending the full tool library (now 15+ functions) on every call. This keeps the context window — and therefore RAM usage — from growing linearly with feature count.
- **Three separate ChromaDB collections:** `jarvis_knowledge` (seeded facts), `jarvis_memory` (summarized conversation history), and `jarvis_file_index` (embedded previews of indexed personal documents) — each with its own retrieval logic, since "what do I know," "what have we discussed," and "what files exist" are genuinely different questions.
- **Confirmation-gated destructive actions.** System-level actions with real consequences (shutdown, restart) require an explicit two-step confirmation rather than executing on the first request.
- **Sandboxed, extension-restricted file access.** All file writes are confined to a dedicated folder; all file reads (including a broader, semantically-searchable personal document index) are validated against path traversal before any I/O occurs.

---

## Tech stack

| Layer | Tool |
|---|---|
| LLM | [Ollama](https://ollama.com) — `llama3.2:3b` |
| Embeddings | `nomic-embed-text` (via Ollama) |
| Vector store | ChromaDB (persistent, local) |
| Speech-to-text | `faster-whisper` |
| Text-to-speech | [Piper](https://github.com/OHF-Voice/piper1-gpl) |
| System automation | `subprocess`, AppleScript (`osascript`), Apple Reminders integration |
| PDF parsing | `pypdf` |
| Runtime | Python 3.11, conda |

---

## Setup

```bash
# 1. Clone and create the environment
conda create -n jarvis python=3.11
conda activate jarvis
pip install -e .

# 2. Install Ollama and pull the models
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# 3. Install Piper and grab a voice
# (see /src/voice/Voices for expected model path)

# 4. Run
python src/main.py
```

Hold **Enter** to talk, press again to stop. Say "power down" to end a session (long-term memory is saved on graceful exit, Ctrl+C, and Ctrl+\\).

---

## Known limitations

This project was deliberately built and tuned against real hardware constraints rather than assuming unlimited resources — the limitations below are documented, not hidden:

- **8GB memory ceiling.** Running Ollama, Whisper, and Piper simultaneously alongside a normal daily app load (browser, editor) leaves limited headroom. Opening several heavy applications in one command can cause temporary system-wide slowdown. Mitigations in place: short `keep_alive` windows, capped context length, staggered multi-app launches, and a smaller/faster Whisper model tier.
- **Small-model tool-calling isn't perfectly reliable.** `llama3.2:3b` occasionally misselects a tool or hallucinates an argument on ambiguous input. This is mitigated, not eliminated, through tightly-scoped tool descriptions, explicit examples, defensive argument parsing, and a strict server-side whitelist that refuses any invalid or unrecognized action before it can execute — the failure mode is "asks for clarification," never "does something unintended."
- **Speech recognition accuracy varies** with background noise and, occasionally, misidentifies the spoken language on short utterances.
- **No wake word / continuous listening** (by design, for now) — push-to-talk avoids running a second always-on model competing for limited RAM.

---

## Roadmap

Deliberately scoped out of the current build, tracked as future work:

- Voice activity detection (auto-stop recording on silence, no manual toggle)
- Wake-word activation (fully local, e.g. openWakeWord)
- Live web search with actual content synthesis (current web tools open a browser tab; they don't read and summarize results)
- MCP integration for standardized access to external services (calendar, spreadsheets)
- Optional remote/cloud Ollama backend for heavier models, as an explicit opt-in alongside the local-first default

---

## Project structure

```
src/
├── main.py           # entry point — voice loop, session lifecycle, memory persistence
├── agent.py           # tool-calling orchestration, dynamic tool selection
├── rag.py              # ChromaDB clients, embeddings, knowledge/memory retrieval
├── voice/
│   ├── voice.py         # push-to-talk capture + Whisper transcription
│   └── speech.py        # Piper TTS synthesis + playback
├── tools/
│   ├── tools.py           # apps, browser, workspaces, reminders, system status
│   └── file_access.py + file_index.py   # sandboxed file I/O + semantic file search
└── memory/
    └── memory.py          # conversation summarization for long-term memory
```

---

## Author

Jason (Phong) Dinh — Master of Artificial Intelligence, Monash University