#AUTHENTICATION DATA (REQUIRED)

#JWT Token (for folder requests)
AUTH_TOKEN = "token"

#Cookies string (for song list requests)
UDIO_COOKIES = """cookies"""

#EXPORTER SETTINGS
DOWNLOAD_DIR = "_Exported"
REQUEST_DELAY_SECONDS = 0.5     #delay in seconds between API requests [don't set too small]
PAGE_SIZE = 100                 #number of songs/items to fetch per API request (1-100)
MAX_DEPTH = None                #maximum folder depth to traverse. Set to an integer (e.g., 2) or None for unlimited depth
DOWNLOAD_LIMIT = None           #set to an integer to limit the total number of songs to download, or None to download all

#API CONSTANTS
SONG_LIST_API_TEMPLATE = "https://www.udio.com/api/songs/me?likedOnly=false&publishedOnly=false&includeDisliked=true&onlyTrees=false&searchTerm=&sort=created_at&readOnly=true&pageSize={}&pageParam={}&inFolder={}"
FOLDER_LIST_API_URL = "https://www.udio.com/api/v2/unchartedlabs.dataapi.v1.FolderService/ListFolders"
SONG_SETTINGS_API_TEMPLATE = "https://www.udio.com/api/songs/{}/settings"

def get_auth_headers():
    if AUTH_TOKEN == "token" or UDIO_COOKIES == "cookies":
        raise ValueError("AUTH_TOKEN or UDIO_COOKIES have not been updated in config.py")

    headers_for_songs = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json, text/plain, */*',
        'Cookie': UDIO_COOKIES
    }
    
    headers_for_folders = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': '*/*',
        'Authorization': AUTH_TOKEN,
        'Content-Type': 'application/json',
        'connect-protocol-version': '1'
    }
    
    return headers_for_songs, headers_for_folders