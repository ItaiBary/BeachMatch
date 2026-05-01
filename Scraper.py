import requests
from bs4 import BeautifulSoup
import os
import pymongo
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")


def get_collection():
    client = pymongo.MongoClient(MONGO_URI)
    db = client['BeachMatchDB']
    return db['forecasts']


SEA_URLS = {
    "HOF_TZAFONI": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_212_he.xml",
    "HOF_MERKAZI": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_210_he.xml",
    "HOF_DAROMI": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_213_he.xml",
    "KINNERET": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_211_he.xml",
    "EILAT": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_214_he.xml",
}


def parse_description(html_desc):
    soup = BeautifulSoup(html_desc, "html.parser")
    blocks = []
    current = None
    for elem in soup.stripped_strings:
        text = elem.strip()
        if text.startswith("מ-") and "עד" in text:
            if current: blocks.append(current)
            current = {"time_range": text, "data": []}
        elif current and not text.startswith("הנרשם"):
            current["data"].append(text)
    if current: blocks.append(current)
    return blocks


def extract_variables(block):
    result = {}
    for line in block["data"]:
        if "מהירות הרוח" in line:
            numbers = [int(s) for s in line.replace("קמ\"ש", "").split() if s.isdigit()]
            result["wind_speed"] = numbers if numbers else None
        elif "כיוון הרוח" in line:
            result["wind_direction"] = line.split(":")[-1].strip()
        elif "גובה הגלים" in line:
            numbers = [int(s) for s in line.replace("ס\"מ", "").split() if s.isdigit()]
            result["wave_height"] = numbers if numbers else None
        elif "טמפרטורת פני הים" in line:
            numbers = [int(s) for s in line.split(":")[-1].split() if s[0].isdigit()]
            result["water_temp"] = numbers[0] if numbers else None
    return result


def scrape_sea_forecast():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] מתחיל עדכון נתונים מ-IMS...")
    collection = get_collection()

    for station, url in SEA_URLS.items():
        try:
            response = requests.get(url, timeout=10)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "xml")
            item = soup.find("item")
            if not item: continue

            title = item.find("title").text
            pub_date = item.find("pubDate").text
            description_html = item.find("description").text

            blocks = parse_description(description_html)
            for block in blocks:
                variables_dict = extract_variables(block)
                document = {
                    "station": station,
                    "title": title,
                    "pub_date": pub_date,
                    "forecast_time_range": block["time_range"],
                    "data": variables_dict,
                    "scraped_at": datetime.now()
                }
                collection.insert_one(document)
            print(f"  [V] {station} עודכן.")
        except Exception as e:
            print(f"X שגיאה ב-{station}: {e}")
    return True


if __name__ == "__main__":
    scrape_sea_forecast()
    os.system("pip freeze > requirements.txt")