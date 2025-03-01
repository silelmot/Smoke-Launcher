import base64
import requests
import configparser
import os
import json
from platformdirs import *
import logging
import sqlite3
import time
import keyring
import patoolib
from pathlib import Path
import subprocess
import shutil
import os
import base64
import requests
from io import BytesIO
from PIL import Image
import logging


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
USERNAME = config['SETTINGS'].get('username')
PASSWORD = keyring.get_password("Smoke-Launcher", USERNAME)

install_location = config['SETTINGS'].get('install_location')
url = config['SETTINGS'].get('url')



CACHE_DIR = f"{settings_location}/cache"
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


def is_game_downloaded(gid):
    install_location = config['SETTINGS'].get('install_location')
    game_name = fetch_game_info(USERNAME,PASSWORD,gid)['title']
    download_path = os.path.join(install_location, f"Downloads/({gid}){game_name}.zip")
    return os.path.exists(download_path)

def unpack_game(gid):
    """Handles unpacking without UI updates inside."""
    install_location = config['SETTINGS'].get('install_location')
    game_name = fetch_game_info(USERNAME, PASSWORD, gid)['title']
    filetype = fetch_game_info(USERNAME, PASSWORD, gid)['file_path'].split(".")[-1]
    
    download_path = os.path.join(install_location, f"Downloads/({gid}){game_name}.{filetype}")
    extract_path = os.path.join(install_location, f"Installations/({gid}){game_name}/Files")
    os.makedirs(extract_path, exist_ok=True)

    # Extract in a blocking manner, but since it's in a thread, it won't freeze the UI
    patoolib.extract_archive(download_path, outdir=extract_path)

    # Create the gamevault-exec file after extraction
    file_path = Path(install_location) / f"Installations/({gid}){game_name}" / "gamevault-exec"
    file_path.touch()

    return True

def is_game_installed(gid):
    install_location = config['SETTINGS'].get('install_location')
    game_name = fetch_game_info(USERNAME,PASSWORD ,gid)['title']
    extract_path = os.path.join(install_location, f"Installations/({gid}){game_name}")
    return os.path.exists(extract_path)

def uninstall_game(gid):
    """Removes the game installation directory in a cross-platform way."""
    install_location = config['SETTINGS'].get('install_location')
    game_name = fetch_game_info(USERNAME, PASSWORD, gid)['title']
    extract_path = os.path.join(install_location, f"Installations/({gid}){game_name}")

    try:
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)  # Cross-platform directory deletion
        return True
    except Exception as e:
        print(f"Error uninstalling game {game_name}: {e}")
        return False

def get_exes(gid):
    foldername = fetch_game_info("NULL", "NULL", gid)  # Assuming fetch_game_info exists and returns a dictionary
    game_name = foldername['title']
    installfolder = config['SETTINGS'].get('install_location')
    destination = f"{installfolder}/Installations/({gid}){game_name}/"

    # List of executable names to ignore (with .exe appended)
    ignore_base_names = [
        "arc", "autorun", "bssndrpt", "crashpad_handler", "crashreportclient", 
        "crashreportserver", "dxdiag", "dxsetup", "dxwebsetup", "dxwebsetupinstaller", 
        "installationkit", "installationmanager", "installationscript", "installationwizard", 
        "installer", "installerassistant", "installersetup", "installerupdater", "installfile", 
        "installscript", "installwizard", "notification_helper", "oalinst", "patcher", 
        "patchinstaller", "patchmanager", "patchscript", "patchsetup", "patchupdater", 
        "python", "pythonw", "quicksfv", "quickuninstall", "sendrpt", "setup", 
        "setupassistant", "setupconfig", "setupfile", "setupinstaller", "setupkit", 
        "setupmanager", "setupscript", "setuputility", "setupwizard", "skidrow", 
        "smartsteaminstaller", "smartsteamloader_x32", "smartsteamloader_x64", 
        "smartsteamuninstaller", "ubisoftgamelauncherinstaller", "ue4prereqsetup_x64", 
        "unarc", "unins000", "unins001","unins002", "uninst", "uninstall", "uninstallagent", 
        "uninstallapplication", "uninstalldriver", "uninstaller", "uninstallerassistant", 
        "uninstallhandler", "uninstallhelper", "uninstallmanager", "uninstallprogram", 
        "uninstallscript", "uninstallservice", "uninstalltool", "uninstalltoolkit", 
        "uninstallupdater", "uninstallutility", "uninstallwizard", "unitycrashhandler", 
        "unitycrashhandler32", "unitycrashhandler64", "unrealcefsubprocess", "vc_redist.x64", 
        "vc_redist.x86", "vcredist_x64", "vcredist_x642", "vcredist_x643", "vcredist_x86", 
        "vcredist_x862", "vcredist_x863", "vcredist_x86_2008", "verify", "VC_redist.x86",
        "VC_redist.x64","DXSETUP","gfwlivesetup","GfWLPKSetter"
    ]
    ignore_list = {f"{name}.exe" for name in ignore_base_names}

    exes = []
    for root, dirs, files in os.walk(destination):
        for filename in files:
            if filename.endswith(".exe") and filename not in ignore_list:
                exes.append(os.path.join(root, filename))  # Include full path to the exe file
    return exes

