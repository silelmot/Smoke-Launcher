import base64
import requests
import configparser
import os
import json
from platformdirs import *
import logging
import sqlite3
import time
import functools
import keyring
import customtkinter
import patoolib
from pathlib import Path

#___________Main Settings___________
appname = 'Smoke Launcher'
settings_file_name = 'settings.ini'
settings_location = user_data_dir(appname)
settings_file = os.path.join(settings_location, settings_file_name)




# Ensure settings directory exists
os.makedirs(settings_location, exist_ok=True)

# Check if settings file exists
if not os.path.exists(settings_file):
    # Create ConfigParser instance
    config = configparser.ConfigParser()

    # Set default values
    config['SETTINGS'] = {
        'username': '',
        'install_location': '',
        'url': '',
        'apperance': 'System',
        'theme': 'blue',
        'debug': 'False'
    }

    # Write the default configuration to the file
    with open(settings_file, 'w') as configfile:
        config.write(configfile)
else:
    # Read configuration from file
    config = configparser.ConfigParser()
    config.read(settings_file)

if config['SETTINGS'].get('debug') == 'True':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)

# Get values from config
username = config['SETTINGS'].get('username')
install_location = config['SETTINGS'].get('install_location')
url = config['SETTINGS'].get('url')



CACHE_DIR = f"{settings_location}/cache"
CACHE_FILE = f"{CACHE_DIR}/cached_games.json"  # This is all the games in one file
os.makedirs(settings_location, exist_ok=True)

# Define the path for the SQLite database file
DB_PATH = os.path.join(CACHE_DIR, "cache.db")
# Cache Expiry Time (in seconds)
CACHE_EXPIRY_TIME = 60 * 60  # 1 hour


def is_online():
    try:
        response = requests.get(url)
        if response.status_code == 200:
            logging.debug("ONLINE")
            return True
    except Exception:
        logging.debug("OFFLINE")
        return False
    
online_status = is_online()



#___________END Main Settings___________

def fetch_game_info(username, password, gid):
    # Check if the response is already in the cache and if it's expired
    cached_data = load_cache(gid)
    if cached_data:
        # Check if cache is expired
        if is_cache_expired(cached_data['timestamp']):
            print(f"Cache for game {gid} expired, fetching new data...")
        else:
            print(f"Fetching game info from cache...{gid}")
            return cached_data['data']

    # If no valid cache, fetch new data
    encoded_credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    url = f"{config['SETTINGS'].get('url')}/api/games/{gid}"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Basic {encoded_credentials}'
    }
    params = {}

    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        # Cache the response
        save_cache(gid, data)
        return data
    else:
        print("Failed to fetch game info. Status code:", response.status_code)
        return None

# Function to initialize the database and create the cache table if it doesn't exist
def init_db():
    # Ensure the directory for the database exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # Create the database and the cache table if they don't exist
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                gid TEXT PRIMARY KEY,
                data TEXT,
                timestamp INTEGER
            )
        ''')
        conn.commit()

# Function to save cache data to the SQLite database
def save_cache(gid, data):
    init_db()  # Ensure the database is initialized
    timestamp = int(time.time())  # Current timestamp in seconds
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO cache (gid, data, timestamp) VALUES (?, ?, ?)
        ''', (gid, json.dumps(data), timestamp))
        conn.commit()

# Function to load cache data from the SQLite database
def load_cache(gid):
    init_db()  # Ensure the database is initialized
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data, timestamp FROM cache WHERE gid = ?', (gid,))
        result = cursor.fetchone()
        if result:
            data, timestamp = result
            return {'data': json.loads(data), 'timestamp': timestamp}
        return None

# Function to check if the cached data has expired
def is_cache_expired(timestamp):
    current_time = int(time.time())
    return current_time - timestamp > CACHE_EXPIRY_TIME


