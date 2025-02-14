from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import requests
import os

load_dotenv()  # Load environment variables

API_KEY = os.getenv("API_KEY")

app = Flask(__name__)

BASE_URL = "http://api.weatherapi.com/v1/"

@app.route("/", methods=["GET", "POST"])
def home():
    city = "London"
    if request.method == "POST":
        city = request.form["city"]
    
    urls = {
        "weather": f"{BASE_URL}current.json?key={API_KEY}&q={city}&aqi=yes",
        "forecast": f"{BASE_URL}forecast.json?key={API_KEY}&q={city}&days=3&aqi=yes&alerts=yes",
        "timezone": f"{BASE_URL}timezone.json?key={API_KEY}&q={city}",
        "marine": f"{BASE_URL}marine.json?key={API_KEY}&q={city}",
        "astronomy": f"{BASE_URL}astronomy.json?key={API_KEY}&q={city}"
    }

    responses = {}

    for key, url in urls.items():
        try:
            response = requests.get(url)
            data = response.json()
            if "error" in data:
                responses[key] = {"error": data["error"]["message"]}
            else:
                responses[key] = data
        except requests.exceptions.RequestException as e:
            responses[key] = {"error": "Failed to fetch data"}

    return render_template("index.html", **responses)

@app.route("/get_weather")
def get_weather():
    city = request.args.get("city", "")
    if not city:
        return jsonify({"error": "City is required"}), 400

    weather_url = f"{BASE_URL}current.json?key={API_KEY}&q={city}&aqi=yes"
    try:
        response = requests.get(weather_url)
        data = response.json()
        if "error" in data:
            return jsonify({"error": data["error"]["message"]}), 400
        return jsonify(data)
    except requests.exceptions.RequestException:
        return jsonify({"error": "Failed to fetch data"}), 500

if __name__ == "__main__":
    app.run(debug=True)
