import requests
import json
import os
import re
import time
import logging
from datetime import datetime
from config import get_auth_headers, DOWNLOAD_DIR, PAGE_SIZE, MAX_DEPTH, DOWNLOAD_LIMIT, SONG_LIST_API_TEMPLATE, FOLDER_LIST_API_URL, REQUEST_DELAY_SECONDS, SONG_SETTINGS_API_TEMPLATE
from metadata import apply_metadata, set_file_creation_time_precise, parse_iso_date

#GLOBAL STATE
class Stats:
    total_songs_found, total_folders_found, total_files_downloaded = 0, 0, 0

class Cache:
    CACHE_FILE = "data_cache.json"
    data = {"songs": {}, "folders": {}}

#LOGGING SETUP
log_filename = os.path.join("logs", datetime.now().strftime("%Y%m%d_%H%M%S.log"))
os.makedirs("logs", exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(log_filename, mode='w', encoding='utf-8'), logging.StreamHandler()])

#CACHE MANAGEMENT

def load_cache():
    if os.path.exists(Cache.CACHE_FILE):
        try:
            with open(Cache.CACHE_FILE, 'r', encoding='utf-8') as f:
                Cache.data = json.load(f)
            logging.info("Cache loaded successfully.")
        except Exception as e:
            logging.warning(f"Failed to load cache: {e}. Starting fresh.")

