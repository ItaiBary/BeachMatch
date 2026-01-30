import requests
from bs4 import BeautifulSoup
import os

SEA_URLS = {
    "HOF_TZAFONI": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_212_he.xml",
    "HOF_MERKAZI": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_210_he.xml",
    "HOF_DAROMI": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_213_he.xml",
    "KINNERET": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_211_he.xml",
    "EILAT": "https://ims.gov.il/sites/default/files/ims_data/rss/forecast_sea/rssForecastSea_214_he.xml",
}

VARIABLES = ["wind_speed", "wind_direction", "wave_height", "water_temp"]


def parse_description(html_desc):
    """ מפרק את תיאור החוף לבלוקים לפי טווחי זמן """
    soup = BeautifulSoup(html_desc, "html.parser")
    blocks = []
    current = None

    for elem in soup.stripped_strings:
        text = elem.strip()
        if text.startswith("מ-") and "עד" in text:  # התחלה של טווח זמן
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


def save_data(station, variables_dict):
    """ שומר כל משתנה בספרייה נפרדת """
    BASE_DIR = "data"
    if not os.path.exists(BASE_DIR):
        os.mkdir(BASE_DIR)

    for var in variables_dict:
        var_dir = os.path.join(BASE_DIR, var)
        if not os.path.exists(var_dir):
            os.mkdir(var_dir)

        file_path = os.path.join(var_dir, f"{station}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(str(variables_dict[var]))


def scrape_sea_forecast():
    print("\n=== מתחיל משיכת תחזיות חופים ===\n")
    for station, url in SEA_URLS.items():
        try:
            response = requests.get(url, timeout=10)
            response.encoding = "utf-8"
        except Exception as e:
            print(f"Error fetching {station}: {e}")
            continue

        soup = BeautifulSoup(response.text, "xml")
        item = soup.find("item")
        if not item:
            continue

        title = item.find("title").text
        pub_date = item.find("pubDate").text
        description_html = item.find("description").text

        print("=" * 50)
        print(f"חוף: {station}")
        print(f"כותרת: {title}")
        print(f"זמן פרסום: {pub_date}\n")

        blocks = parse_description(description_html)

        for block in blocks:
            print(block["time_range"])
            variables_dict = extract_variables(block)
            for var_name, value in variables_dict.items():
                print(f"- {var_name}: {value}")
            save_data(station, variables_dict)
            print()

        print("=" * 50, "\n")


def read_variable(variable_name):
    """ קורא את כל הקבצים בספרייה של משתנה מסוים """
    var_dir = os.path.join("data", variable_name)
    if not os.path.exists(var_dir):
        print(f"No directory for variable '{variable_name}'")
        return

    print(f"\n--- Values for variable '{variable_name}' ---")
    for filename in os.listdir(var_dir):
        file_path = os.path.join(var_dir, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            value = f.read().strip()
        print(f"{filename.replace('.txt', '')} -> {value}")


def read_station(station_name):
    """ קורא את כל המשתנים עבור חוף מסוים """
    print(f"\n=== Data for station '{station_name}' ===")
    base_dir = "data"
    if not os.path.exists(base_dir):
        print("No data available. Run scrape_sea_forecast() first.")
        return

    for var in VARIABLES:
        var_dir = os.path.join(base_dir, var)
        file_path = os.path.join(var_dir, f"{station_name}.txt")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                value = f.read().strip()
            print(f"{var}: {value}")
        else:
            print(f"{var}: No data")


if __name__ == "__main__":
    scrape_sea_forecast()  # מושך ושומר את כל החופים

    # דוגמה: קריאה לפי משתנה
    read_variable("wind_speed")
    read_variable("wave_height")

    # דוגמה: קריאה לפי חוף
    read_station("HOF_TZAFONI")
    read_station("EILAT")
