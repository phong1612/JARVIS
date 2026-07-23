import subprocess
import os
import uuid
from urllib.parse import urlparse

import time
from time import localtime, strftime
import datetime
import threading

import json
import psutil


white_list = {
    "notion": "Notion",
    "obsidian": "Obsidian",
    "brave": "Brave Browser",
    "vs code": "Visual Studio Code",
    "tradingview": "TradingView",
    "zalo": "Zalo",
    "ghostty": "Ghostty",
    "finder": "Finder",
    "spotify": "Spotify",
    "discord": "Discord",
    "whatsapp": "WhatsApp",
    "activity monitor": "Activity Monitor"
}
known_sites = {
    'youtube': 'https://www.youtube.com/',
    "instagram": "https://www.instagram.com/",
    'github': 'https://github.com/',
    'facebook': 'https://www.facebook.com/',
    'gmail': 'https://mail.google.com',
    'vercel': 'https://vercel.com/phongnhatdinhs-projects',
    'moodle': 'https://learning.monash.edu/',
    'ed': 'https://edstem.org/au/dashboard',
    'supabase': "https://supabase.com/dashboard/"
}
browsers = {
    "google": "Google Chrome",
    "brave": "Brave Browser",
    "edge": "Microsoft Edge",
    "safari": "Safari"
}
workspaces = {
    "coding": ["vs code", "brave", "notion", "activity monitor"],
    "trading": ["tradingview", "brave", "discord"],
    "study": ["notion", "obsidian"],
}
webspaces = {
    "entertainment": ["youtube", "facebook", "instagram"],
    "school": ["moodle", "gmail", "ed"],
    "code": ["vercel", "github", "supabase"]
}


# Low-risk, easy tools
def get_time():
    return f" The current time is {strftime('%H:%M:%S', localtime())}."

def get_date():
    return f"The current date is {strftime('%A %Y-%m-%d', localtime())}."

