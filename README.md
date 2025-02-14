# Weather App

This is a simple weather app that allows users to check the current weather and a 3-day forecast for any location.

## Features
- Search for weather by city name
- Display current weather conditions
- Show a 3-day weather forecast
- Responsive UI with a modern design

## Technologies Used
- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python (Flask)
- **API:** WeatherAPI (or any other weather API)

## Installation

### Prerequisites
Make sure you have **Python 3** installed.

### Setup
1. Clone the repository:
   ```sh
   git clone https://github.com/Ezepue/weather-app.git
   cd weather-app
   ```
2. Create a virtual environment:
   ```sh
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Set up your API key in a `.env` file:
   ```sh
   echo "API_KEY=your_api_key_here" > .env
   ```
5. Run the application:
   ```sh
   python app.py
   ```
6. Open your browser and go to `http://127.0.0.1:5000/`

## API Key Configuration
- This app requires an API key from WeatherAPO (or your preferred weather API).
- Register on [WeatherAPI](https://www.weatherapi.com/) to get a free API key.
- Store the API key in a `.env` file to keep it secure.

## Requirements
A list of dependencies is available in `requirements.txt`.

```
Flask
requests
dotenv
```

## License
This project is licensed under the MIT License.

## Contributing
Feel free to fork this repo and contribute! 🚀

