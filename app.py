from flask import Flask, render_template, request
import requests

app = Flask(__name__)

API_KEY = "7e9f9ec3865241c187795412251302"
BASE_URL = "http://api.weatherapi.com/v1/"


def get_weather(city):
    url = f"{BASE_URL}current.json?key={API_KEY}&q={city}&aqi=yes"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def get_forecast(city):
    url = f"{BASE_URL}forecast.json?key={API_KEY}&q={city}&days=3&aqi=yes&alerts=yes"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None   
    
@app.route("/", methods=["GET", "POST"])
def home():
    weather_data = None
    forecast_data = None
    if request.method == "POST":
        city = request.form["city"]
        weather_data = get_weather(city)
        forecast_data = get_forecast(city) 
    return render_template("index.html", weather=weather_data, forecast=forecast_data)

if __name__ == "__main__":
    app.run(debug=True)
    