def save_cache():
    try:
        with open(Cache.CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(Cache.data, f, indent=2, ensure_ascii=False)
        logging.info("Cache saved successfully.")
    except Exception as e:
        logging.error(f"Failed to save cache: {e}")

#NETWORK FUNCTIONS

def download_file(url, destination_path, headers, is_metadata_request=False):
    if is_metadata_request:
        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            return response
        except Exception as e:
            raise Exception(f"Failed metadata request: {e}")
    
    logging.info(f"    - Downloading: {url}")
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        with open(destination_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        return True
    except Exception as e:
        logging.error(f"    - [Error] Failed to download file: {e}")
        return False

def get_song_settings(song_id, headers):
    if song_id in Cache.data["songs"].get(song_id, {}).get("settings", {}):
        return Cache.data["songs"][song_id]["settings"]
        
    url = SONG_SETTINGS_API_TEMPLATE.format(song_id)
    logging.info(f"    - Requesting full metadata...")
    try:
        time.sleep(REQUEST_DELAY_SECONDS)
        response = download_file(url, None, headers, is_metadata_request=True)
        settings = response.json()
        
        if song_id not in Cache.data["songs"]:
            Cache.data["songs"][song_id] = {}
        Cache.data["songs"][song_id]["settings"] = settings
        save_cache()

        return settings
    except Exception as e:
        logging.warning(f"    - Failed to get full metadata: {e}")
        return None

def fetch_songs_in_folder(folder_id="", headers_for_songs=None):
    all_songs, offset = [], 0
    folder_name = "root directory" if not folder_id else f"folder {folder_id}"
    logging.info(f"Starting to fetch songs from {folder_name}...")
    while True:
        url = SONG_LIST_API_TEMPLATE.format(PAGE_SIZE, offset, folder_id)
        try:
            logging.info(f"  Requesting songs (offset: {offset})...")
            time.sleep(REQUEST_DELAY_SECONDS)
            response = requests.get(url, headers=headers_for_songs, timeout=20)
            if response.status_code == 401:
                logging.critical("Code 401: Unauthorized. Your COOKIES are stale.")
                logging.critical(">>> Please update the UDIO_COOKIES variable in config.py")
                return []
            response.raise_for_status()
            songs_on_page = response.json().get('data', [])
            
            for song in songs_on_page:
                Cache.data["songs"][song["id"]] = song
            
            if songs_on_page: all_songs.extend(songs_on_page)
            if not songs_on_page or len(songs_on_page) < PAGE_SIZE: break
            offset += PAGE_SIZE
        except Exception as e:
            logging.error(f"  An error occurred while fetching songs: {e}")
            break
    logging.info(f"  Found {len(all_songs)} songs in this folder.")
    return all_songs

def fetch_folders_in_folder(parent_folder_id=None, headers_for_folders=None):
    logging.info(f"  Searching for subfolders (parent: {parent_folder_id or 'root'})...")
    
    cache_key = parent_folder_id if parent_folder_id else "root"
    if cache_key in Cache.data["folders"]:
        return Cache.data["folders"][cache_key]

    payload = {"filter": {"depth": {"start": 1, "end": 1}}, "pageSize": 500}
    if parent_folder_id:
        payload["filter"]["parentId"] = parent_folder_id
    try:
        time.sleep(REQUEST_DELAY_SECONDS)
        response = requests.post(FOLDER_LIST_API_URL, headers=headers_for_folders, data=json.dumps(payload), timeout=20)
        if response.status_code == 401:
            logging.critical("Code 401: Unauthorized. Your AUTH_TOKEN is stale.")
            logging.critical(">>> Please update the AUTH_TOKEN variable in config.py")
            return []
        response.raise_for_status()
        folders = response.json().get('folders', [])
        
        Cache.data["folders"][cache_key] = folders
        save_cache()

        logging.info(f"  Found {len(folders)} subfolders.")
        return folders
    except Exception as e:
        logging.error(f"  An error occurred while searching for subfolders: {e}")
        return []

#FLOW CONTROL AND RECURSION

def process_song(song_data, current_path, headers_for_songs):
    if DOWNLOAD_LIMIT is not None and Stats.total_files_downloaded >= DOWNLOAD_LIMIT: return True
    
    title, song_id = song_data.get('title', 'Untitled'), song_data.get('id')
    logging.info(f"\n--- Processing Song: {title} (ID: {song_id}) ---")
    
    unique_suffix = song_id.split('-')[-1]
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    unique_filename = f"{safe_title} [{unique_suffix}_ID].mp3"
    mp3_filepath = os.path.join(current_path, unique_filename)

    if os.path.exists(mp3_filepath):
        logging.info(f"   -> File '{unique_filename}' already exists. Skipping.")
        return False
        
    audio_url = song_data.get('song_path')
    if not audio_url or not download_file(audio_url, mp3_filepath, headers_for_songs): return False
    
    settings_data = get_song_settings(song_id, headers_for_songs)
    
    apply_metadata(mp3_filepath, song_data, settings_data, download_file, DOWNLOAD_DIR) 

    created_at_str = song_data.get('created_at')
    if created_at_str:
        dt_object = parse_iso_date(created_at_str)
        if dt_object:
            set_file_creation_time_precise(mp3_filepath, dt_object)

    Stats.total_files_downloaded += 1
    if DOWNLOAD_LIMIT is not None:
        logging.info(f"   -> Successfully downloaded. Total: {Stats.total_files_downloaded}/{DOWNLOAD_LIMIT}")
    else:
        logging.info(f"   -> Successfully downloaded. Total: {Stats.total_files_downloaded}")
    
    return DOWNLOAD_LIMIT is not None and Stats.total_files_downloaded >= DOWNLOAD_LIMIT

def process_directory(parent_folder_id=None, current_path=DOWNLOAD_DIR, depth=0, headers_for_songs=None, headers_for_folders=None):
    indent = "  " * depth
    logging.info(f"\n{indent}--- Analyzing Folder: '{os.path.basename(current_path)}' ---")
    
    if MAX_DEPTH is not None and depth > MAX_DEPTH:
        logging.warning(f"{indent}[!] Max depth ({MAX_DEPTH}) reached. Stopping traversal.")
        return False

    songs = fetch_songs_in_folder(parent_folder_id or "", headers_for_songs)
    Stats.total_songs_found += len(songs)
    for song in songs:
        if process_song(song, current_path, headers_for_songs):
            logging.info("Download limit reached. Shutting down.")
            return True

    subfolders = fetch_folders_in_folder(parent_folder_id, headers_for_folders)
    Stats.total_folders_found += len(subfolders)
    for folder in subfolders:
        folder_name, folder_id = folder.get('name'), folder.get('id')
        safe_folder_name = re.sub(r'[\\/*?:"<>|]', "", folder_name)
        new_path = os.path.join(current_path, safe_folder_name)
        try: os.makedirs(new_path, exist_ok=True)
        except OSError as e:
            logging.error(f"Failed to create directory '{new_path}': {e}")
            continue
        
        logging.info(f"\n{indent}>>> Entering Folder: {folder_name} <<<")
        if process_directory(folder_id, new_path, depth + 1, headers_for_songs, headers_for_folders):
            return True
        logging.info(f"\n{indent}<<< Exiting Folder: {folder_name} >>>")
    return False

def main():
    logging.info("--- Starting Exporter (v1.0) ---")
    
    try:
        load_cache()
        headers_for_songs, headers_for_folders = get_auth_headers()
        logging.info("Authorization data loaded successfully.")
    except ValueError as e:
        logging.critical(e)
        return
    except Exception as e:
        logging.critical(f"An unexpected error occurred during startup: {e}")
        return
    
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    try:
        process_directory(
            parent_folder_id=None, 
            current_path=DOWNLOAD_DIR,
            headers_for_songs=headers_for_songs,
            headers_for_folders=headers_for_folders
        )
    except KeyboardInterrupt:
        logging.warning("\n\nOperation manually interrupted by user (Ctrl+C). Saving progress...")
    
    save_cache()
    
    logging.info("\n\n" + "="*50)
    logging.info("--- FINAL STATISTICS ---")
    logging.info(f"Total folders found: {Stats.total_folders_found}")
    logging.info(f"Total songs found: {Stats.total_songs_found}")
    logging.info(f"Total files downloaded: {Stats.total_files_downloaded}")
    logging.info("="*50)
    logging.info("\n--- Operation Complete! ---")

if __name__ == "__main__":
    main()