def delete_download(gid):
    install_location = config['SETTINGS'].get('install_location')
    game_name = fetch_game_info(USERNAME,PASSWORD ,gid)['title']
    filetype = fetch_game_info(USERNAME, PASSWORD, gid)['file_path'].split(".")[-1]
    download_path = os.path.join(install_location, f"Downloads/({gid}){game_name}.{filetype}")
    os.remove(download_path)


import requests

import requests
from requests.auth import HTTPBasicAuth

import os
import requests
from requests.auth import HTTPBasicAuth

def get_box_art(gid):
    # Fetch the game info to get the image metadata
    game_info = fetch_game_info(USERNAME, PASSWORD, gid)
    
    # Extract the image name and ID
    image_name = game_info['provider_metadata'][0]['cover']['file_path'].split('/')[-1]
    image_id = game_info['provider_metadata'][0]['cover']['id']
    
    print(image_name)
    print(image_id)
    
    # Define the cache directory and create subdirectories if they don't exist
    CACHE_DIR = f"{settings_location}/cache"
    image_dir = CACHE_DIR  # Create a directory for the specific GID
    os.makedirs(image_dir, exist_ok=True)  # Make sure the directory exists
    
    # Define the full path for saving the image (with extension)
    image_path = os.path.join(image_dir, image_name)
    
    # Check if the image already exists in the cache
    if os.path.exists(image_path):
        print(f"Image already exists at {image_path}")
        return image_path
    
    # Prepare the URL and headers for fetching the image
    url = f"{config['SETTINGS'].get('url')}/api/media/{image_id}"  # Adjust endpoint to match API documentation
    headers = {'accept': 'image/*'}  # Accept header changed to image/*
    
    # Make the GET request to fetch the image with basic auth
    response = requests.get(url, headers=headers, auth=HTTPBasicAuth(USERNAME, PASSWORD))
    
    if response.status_code == 200:
        # Save the image to the specified location
        with open(image_path, 'wb') as img_file:
            img_file.write(response.content)
        print(f"Image saved as {image_path}")
        return image_path
    else:
        print(f"Failed to fetch image. Status code: {response.status_code}")
    
def get_selected_exe(gid):
    install_location = config['SETTINGS'].get('install_location')
    game_name = fetch_game_info(USERNAME, PASSWORD, gid)['title']
    extract_path = os.path.join(install_location, f"Installations/({gid}){game_name}")
    filename = os.path.join(extract_path, "gamevault-exec")

    if os.path.exists(filename):
        with open(filename, "r") as file:
            content = file.read()
            # Split the content into lines and look for the Executable key
            for line in content.splitlines():
                if line.startswith('Executable='):
                    return line.split('=')[1].strip()

        
print(get_selected_exe("1"))