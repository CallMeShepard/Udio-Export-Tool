# Udio Export Tool
**[WAS TESTED ON WINDOWS 11]**

A Python script designed to scrape and download your generated Udio songs. It organizes the downloaded files according to your Udio folder structure and embeds comprehensive metadata and cover art into the MP3 files for archival.

## Disclaimer and Context

This script was developed in the wake of Udio's announcement on October 29, 2025, detailing a historic partnership and a [transition period](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.udio.com%2Fblog%2Fa-new-era). A key change during this transition was the temporary opportunity to download tracks locally within a 48-hour window.

This tool interacts with a third-party service's private API. While the methods used are based on observation of normal web traffic, and the current testing of this application has not resulted in any account issues, bans, or other negative consequences, there is no guarantee that the service provider will not change its policies or technical defenses in the future.

**I'm not responsible for any issues that may arise with your Udio account, including but not limited to temporary suspension, permanent bans, or any other loss or damage, resulting from the use of this software. Use at your own risk.**

## Features

*   **Recursive Folder Traversal:** Scrapes and downloads songs from all custom folders and subfolders defined in your Udio library.
*   **Rich Metadata:** Embeds standard ID3 tags including Title, Artist, Album ("Udio"), Year, and Cover Art.
*   **Full JSON Archival:** Stores the complete, raw API response data for both song details and generation settings within the MP3's `COMMENT` tag for detailed archival.
*   **Precise Timestamps:** Sets the local file's Creation and Modification dates to match the song's original `created_at` timestamp from Udio.
*   **Caching:** Utilizes a local cache file (`data_cache.json`) to store folder lists and song settings, speeding up subsequent runs and minimizing redundant API requests.
*   **Rate Limiting:** Includes a customizable delay between API requests to prevent rate limiting.

## Prerequisites

*   Python 3.13 or newer

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/CallMeShepard/Udio-Export-Tool.git
    cd Udio-Export-Tool
    ```
2.  **Create and activate a virtual environment (Optional, but Recommended):**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Before running the script, you **must** update the authentication data in `config.py`.

1.  Open `config.py`.
2.  Update the placeholder values for `AUTH_TOKEN` (JWT) and `UDIO_COOKIES` with your credentials.

### How to Get Your Udio Credentials

1.  Go to `https://www.udio.com/` and log in with your account.
2.  Open your browser's Developer Tools (F12 or Ctrl+Shift+I).
3.  Go to the **Network** tab.
4.  Navigate to your song library or refresh the page to capture network traffic.
5. **To get `AUTH_TOKEN` (for folder and metadata requests):**
    *   Find a request to the folder list endpoint (`/api/v2/unchartedlabs.dataapi.v1.FolderService/ListFolders`).
    *   In the **Headers** tab, find the `Authorization` request header. Copy the entire JWT token (starts with `eyJ`).
    *   Paste this token into `AUTH_TOKEN` in `config.py`.
6.  **To get `UDIO_COOKIES` (for song list requests):**
    *   Find a request to the folder list endpoint (`/api/v2/unchartedlabs.dataapi.v1.FolderService/ListFolders`).
    *   In the **Headers** tab for that request, find the `Cookie` request header. Copy the entire string (it is typically a very long string of key-value pairs separated by semicolons).
    *   Paste this entire string into `UDIO_COOKIES` in `config.py`.

> **IMPORTANT SECURITY NOTE:** These tokens and cookies are sensitive and will expire over time. If the script fails with a `401 Unauthorized` error, you will need to repeat these steps to get a fresh set of credentials. **Do not share your filled-out `config.py` or commit it to a public repository.**

## Usage

Once configured, run the scraper from the terminal:

```bash
python scraper.py
```

Downloaded files will be saved into the `_Exported` directory (or the path specified by `DOWNLOAD_DIR` in `config.py`), preserving your original Udio folder structure.

## Configuration Options (`config.py`)

The `config.py` file allows you to customize the tool's behavior:

| Setting | Default | Description |
| :--- | :--- | :--- |
| `DOWNLOAD_DIR` | `_Exported` | The local folder where downloaded songs will be saved. |
| `REQUEST_DELAY_SECONDS` | `0.5` | Delay in seconds between API requests. Increasing this value can help prevent rate limiting. |
| `PAGE_SIZE` | `100` | The number of songs/items to fetch per API request (maximum is 100). |
| `MAX_DEPTH` | `None` | Maximum folder depth to traverse. Set to an integer (e.g., `2`) or leave as `None` for unlimited depth. |
| `DOWNLOAD_LIMIT` | `None` | Set to an integer to limit the total number of songs to download, or leave as `None` to download all found songs. |
