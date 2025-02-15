import threading
import yaml
import os
import time
from colorama import Fore, Style, init
from datetime import datetime
from curl_cffi import requests as request

init()

# Load configuration
with open("config.yml", "r") as file:
    config = yaml.safe_load(file)

def timestamp():
    return datetime.utcnow().strftime("%H:%M:%S")  # Format as HH MM SS

def success(content):
    print(f"{Fore.LIGHTBLACK_EX}{timestamp()} {Fore.LIGHTGREEN_EX}SUCCESS {Fore.WHITE}>{Fore.LIGHTBLACK_EX} {content}{Style.RESET_ALL}")

def error(content):
    print(f"{Fore.LIGHTBLACK_EX}{timestamp()} {Fore.LIGHTRED_EX}ERROR {Fore.WHITE}>{Fore.LIGHTBLACK_EX} {content}{Style.RESET_ALL}")

def warn(content):
    print(f"{Fore.LIGHTBLACK_EX}{timestamp()} {Fore.LIGHTYELLOW_EX}WARN {Fore.WHITE}>{Fore.LIGHTBLACK_EX} {content}{Style.RESET_ALL}")

def inp(prompt):
    return input(f"{Fore.LIGHTBLACK_EX}{timestamp()} {Fore.LIGHTMAGENTA_EX}INPUT {Fore.WHITE}>{Fore.LIGHTBLACK_EX} {prompt}{Style.RESET_ALL} ")

def solver(api_key: str, sitekey: str, proxy: str, rqdata: str):
    payload = {
        'key': api_key,
        'type': "hcaptcha_enterprise",
        'data': {
            'sitekey': sitekey, 
            'siteurl': "discord.com", 
            'proxy': f"http://{proxy}", 
            'rqdata': rqdata
        }
    }
    
    # Step 1: Create the Captcha Task
    post_solver = request.post(
        url="https://api.razorcap.xyz/create_task",
        json=payload
    )

    if post_solver.status_code != 200:
        error("Failed To Create Task")
        return None

    sigma = post_solver.json()
    taskid = sigma.get('task_id')
    if not taskid:
        error("Task ID not received")
        return None

    success(f"Task Created: {taskid}")

    # Step 2: Poll Until Solved
    while True:
        get_taskinfo = request.get(
            url=f"https://api.razorcap.xyz/get_result/{taskid}"
        )

        if get_taskinfo.status_code != 200:
            error("❌ Failed to get task result")
            return None

        taskinfojson = get_taskinfo.json()
        status = taskinfojson.get('status')

        if status == "solving":
            time.sleep(5)  # Wait 5 seconds before checking again
            continue
        elif status == "solved":
            response_key = taskinfojson.get('response_key')
            success("Captcha Solved!")
            return response_key
        else:
            error(f"Unexpected status: {status}")
            return None

chrome_version = "133"

def bot_add(token, guild_id, bot_id):
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": token,
        "priority": "u=1, i",
        "referer": "https://discord.com/channels",
        "sec-ch-ua": f'"Not)A;Brand";v="99", "Microsoft Edge";v="{chrome_version}", "Chromium";v="{chrome_version}"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-discord-timezone": "Asia/Katmandu",
    }
    payload = {
        "guild_id": guild_id,
        "permissions": "8",
        "authorize": True,
        "integration_type": 0
    }

    response = request.post(
        url=f"https://discord.com/api/v9/oauth2/authorize?client_id={bot_id}&scope=bot%20applications.commands",
        headers=headers,
        json=payload,
        impersonate="chrome"
    )
    
    if response.status_code == 200:
        success(f"Successfully added bot {bot_id} to server {guild_id}")
    elif response.status_code == 400:
        warn("Captcha Encountered")
        captcha_data = response.json()
        response_key = solver(config["api_key"], captcha_data["captcha_sitekey"], config["proxy"], captcha_data["captcha_rqdata"])
        
        if response_key:
            headers["x-captcha-key"] = response_key
            headers["x-captcha-rqtoken"] = captcha_data["captcha_rqtoken"]
            response13 = request.post(
                url=f"https://discord.com/api/v9/oauth2/authorize?client_id={bot_id}&scope=bot%20applications.commands",
                headers=headers,
                json=payload,
                impersonate="chrome"
            )
            if response13.status_code == 200:
                success(f"Successfully added bot {bot_id} to server {guild_id} | Captcha Involved")
            else:
                error(f"Something Went Wrong : {response13.text}")
    else:
        error(f"Something Went Wrong : {response.text}")

def worker(token, guild_id, bot_ids, thread_id):
    """Thread function to process multiple bot additions."""
    for bot_id in bot_ids:
        bot_add(token, guild_id, bot_id)
        time.sleep(2)  # Short delay to prevent rate limits

def main():
    os.system("cls")
    token = config["token"]
    guild_id = inp("Enter the Server ID where you want to add bots: ")

    if not os.path.exists("botid.txt"):
        error("❌ botid.txt file not found!")
        return

    with open("botid.txt", "r") as file:
        bot_ids = [line.strip() for line in file if line.strip()]

    bot_count = int(inp(f"Enter how many bots to add (max {len(bot_ids)}): "))
    
    if bot_count > len(bot_ids):
        error("❌ Not enough bot IDs in botid.txt")
        return

    thread_count = config["threads"]

    
    chunk_size = (bot_count + thread_count - 1) // thread_count  
    threads = []

    for i in range(thread_count):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, bot_count)
        if start >= bot_count:
            break  

        thread = threading.Thread(target=worker, args=(token, guild_id, bot_ids[start:end], i + 1))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
