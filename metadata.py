import json
import os
import io
import logging
from datetime import datetime, timezone
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, COMM, TDRC
from PIL import Image
from filedate import File
from config import REQUEST_DELAY_SECONDS, SONG_SETTINGS_API_TEMPLATE

class MetadataGlobals:
    DOWNLOAD_DIR = ""
    DOWNLOAD_FILE_FUNC = None

def parse_iso_date(date_str):
    try:
        if date_str.endswith('Z'):
            dt_object = datetime.fromisoformat(date_str[:-1]).replace(tzinfo=timezone.utc)
        else:
            dt_object = datetime.fromisoformat(date_str)
            if dt_object.tzinfo is None or dt_object.tzinfo.utcoffset(dt_object) is None:
                dt_object = dt_object.replace(tzinfo=timezone.utc)
        return dt_object
    except Exception as e:
        logging.warning(f"  [Error] Failed to parse date '{date_str}': {e}")
        return None

def set_file_creation_time_precise(filepath, dt_object):
    try:
        file = File(filepath)
        file.set(
            created=dt_object, 
            modified=dt_object, 
            accessed=dt_object
        ) 
        logging.info(f"    - Set file Creation/Modification Date: {dt_object.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    except Exception as e:
        logging.warning(f"    - [Error] Failed to set file time: {e}")
        logging.warning("    - For precise date setting, ensure filedate is installed: pip install filedate")

def apply_metadata(mp3_path, song_data, settings_data, download_file_func, download_dir):
    MetadataGlobals.DOWNLOAD_FILE_FUNC = download_file_func
    MetadataGlobals.DOWNLOAD_DIR = download_dir
    logging.info("    - Applying metadata...")
    
    image_url, image_data = song_data.get('image_path'), None
    if image_url:
        temp_image_path = os.path.join(download_dir, "temp_cover.jpg")
        if download_file_func(image_url, temp_image_path, {}):
            try:
                with Image.open(temp_image_path) as img:
                    output_buffer = io.BytesIO()
                    if img.mode == 'RGBA': img = img.convert('RGB')
                    img.save(output_buffer, format='JPEG')
                    image_data = output_buffer.getvalue()
                os.remove(temp_image_path)
            except Exception as e: logging.error(f"    - [Error] Failed to convert cover art: {e}")
    
    try:
        audio = MP3(mp3_path)
        audio.delete()
        audio.tags = ID3()

        if image_data: audio.tags.add(APIC(encoding=0, mime='image/jpeg', type=3, desc='', data=image_data))
        
        audio.tags.add(TIT2(encoding=3, text=song_data.get('title', '')))
        audio.tags.add(TPE1(encoding=3, text=song_data.get('artist', '')))
        audio.tags.add(TALB(encoding=3, text="Udio"))
        
        year_str = ""
        created_at_str = song_data.get('created_at')
        if created_at_str:
            try:
                dt_object = parse_iso_date(created_at_str)
                year_str = dt_object.strftime('%Y')
                audio.tags.add(TDRC(encoding=3, text=year_str))
            except: pass
        
        export_info_data = {"exporter": "Udio-Export-Tool", "export_date": datetime.utcnow().isoformat() + "Z", "version": "1.0", "github": "https://github.com/CallMeShepard/Udio-Export-Tool","comment": "This JSON contains all available metadata exported from Udio's API."}
        
        unified_comment_data = {
            "ExportedData": {
                "song_details": song_data,
                "generation_settings": settings_data,
                "_export_info": export_info_data
            }
        }
        comment_text = json.dumps(unified_comment_data, indent=2, ensure_ascii=False)
        
        audio.tags.add(COMM(encoding=3, lang='XXX', desc='', text=comment_text))
        
        audio.save(v2_version=3)
        logging.info("    - ID3v2 tags successfully applied.")
        
    except Exception as e:
        logging.error(f"    - [Critical Error] Failed to write metadata: {e}", exc_info=True)