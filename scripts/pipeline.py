#!/usr/bin/env python3

import os
import json
import time
import logging
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pyvirtualdisplay import Display
import pyautogui

# === CONFIGURATION ===
BASE_DIR = os.path.expanduser("~/FantasyAI")
SCRIPT_DIR = os.path.join(BASE_DIR, "scripts")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)

OLLAMA_URL = "http://localhost:11434/api/generate"
GOOGLE_VEO_URL = "https://veo.google/"
CAPCUT_TEMPLATE_ID = "YOUR_CAPCUT_TEMPLATE_ID"
SERVICE_ACCOUNT_FILE = os.path.join(SCRIPT_DIR, "service-account.json")
TIKTOK_CREDS_FILE = os.path.join(SCRIPT_DIR, "tiktok_creds.json")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "pipeline.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === TREND ANALYSIS ===
def fetch_trends():
    logger.info("📊 Fetching trends...")
    # In production: connect to real API (TikTok/YouTube Trends)
    return [
        "Dancing Videos", "TikTok Duets", "ASMR", 
        "AI Art Challenges", "Viral Animal Videos"
    ]

def cluster_trends(trends):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    
    logger.info("🧠 Clustering trends...")
    vectorizer = TfidfVectorizer(stop_words='english')
    X = vectorizer.fit_transform(trends)
    kmeans = KMeans(n_clusters=3, random_state=0, n_init=10)
    kmeans.fit(X)
    return trends[kmeans.labels_[0]]

# === PROMPT GENERATION ===
def generate_prompt(trend):
    logger.info(f"🎬 Generating prompt for: {trend}")
    payload = {
        "model": "mistral",
        "prompt": f"Create an 8-second viral TikTok video about {trend}. Include: "
                  "1. Vertical format (9:16) 2. Trending audio 3. Text overlays "
                  "4. Quick cuts 5. Surprise ending",
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception as e:
        logger.error(f"Prompt generation failed: {e}")
        raise

# === VIDEO GENERATION ===
def generate_veo_video(prompt):
    logger.info("🎥 Generating video with Google Veo...")
    
    # Start virtual display for headless environments
    display = Display(visible=0, size=(1920, 1080))
    display.start()
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Configure download directory
    prefs = {
        "download.default_directory": OUTPUT_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    try:
        driver.get(GOOGLE_VEO_URL)
        
        # Enter prompt
        textarea = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "textarea"))
        )
        textarea.send_keys(prompt)
        
        # Generate video
        generate_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Create video')]"))
        )
        generate_btn.click()
        
        # Wait for download button
        download_btn = WebDriverWait(driver, 300).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Download')]"))
        )
        download_btn.click()
        
        # Wait for download to complete
        time.sleep(10)
        return get_latest_file(OUTPUT_DIR, ".mp4")
        
    finally:
        driver.quit()
        display.stop()

def get_latest_file(directory, extension):
    files = [f for f in os.listdir(directory) if f.endswith(extension)]
    paths = [os.path.join(directory, f) for f in files]
    return max(paths, key=os.path.getctime) if paths else None

# === VIDEO EDITING ===
def edit_with_capcut(video_path):
    logger.info("✂️ Editing video with CapCut...")
    
    # Start virtual display for GUI automation
    display = Display(visible=0, size=(1920, 1080))
    display.start()
    
    try:
        # Open CapCut template
        os.system(f"xdg-open 'capcut://template/detail?template_id={CAPCUT_TEMPLATE_ID}'")
        time.sleep(10)
        
        # Automation sequence (calibrate these coordinates)
        pyautogui.hotkey('ctrl', 'i')  # Import shortcut
        time.sleep(2)
        pyautogui.write(video_path)
        pyautogui.press('enter')
        time.sleep(5)
        
        # Auto-edit workflow
        pyautogui.click(x=1200, y=650)  # Apply template button
        time.sleep(3)
        pyautogui.click(x=1350, y=800)  # Export button
        time.sleep(2)
        
        # Set output filename
        output_path = os.path.join(OUTPUT_DIR, "final_video.mp4")
        pyautogui.write(output_path)
        pyautogui.press('enter')
        
        # Wait for export
        time.sleep(30)
        return output_path
        
    finally:
        display.stop()

# === SOCIAL MEDIA UPLOAD ===
def upload_to_tiktok(video_path):
    logger.info("🆙 Uploading to TikTok...")
    try:
        creds = json.load(open(TIKTOK_CREDS_FILE))
        
        # TikTok upload API (simplified)
        upload_url = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
        headers = {
            "Authorization": f"Bearer {creds['access_token']}",
            "Content-Type": "application/json"
        }
        payload = {
            "post_info": {
                "title": "AI Generated Video",
                "privacy_level": "PUBLIC",
                "disable_comment": False,
                "disable_duet": False,
                "disable_stitch": False
            }
        }
        
        response = requests.post(upload_url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"✅ TikTok upload successful! ID: {response.json()['data']['publish_id']}")
        return True
    except Exception as e:
        logger.error(f"❌ TikTok upload failed: {str(e)}")
        return False

def upload_to_youtube(video_path):
    logger.info("🆙 Uploading to YouTube...")
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/youtube.upload']
        )
        youtube = build('youtube', 'v3', credentials=credentials)
        
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": "AI Generated Video",
                    "description": "Created with FantasyAI pipeline",
                    "tags": ["AI", "Generated", "Veo"],
                    "categoryId": "22"
                },
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload(video_path)
        )
        response = request.execute()
        logger.info(f"✅ YouTube upload successful! ID: {response['id']}")
        return True
    except Exception as e:
        logger.error(f"❌ YouTube upload failed: {str(e)}")
        return False

# === MAIN WORKFLOW ===
def main():
    try:
        # Step 1: Get trends
        trends = fetch_trends()
        selected_trend = cluster_trends(trends)
        
        # Step 2: Generate prompt
        prompt = generate_prompt(selected_trend)
        logger.info(f"📝 Generated Prompt:\n{prompt}")
        
        # Step 3: Create video
        raw_video = generate_veo_video(prompt)
        if not raw_video:
            raise Exception("Video generation failed")
        
        # Step 4: Edit video
        final_video = edit_with_capcut(raw_video)
        
        # Step 5: Upload to platforms
        upload_to_tiktok(final_video)
        upload_to_youtube(final_video)
        
        logger.info("🚀 Pipeline completed successfully!")
        
    except Exception as e:
        logger.error(f"🔥 Pipeline failed: {str(e)}")

if __name__ == "__main__":
    main()
