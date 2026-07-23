from tools.tools import get_time, get_date, set_reminder, open_app, open_url, search_engine, open_workspace, open_webspace, close_app, close_url, close_workspace, close_webspace, get_battery_status, white_list, known_sites, workspaces, webspaces
from tools.file_access import open_file, create_file, read_file, find_file
from rag import collections, get_embedding, retrieve_memory, client
import ollama
import time
import inspect # Check required arguments of functions

MODEL = "llama3.2:3b"
app_names = ", ".join(white_list.keys())
site_names = ", ".join(known_sites.keys())

tool_index = client.get_or_create_collection(name="jarvis_tools")
def build_tool_index():
    if tool_index.count() > 0:
        return
    print("Building JARVIS's tool kit.")
    for tool in tools_schema:
        name = tool["function"]["name"]
        desc = tool["function"]["description"]
        embedding = get_embedding(f"{name}: {desc}")
        tool_index.add(
            documents=[name],
            embeddings=[embedding],
            ids=[name]
        )

CORE_TOOLS = {"search_memory"} # always included
def select_tools(query: str, k:int = 6):
    query_embed = get_embedding(query)
    results = tool_index.query(query_embeddings=[query_embed], n_results = k)
    selected = set(results["documents"][0]) | CORE_TOOLS

    filtered_schema = [t for t in tools_schema if t["function"]["name"] in selected]
    filtered_functions = {name: tool_functions[name] for name in selected if name in tool_functions}

    return filtered_schema, filtered_functions


def search_memory(query: str) -> str:
    print(f"[search_memory called with query: '{query}']")
    query_embedding = get_embedding(query)
    results = collections.query(query_embeddings=[query_embedding], n_results=2)
    memory = retrieve_memory(query)
    knowledge = "\n".join(results['documents'][0])
    return f"Knowledge: {knowledge}.\nLong-tern memory: {memory}."

def safe_call(func_name: str, arguments: dict):
    if func_name not in tool_functions:
        return f"'{func_name}' is not a real tool — refused."
    
    func = tool_functions[func_name]
    sig = inspect.signature(func)
    required_args = len(sig.parameters) > 0
    func = tool_functions[func_name]
    if required_args and (not arguments or not any(v for v in arguments.values())):
        return "Tool call had no usable arguments — refused."
    try:
        return func(**arguments)
    except TypeError as e:
        return f"Tool call failed — argument mismatch: {e}"

def clean_content(content: str) -> str:
    content = content.strip()
    looks_like_fake_call = (
        ('"name"' in content and '"parameters"' in content) or
        ('open_' in content and '(' in content and ')' in content) or
        ('close_' in content and '(' in content and ')' in content) or
        content.startswith('`') 
    )
    if looks_like_fake_call:
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
            "description": "Opens a website in a browser. Use only when user ask to open, visit, go to, or launch a website",
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
        'function': {
            "name": "search_engine",
            "description": "Browse the browser to search for something. Use only when user ask to search for something. Must not claim facts obtained from a search unless a tool explicitly returned those facts. You are only opening a browser tab — you cannot see or know the actual content of that page. NEVER describe, summarize, or make up what might be on a website or search result. Simply confirm that you opened it, and let the user look at it themselves.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_text": {
                        "type": "string",
                        "description": "The topic to search for."
                    }
                },
                "required": ["user_text"]
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
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        'type': 'function',
        'function': {
            "name": "get_date",
            "description": "Get the current local time. Use this when the user ask for the current time.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_battery_status",
            "description": "Get the status of the machine's battery. Use this when the user ask for the status of the laptop's battery.",
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_file",
            "description": """
                Find files on the user's computer by filename. Use this when the user wants to locate a file or asks where a file is stored. This tool only searches filenames and returns matching file paths. It does NOT read file contents. Make sure that you find the file with the exact name as query. If you can't find one then tell the user the file can't be found and tell them to clarify. NEVER claim to have opened, read, previewed, or shown the contents of a file unless you actually called open_file or read_file in THIS response and received a real result. Finding a file's path via find_file does NOT mean it has been opened or read.

                Examples:
                - "Find my resume."
                - "Where is my thesis?"
                - "Locate budget.xlsx."
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The file you want to find."},
                    "max_results": {"type": "number", "description": "The maximum number of results to get."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": """
                Read the contents of a text-based file.

                Use this after a file has already been identified, or when the user asks to read, summarize, explain, or answer questions about a specific file.

                Examples:
                - "Read my notes."
                - "Summarize Resume.md."
                - "What does todo.txt say?"

                Only use this for files that have already been found or whose location is known.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "The file you want to read."}
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_file",
            "description": """
                Open the text-based file on a suitable application (e.g Brave or Preview)
                Use this after a file has already been identified, or when the user asks to open, display, show a specific file.

                Examples:
                - "Open my note file."
                - "Open Resume.pdf."
                - "What does todo.txt look like?"

                Only use this for files that have already been found or whose location is known.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The file you want to open."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": """
                Create a new text or Markdown file in JARVIS's workspace.

                Use this when the user asks to create, save, write, or generate a note, document, checklist, or similar text file.

                Examples:
                - "Create a shopping list."
                - "Save this as notes.md."
                - "Make a file called ideas.txt."
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "The file you want to write."},
                    "content": {"type": "string", "description": "The content of the file."}
                },
                "required": ["filename", "content"]
            }
        }
    }
]