def check_url_health(passedurl):
    try:
        response = requests.get(f'{passedurl}/api/health')
        if response.status_code == 200:
            logging.debug("CODE 200 on url health check")
            json_data = response.json()
            if "status" in json_data and json_data["status"] == "HEALTHY":
                return True
    except Exception as e:
        logging.debug(f"An error occurred: {e}")
    
    return False

def check_config(config_file):
    print(f"Checking config file: {config_file}")
    config = configparser.ConfigParser()
    config.read(config_file)
    if config['SETTINGS'].get('url') == "":
        logging.debug("URL not found in config")
        return False
    if config['SETTINGS'].get('username') == "":
        logging.debug("Username not found in config")
        return False
    if config['SETTINGS'].get('install_location') == "":
        logging.debug("Install location not found in config")
        return False
    return True




def fetch_game_titles(username, password, online_status=True):
    gid = "game_titles"
    cached_data = load_cache(gid)
    
    encoded_credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    
    if cached_data:
        logging.debug("GV Client Online. Using cached game titles.")
    
    if not online_status:
        logging.debug("GV Client Offline. Using cached game titles.")
        return cached_data
    
    # API Call
    headers = {'accept': 'application/json', 'Authorization': f'Basic {encoded_credentials}'}
    params = {'sortBy': 'title:ASC'}
    try:
        response = requests.get(config["SETTINGS"].get("url") + "/api/games", params=params, headers=headers)
        response.raise_for_status()  # Raise an exception for non-200 status codes
        data = response.json().get('data', [])
        if data != cached_data:
            save_cache(gid, data)
            logging.debug("Cached game titles updated.")
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch game titles: {e}")
        return cached_data
    
# def download_file(url, file_path,auth):
#     dl = Pypdl(auth=auth)
#     dl.start(url, file_path=file_path, segments=10, display=True, multisegment=True, block=False, retries=0, overwrite=False)


# # def download_game_files(username, password, gid):
#     game_info = fetch_game_info(username, password, gid)
#     if not game_info:
#         logging.error("Failed to fetch game information.")
#         return
#     auth = aiohttp.BasicAuth(username, password)
#     download_url = config["SETTINGS"].get("url") + f"/api/games/{gid}/download"
#     game_name = game_info['title']
#     install_location = config['SETTINGS'].get('install_location')
#     download_path = os.path.join(install_location, f"Downloads/({gid}){game_name}.zip")

#     # Create the download directory if it doesn't exist
#     os.makedirs(os.path.dirname(download_path), exist_ok=True)

#     # Download the file using pypdl
#     download_file(download_url, download_path,auth)

def is_game_downloaded(gid):
    install_location = config['SETTINGS'].get('install_location')
    game_name = fetch_game_info(username,keyring.get_password("Smoke-Launcher", username) ,gid)['title']
    download_path = os.path.join(install_location, f"Downloads/({gid}){game_name}.zip")
    return os.path.exists(download_path)

def unpack_game(gid):
    install_location = config['SETTINGS'].get('install_location')
    game_name = fetch_game_info(username,keyring.get_password("Smoke-Launcher", username) ,gid)['title']
    filetype = fetch_game_info(username,keyring.get_password("Smoke-Launcher", username) ,gid)['file_path'].split(".")[-1]
    download_path = os.path.join(install_location, f"Downloads/({gid}){game_name}.{filetype}")
    extract_path = os.path.join(install_location, f"Installations/({gid}){game_name}/Files")
    os.makedirs(extract_path, exist_ok=True)
    patoolib.extract_archive(download_path, outdir=extract_path)
    file_path = Path(install_location) / f"Installations/({gid}){game_name}" / "gamevault-exec"
    file_path.touch()
    return True

def is_game_installed(gid):
    install_location = config['SETTINGS'].get('install_location')
    game_name = fetch_game_info(username,keyring.get_password("Smoke-Launcher", username) ,gid)['title']
    extract_path = os.path.join(install_location, f"Installations/({gid}){game_name}")
    return os.path.exists(extract_path)




