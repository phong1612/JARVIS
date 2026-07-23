import ollama


def summarize_conversation(history):

    conversation = "\n".join(
        [
            f"{msg['role']}: {msg['content']}"
            for msg in history
        ]
    )

    prompt = f"""
        You are a memory manager.

        Summarize the important information from this conversation.

        Keep:
        - user preferences
        - important facts about the user (name, projects, interests)
        - ongoing projects
        - explicit decisions the user asked for

        Remove:
        - greetings
        - unnecessary details
        - ANY mention of JARVIS opening, closing, or making mistakes with apps/tools
        - ANY meta-conversation about JARVIS correcting itself, apologizing, or discussing its own behavior
        - step-by-step narration of what actions were taken

        Only summarize genuine facts about the USER — their name, preferences, and projects — not what JARVIS did or got wrong during the conversation.

        If this conversation contains no genuinely useful facts about the user or their projects, respond with exactly: NO_MEMORABLE_CONTENT

        Conversation:

        {conversation}

        Summary:
        """

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        keep_alive="0",
        options={'temperature': 0, "num_ctx": 2048}
    )

    return response["message"]["content"]
