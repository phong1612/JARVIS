from tools import get_time, get_date, set_reminder, open_app, open_url, open_workspace, open_webspace, close_app, close_url, close_workspace, close_webspace, white_list, known_sites, workspaces, webspaces
from rag import collections, get_embedding, retrieve_memory
import ollama
import time

MODEL = "llama3.2:3b"
app_names = ", ".join(white_list.keys())
site_names = ", ".join(known_sites.keys())

def search_memory(query: str) -> str:
    print(f"[search_memory called with query: '{query}']")
    query_embedding = get_embedding(query)
    results = collections.query(query_embeddings=[query_embedding], n_results=2)
    memory = retrieve_memory(query)
    # print("Retrieved memory:")
    # print(memory)
    knowledge = "\n".join(results['documents'][0])
    # print("Retrieved Knowledge:")
    # print(knowledge)
    return f"Knowledge: {knowledge}.\nLong-tern memory: {memory}."

def safe_call(func_name: str, arguments: dict):
    if func_name not in tool_functions:
        return f"'{func_name}' is not a real tool — refused."
    func = tool_functions[func_name]
    if not arguments or not any(v for v in arguments.values()):
        return "Tool call had no usable arguments — refused."
    try:
        return func(**arguments)
    except TypeError as e:
        return f"Tool call failed — argument mismatch: {e}"

def clean_content(content: str) -> str:
    content = content.strip()
    if '"name"' in content and '"parameters"' in content:
        return "Sorry, I got confused processing that — could you rephrase?"
    return content

