document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("weather-form");
    const cityInput = document.getElementById("city-input");
    const loadingText = document.getElementById("loading-text");
    const darkModeToggle = document.getElementById("dark-mode-toggle");
    const body = document.body;

    // Restore dark mode state from localStorage
    if (localStorage.getItem("dark-mode") === "enabled") {
        body.classList.add("dark-mode");
    }

    // Toggle dark mode
    darkModeToggle.addEventListener("click", () => {
        body.classList.toggle("dark-mode");
        if (body.classList.contains("dark-mode")) {
            localStorage.setItem("dark-mode", "enabled");
        } else {
            localStorage.removeItem("dark-mode");
        }
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const city = cityInput.value.trim();
        if (!city) {
            alert("Please enter a city name!");
            return;
        }

        loadingText.style.display = "block";

        try {
            const response = await fetch(`/get_weather?city=${city}`);
            const data = await response.json();

            if (data.error) {
                alert("City not found! Please try again.");
            } else {
                updateWeatherUI(data);
            }
        } catch (error) {
            alert("Failed to fetch weather data. Try again later!");
        } finally {
            loadingText.style.display = "none";
        }
    });

    function updateWeatherUI(data) {
        document.querySelector(".weather-info").innerHTML = `
            <h2><i class="wi wi-day-cloudy"></i> Current Weather in ${data.location.name}, ${data.location.country}</h2>
            <div class="weather-card">
                <p><i class="wi wi-thermometer"></i> Temperature: ${data.current.temp_c}°C</p>
                <p>Condition: <i class="wi wi-${data.current.condition.icon}"></i> ${data.current.condition.text}</p>
                ${data.current.air_quality ? `<p><i class="wi wi-dust"></i> Air Quality Index: ${data.current.air_quality.pm2_5}</p>` : "<p>Air Quality Data not available.</p>"}
            </div>
        `;
    }
});
