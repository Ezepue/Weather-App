from flask import Flask, render_template, request
import requests

app = Flask(__name__)

API_KEY = "7e9f9ec3865241c187795412251302"
BASE_URL = "http://api.weatherapi.com/v1/current.json"

@app.route("/", methods=["GET", "POST"])
def home():
    weather_data = None
    if request.method == "POST":
        city = request.form["city"]
        url = f"{BASE_URL}?key={API_KEY}&q={city}"
        response = requests.get(url)
        if response.status_code == 200:
            weather_data = response.json()
        else:
            weather_data= {"error": "City not found"}
    
    return render_template("index.html", weather=weather_data)

if __name__ == "__main__":
    app.run(debug=True)
    