from flask import Flask, render_template, redirect, url_for
import pymongo
import os
from dotenv import load_dotenv
from Scraper import scrape_sea_forecast # ייבוא הפונקציה מהקובץ השני

load_dotenv()
app = Flask(__name__)

client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client['BeachMatchDB']
collection = db['forecasts']

@app.route('/')
def index():
    beach_names = ["HOF_TZAFONI", "HOF_MERKAZI", "HOF_DAROMI", "KINNERET", "EILAT"]
    latest_forecasts = []
    for name in beach_names:
        data = collection.find_one({"station": name}, sort=[("scraped_at", -1)])
        if data: latest_forecasts.append(data)
    return render_template('index.html', forecasts=latest_forecasts)

@app.route('/refresh')
def refresh():
    scrape_sea_forecast() # הפעלת הסריקה
    return redirect(url_for('index')) # חזרה לדף הבית

if __name__ == '__main__':
    # מריץ סריקה ראשונה עם עליית האתר
    scrape_sea_forecast()
    app.run(debug=True)