# Set Reminder
def set_reminder(text: str, minutes_from_now=None, target_time=None) -> str:
    now = datetime.datetime.now()

    if minutes_from_now in (None, "null", "none", ""):
        minutes_from_now = None
    if target_time in (None, "null", "none", ""):
        target_time = None

    used_fallback_note = ""
    if minutes_from_now is not None and target_time is not None:
        used_fallback_note = f" (Note: you also mentioned {minutes_from_now} minutes, but I used the specific time {target_time} instead.)"
        minutes_from_now = None

    if minutes_from_now is not None:
        try:
            minutes_from_now = int(minutes_from_now)
        except (ValueError, TypeError):
            return f"Couldn't understand '{minutes_from_now}' as a number of minutes."
        due = now + datetime.timedelta(minutes=minutes_from_now)
    elif target_time is not None:
        try:
            hour, minute = map(int, target_time.split(":"))
        except (ValueError, AttributeError):
            return f"Couldn't understand the time '{target_time}' — please use HH:MM format."
        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if due <= now:
            due += datetime.timedelta(days=1)
    else:
        return "No time specified — please say 'in X minutes' or 'at HH:MM'."

    applescript_date = due.strftime("%d/%m/%Y %I:%M:%S %p")
    script = f'''
    tell application "Reminders"
        set newReminder to make new reminder with properties {{name:"{text}", remind me date:date "{applescript_date}"}}
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True)
        return f"Reminder set for {due:%Y-%m-%d %H:%M:%S}: {text}.{used_fallback_note}"
    except subprocess.CalledProcessError as e:
        return f"Failed to create reminder: {e.stderr}"


def get_battery_status():
    battery_status = psutil.sensors_battery()
    return f"""
    Percentage of battery: {battery_status.percent}
    Approximate time remaining: {battery_status.secsleft}
    Is power cable connected: {battery_status.power_plugged}
    """

# Normal-risk, medium difficulties 
def open_workspace(name: str) -> str:
    key = name.lower().strip()
    summary = ''
    if key not in workspaces:
        return f"'{name}' is not a known workspace — refused."
    else:
        for app in workspaces[key]:
            message = open_app(app)
            time.sleep(2.0)
            summary += message
        return summary

def open_webspace(name: str) -> str:
    key = name.lower().strip()
    summary = ''
    if key not in webspaces:
        return f"'{name}' is not a known webspace — refused."
    else:
        for app in webspaces[key]:
            message = open_url(app)
            time.sleep(1.0)
            summary += message
        return summary

def open_app(name: str):
    """
    Opens a whitelisted macOS application by name.
    Returns a string describing what happened (success or refusal) —
    this string is what gets fed back to Ollama, so make it clear.
    """

    key = name.lower().strip()
    if key not in white_list:
        return f"{name} not in the whitelist - action refused"
    else:
        try:
            print(f"Opening {white_list[key]}")
            subprocess.Popen(['open', '-a', white_list[key]])
            return f"Opened {white_list[key]}."
        except Exception as e:
            return f'Cannot open {white_list[key]}: {e}'
        
def open_url(url: str, browser = 'brave'):
    """
    Opens a URL in a whitelisted browser.
    Assumes `url` may come from either:
    1. your known_sites lookup (already a clean, correct URL), or
    2. Ollama constructing it directly from the user's request
    Either way, this function must not trust it blindly.
    """
    browser = (browser or 'brave').lower().strip()
    url = url.lower().strip()
    if browser not in browsers:
        return f"Browser {browser} is not in the whitelist - action refused"
    else:
        if url in known_sites:
            try:
                print(f"Opening {url} on {browsers[browser]}")
                subprocess.Popen(['open', '-a', browsers[browser], known_sites[url]])
                return f"Opened {url} on {browsers[browser]}"
            except Exception as e:
                return f"Can't open {url}: {e}"
        else:
            parse = urlparse(url)
            if not parse.scheme:
                url = 'https://' + url
                parse = urlparse(url)
            check = verified(parse)
            if not check:
                return f'URL is invalid. Cannot open the url'
            else:
                try:
                    print(f"Opening {url} on {browsers[browser]}")
                    subprocess.Popen(['open', '-a', browsers[browser], url])
                    return f"Opened {url} on {browsers[browser]}"
                except Exception as e:
                    return f"Can't open {url}: {e}"

def search_engine(user_text):
    user_text = user_text.lower().strip()
    return open_url(f"https://www.google.com/search?q={user_text}")

def is_app_running(app_name: str) -> bool:
    script = f'application "{app_name}" is running'
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.stdout.strip() == 'true'

def close_app(name: str) -> str:
    key = name.lower().strip()
    if key not in white_list:
        return f"{name} not in whitelist - action refused."
    else:
        if not is_app_running(white_list[key]):
            return f"App {name} is not running right now."
        try:
            print(f"Closing app {name}...")
            subprocess.run(['osascript', '-e', f'quit app "{white_list[key]}"'])
            return f"Closed app {white_list[key]}."
        except Exception as e:
            return f"Can't close app {name}: {e}"

def close_workspace(name:str) -> str:
    key = name.lower().strip()
    if key not in workspaces:
        return f"{name} is not a known workspace - refused."
    summary = ''
    for app in workspaces[key]:
        summary += close_app(app) + ' '
        time.sleep(1.0)
    return summary

def close_url(url: str, browser="brave"):
    browser = (browser or 'brave').lower().strip()
    url = url.lower().strip()
    if browser not in browsers:
        return f"Browser {browser} is not in the whitelist - action refused"
    if url in known_sites:
        domain = urlparse(known_sites[url]).netloc
    else:
        parse = urlparse(url)
        if not parse.scheme:
            url = 'https://' + url
            parse = urlparse(url)
        check = verified(parse)
        if not check:
            return f'URL is invalid. Cannot open the url'
        else:
            try:
                domain = parse.netloc
            except Exception as e:
                return f"Can't close {url}: {e}"
    
    script = f'''
        set targetDomain to "{domain}"
        set closedCount to 0

        try
            tell application "{browsers[browser]}"
                repeat with w in windows
                    repeat with i from (count of tabs of w) to 1 by -1
                        set theTab to tab i of w
                        if URL of theTab contains targetDomain then
                            close theTab
                            set closedCount to closedCount + 1
                        end if
                    end repeat
                end repeat
            end tell
        end try

        return closedCount
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )

        closed = int(result.stdout.strip() or 0)

        if closed == 0:
            return f"No {url} tabs were found."

        return f"Closed {closed} {url} tab(s)."

    except Exception as e:
        return f"Couldn't close {url}: {e}"

def close_webspace(name:str) -> str:
    key = name.lower().strip()
    if key not in webspaces:
        return f"{name} is not a known webspace - refused."
    summary = ''
    for app in webspaces[key]:
        summary += close_url(app) + ' '
        time.sleep(1.0)
    return summary

def verified(parse):
    if parse.scheme not in ['https', 'http']:
        return False
    if not parse.netloc or '.' not in parse.netloc:
        return False
    return True

# SHUTTING DOWN LAPTOP - CAUTIOUS !!!
def laptop_shutdown(confirmed: bool = False) -> str:
    if not confirmed:
        return "CONFIRMATION_REQUIRED: Ask the user to explicitly confirm that the user wants to shut down the computer before shutting down."
    try:
        subprocess.run(['osascript', '-e', 'tell app "System Events" to shut down'])
        return "Shutting down now."
    except Exception as e:
        return f"Failed to shut down: {e}"

# RESTART LAPTOP - CAUTIOUS !!!
def laptop_restart(confirmed: bool = False) -> str:
    if not confirmed:
        return "CONFIRMATION_REQUIRED: Ask the user to explicitly confirm that the user wants to restart the computer before restarting."
    try:
        subprocess.run(['osascript', '-e', 'tell app "System Events" to restart'])
        return "Restarting now."
    except Exception as e:
        return f"Failed to restart: {e}"

