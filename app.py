from flask import Flask, render_template, request
import requests

app = Flask(__name__)

API_KEY = "7e9f9ec3865241c187795412251302"
BASE_URL = "http://api.weatherapi.com/v1/"

@app.route("/", methods=["GET", "POST"])
def home():
    city = "London"
    if request.method == "POST":
        city = request.form["city"]
    
    # API URLs (Sport & History Removed)
    weather_url = f"{BASE_URL}current.json?key={API_KEY}&q={city}&aqi=yes"
    forecast_url = f"{BASE_URL}forecast.json?key={API_KEY}&q={city}&days=7&aqi=yes&alerts=yes"
    timezone_url = f"{BASE_URL}timezone.json?key={API_KEY}&q={city}"
    marine_url = f"{BASE_URL}marine.json?key={API_KEY}&q={city}"
    astronomy_url = f"{BASE_URL}astronomy.json?key={API_KEY}&q={city}"
    
    responses = {}
    urls = {
        "weather": weather_url,
        "forecast": forecast_url,
        "timezone": timezone_url,
        "marine": marine_url,
        "astronomy": astronomy_url
    }

    for key, url in urls.items():
        try:
            response = requests.get(url)
            data = response.json()
            
            # Check if the API returned an error
            if "error" in data:
                print(f"Error fetching {key} data:", data["error"]["message"])
                responses[key] = {"error": data["error"]["message"]}
            else:
                responses[key] = data

        except requests.exceptions.RequestException as e:
            print(f"Exception fetching {key} data:", str(e))
            responses[key] = {"error": "Failed to fetch data"}

    return render_template("index.html", **responses)

if __name__ == "__main__":
    app.run(debug=True)