tools_schema = [
    {
        'type': 'function',
        "function": {
            "name": "open_app",
            "description": "Opens a named macOS application. Use this for a SINGLE specific app the user names directly (e.g. 'open notion'). Do NOT use this for workspace/preset requests — use open_workspace for those instead.",
            "parameters": {
                "type": "object",
                'properties': {
                    "name": {
                        "type": "string",
                        "description": "Name of the app to open. E.g. 'spotify', 'tradingview'."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        'type': 'function',
        "function": {
            "name": "open_url",
            "description": "Opens a URL in a browser. Use only when user ask to open or launch a website",
            "parameters": {
                "type": "object",
                'properties': {
                    "url": {
                        "type": "string",
                        "description": "The website to open. E.g. 'youtube', 'facebook'."
                    },
                    "browser": {
                        "type": 'string',
                        'description': "The browser that will be used to open the website on. E.g. 'brave' "
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        'type': 'function',
        "function": {
            "name": "close_app",
            "description": "Closes a named macOS application. Use this for a SINGLE specific app the user names directly (e.g. 'close notion'). Do NOT use this for workspace/preset requests — use open_workspace for those instead.",
            "parameters": {
                "type": "object",
                'properties': {
                    "name": {
                        "type": "string",
                        "description": "Name of the app to close. E.g. 'spotify', 'tradingview'."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        'type': 'function',
        "function": {
            "name": "close_url",
            "description": "Closes a URL in a browser. Use only when user ask to close a website",
            "parameters": {
                "type": "object",
                'properties': {
                    "url": {
                        "type": "string",
                        "description": "The website to close. E.g. 'youtube', 'facebook'."
                    },
                    "browser": {
                        "type": 'string',
                        'description': "The browser that will be applied to close the website on. E.g. 'brave' "
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        'type': 'function',
        "function": {
            "name": "search_memory",
            "description": """Search JARVIS's long-term memory and knowledge base.

                Use this whenever the user asks about:
                - previous conversations
                - personal preferences
                - ongoing projects
                - stored notes
                - anything JARVIS may have learned before

                The query should be specific and descriptive — rephrase the user's actual question into a searchable phrase (e.g. for "what's my name?" use query="user's name", not just "user" or "name").

                Do NOT use this for simple math or general world knowledge that you can already answer.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        'type': 'function',
        "function": {
            "name": "open_workspace",
            "description": "Opens a preset GROUP of applications for a named workspace (e.g. 'coding', 'study'). Only use this when the user explicitly says a workspace name — NOT when they name a single individual app, even if that app happens to also be part of a workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The workspace name, e.g. 'coding', 'trading', 'study'."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        'type': 'function',
        "function": {
            "name": "close_workspace",
            "description": "Closes a preset GROUP of applications for a named workspace (e.g. 'coding', 'study'). Only use this when the user explicitly says a workspace name — NOT when they name a single individual app, even if that app happens to also be part of a workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The workspace name, e.g. 'coding', 'trading', 'study'."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        'type': 'function',
        "function": {
            "name": "open_webspace",
            "description": "Opens a preset group of websites for a named webspace, e.g. 'code' or 'entertainment'. Use this when the user asks to open their webspace, setup, or environment by name, rather than individual websites.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The webspace name, e.g. 'code', 'school', 'entertainment'."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        'type': 'function',
        "function": {
            "name": "close_webspace",
            "description": "Opens a preset group of websites for a named webspace, e.g. 'code' or 'entertainment'. Use this when the user asks to open their webspace, setup, or environment by name, rather than individual websites.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The webspace name, e.g. 'code', 'school', 'entertainment'."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        'type': 'function',
        'function': {
            "name": "get_time",
            "description": "Get the current local time. Use this when the user ask for the current time.",
        }
    },
    {
        'type': 'function',
        'function': {
            "name": "get_date",
            "description": "Get the current local time. Use this when the user ask for the current time.",
        }
    },
    {
        'type': 'function',
        "function": {
            "name": "set_reminder",
            "description": "Sets a reminder. Use minutes_from_now for relative requests ('remind me in 10 minutes'), or target_time for a specific clock time ('remind me at 9pm' → target_time='21:00'). Always convert times to 24-hour HH:MM format. Provide only ONE of these two, never both.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "What to remind the user about."},
                    "minutes_from_now": {"type": "integer", "description": "Minutes from now, for relative time requests."},
                    "target_time": {"type": "string", "description": "24-hour HH:MM format, for absolute time requests. E.g. '21:00' for 9pm."}
                },
                "required": ["text"]
            }
        }
    }
]

tool_functions = {
    'get_date': get_date,
    'get_time': get_time,
    'set_reminder': set_reminder,
    'open_app': open_app,
    'open_url': open_url,
    'search_memory': search_memory,
    "open_workspace": open_workspace,
    "open_webspace": open_webspace,
    "close_app": close_app,
    "close_url": close_url,
    "close_workspace": close_workspace,
    "close_webspace": close_webspace
}



def run_agent(user_text: str, history: list) -> str:
    """
    Sends user_text to Ollama along with the tool schema.
    If Ollama chooses to call a tool, dispatch it and feed the result
    back for a final natural-language reply. Otherwise, return its
    direct answer as-is.
    """
    
    system_message = {
    "role": "system", "content": 
    f"""
    You are JARVIS. The user's name is Phong Dinh, or Jason for short.

    You have exactly these tools: get_time, get_date, set_reminder, open_app, open_url, search_memory, open_workspace, open_webspace, close_app, close_url.

    Installed Mac applications (use open_app for these): {app_names}
    Known websites (use open_url for these): {site_names}
    Workspaces (use open_workspace for these): {workspaces}
    Webspaces (use open_webspace for these): {webspaces}

    Call a tool whenever the user's request clearly matches what that tool does — reminders, opening/closing named apps or sites, checking time/date, or recalling past information. Trust a clear match; don't ask for clarification when the request is already specific enough.

    Only ask for clarification instead of calling a tool when the app, website, or workspace name genuinely isn't recognizable from the lists above and there's no reasonable match — not for requests that are simply worded differently than the examples.

    Example: user asks 'what's 2+2' → respond '4' directly, no tool call.
    Example: user asks 'open spotify' → call open_app with name='spotify'.
    Example: user asks 'what is the weather today' → call open_url with url='https://weather.com/'.
    Example: user asks 'close brave' → call close_app with name='brave'.
    Example: user asks 'remind me in 5 minutes to stretch' → call set_reminder with text='stretch', minutes_from_now=5.
    Example: user asks 'remind me at 9pm to sleep' → call set_reminder with text='sleep', target_time='21:00'.
    Example: user asks about something previously discussed → call search_memory.
    Example: user says something vague or unrelated to any tool, like sharing their name or making small talk → respond in plain text, no tool call, consider saving that into memory.

    When answering from retrieved memory or knowledge, some entries may be incomplete or say "unknown" — this does not mean the information is unavailable. If ANY retrieved entry contains a clear, specific answer, use it confidently."""
    }

    message = [system_message] + history + [{"role": "user", "content": user_text}]
    response = ollama.chat(
        model=MODEL,
        messages=message,
        tools=tools_schema,
        options={"temperature": 0, "num_ctx": 2048},
        keep_alive="0"
    )
    content = response['message']['content'].strip()
    if content.startswith('{') and '"name"' in content and '"parameters"' in content:
        return "Sorry, I got confused processing that — could you rephrase?"
    tool_calls = response['message'].tool_calls
    if not tool_calls:
        return clean_content(response['message']['content'])
    message.append(response['message'])
    tool_calls = response['message'].tool_calls

    print("TOOL CALLS:")
    print(tool_calls)
    for tool in tool_calls:
        function_name = tool.function.name
        arguments = tool.function.arguments
        results = safe_call(function_name, arguments)
        time.sleep(1.5)

        message.append({
            'role': 'tool',
            'content': str(results)
        })
    final_response = ollama.chat(
        model=MODEL, 
        messages=message, 
        tools=tools_schema,
        options={'temperature': 0, "num_ctx": 2048},
        keep_alive="0"
    )
    answer = clean_content(final_response['message']['content'])

    return answer
if __name__ == "__main__":
    # quick manual tests, no voice involved yet
    # print(search_memory("Do you remember what we were talking about?"))
    print(run_agent("Set reminder in 2 minutes to wake up.", []))