tool_functions = {
    'get_date': get_date,
    'get_time': get_time,
    'get_battery_status': get_battery_status,
    'set_reminder': set_reminder,
    'open_app': open_app,
    'open_url': open_url,
    "search_engine": search_engine,
    'search_memory': search_memory,
    "open_workspace": open_workspace,
    "open_webspace": open_webspace,
    "close_app": close_app,
    "close_url": close_url,
    "close_workspace": close_workspace,
    "close_webspace": close_webspace,
    "find_file": find_file,
    "read_file": read_file,
    "create_file": create_file,
    "open_file": open_file
}



def run_agent(user_text: str, history: list) -> str:
    """
    Sends user_text to Ollama along with the tool schema.
    If Ollama chooses to call a tool, dispatch it and feed the result
    back for a final natural-language reply. Otherwise, return its
    direct answer as-is.
    """
    
    relevant_schema, relevant_functions = select_tools(user_text)

    print(relevant_functions.keys())

    system_message = {
    "role": "system",
    "content":
    f"""
    You are JARVIS, a personal AI assistant created for Jason (Phong Dinh).

    Your purpose is to assist Jason by understanding his requests, maintaining continuity through memory, and taking useful actions when appropriate.

    You have access to long-term memory through the search_memory tool.
    Use search_memory when:
    - Jason asks about previous conversations or past decisions
    - Jason asks about his preferences, projects, or personal information
    - Jason references something that may have been discussed before
    - Additional context from memory would improve your answer

    Do NOT use search_memory for:
    - General knowledge questions
    - Simple calculations
    - Tasks where the answer is already available in the current conversation

    Available tools:
    {', '.join(relevant_functions.keys())}

    Use tools when they provide a direct action or missing information.
    Examples:
    - Opening/closing applications → use the appropriate app tool
    - Opening/closing websites → use the appropriate web tool
    - Checking current information (time/date/battery) → use the relevant tool
    - Searching online → use the search tool
    - Recalling previous information → use search_memory

    Do not describe tool calls in text.
    Never write examples like:
    open_app("spotify")
    open_url("facebook")
    open_file

    Instead, call the tool through the provided tool system.

    When no tool is needed:
    - Answer naturally and conversationally
    - Explain clearly
    - Maintain awareness that you are JARVIS, Jason's personal assistant

    Decision rules:
    1. Prefer taking action over explaining how Jason can do it himself.
    2. If a request clearly matches a tool, use the tool immediately.
    3. Only ask for clarification when the request is genuinely ambiguous or missing required information.
    4. If a tool returns useful information, incorporate it naturally into your response.

    Memory awareness:
    You should behave as an assistant with continuity across conversations.
    Use retrieved memories when relevant, but do not assume missing information.
    If memory contains a clear answer, use it confidently.

    Current available applications:
    {app_names}

    Known websites:
    {site_names}

    Available workspaces:
    {workspaces}

    Available webspaces:
    {webspaces}
    """
    }
    message = [system_message] + history + [{"role": "user", "content": user_text}]
    response = ollama.chat(
        model=MODEL,
        messages=message,
        tools=relevant_schema,
        options={"temperature": 0, "num_ctx": 4096},
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
    print(f"Tool call: {tool_calls}")
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
        options={'temperature': 0, "num_ctx": 4096},
        keep_alive="0"
    )
    answer = clean_content(final_response['message']['content'])

    return answer
# agent.py — run directly
if __name__ == "__main__":
    client.delete_collection("jarvis_tools")
    tool_index = client.get_or_create_collection(name="jarvis_tools")