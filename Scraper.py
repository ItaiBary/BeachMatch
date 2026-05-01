import requests
from bs4 import BeautifulSoup
import os
import pymongo
from datetime import datetime
from dotenv import load_dotenv

# --- טעינת הגדרות אבטחה ---
load_dotenv()  # טוען את המשתנים מקובץ .env
MONGO_URI = os.getenv("MONGO_URI")

# --- חיבור ל-MongoDB ---
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client['BeachMatchDB']
    collection = db['forecasts']
    # בדיקת חיבור
    client.admin.command('ping')
    print("V - התחברת בהצלחה ל-MongoDB (מאובטח)!")
except Exception as e:
    print(f"X - שגיאה בחיבור ל-MongoDB: {e}")

SEA_URLS = {
    "HOF_TZAFONI": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_212_he.xml",
    "HOF_MERKAZI": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_210_he.xml",
    "HOF_DAROMI": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_213_he.xml",
    "KINNERET": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_211_he.xml",
    "EILAT": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_214_he.xml",
}


def parse_description(html_desc):
    """ מפרק את תיאור החוף לבלוקים לפי טווחי זמן """
    soup = BeautifulSoup(html_desc, "html.parser")
    blocks = []
    current = None

    for elem in soup.stripped_strings:
        text = elem.strip()
        if text.startswith("מ-") and "עד" in text:
            if current:
                blocks.append(current)
            current = {"time_range": text, "data": []}
        elif current and not text.startswith("הנרשם"):
            current["data"].append(text)

    if current:
        blocks.append(current)
    return blocks


def extract_variables(block):
    """ מחלץ את הערכים של המשתנים מתוך בלוק """
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


def save_to_mongo(station, time_range, variables, title, pub_date):
    """ שומר את המידע ל-MongoDB """
    try:
        document = {
            "station": station,
            "title": title,
            "pub_date": pub_date,
            "forecast_time_range": time_range,
            "data": variables,
            "scraped_at": datetime.now()
        }
        collection.insert_one(document)
        return True
    except Exception as e:
        print(f"שגיאה בשמירה ל-DB: {e}")
        return False


def scrape_sea_forecast():
    print("\n=== מתחיל משיכת תחזיות ושמירה לענן ===\n")
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

            print(f"מעבד נתונים עבור: {station}...")
            blocks = parse_description(description_html)

            for block in blocks:
                variables_dict = extract_variables(block)
                success = save_to_mongo(station, block["time_range"], variables_dict, title, pub_date)
                if success:
                    print(f"  [V] נשמר טווח זמן: {block['time_range']}")

        except Exception as e:
            print(f"שגיאה בעיבוד {station}: {e}")


if __name__ == "__main__":
    # הרצת הסריקה
    scrape_sea_forecast()

    # עדכון קובץ ה-requirements אוטומטית בסיום
    os.system("pip freeze > requirements.txt")
    print("\nהתהליך הסתיים בהצלחה! קובץ ה-requirements עודכן.")