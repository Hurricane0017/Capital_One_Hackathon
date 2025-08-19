import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from geopy.geocoders import Nominatim
import numpy as np

def get_coordinates(address):
    geolocator = Nominatim(user_agent="weather_app")
    location = geolocator.geocode(address)
    if location:
        return location.latitude, location.longitude
    else:
        raise ValueError(f"Address '{address}' not found.")

# Prompt user for detailed address input
address = input("Enter address (vlg, mandal, pincode, district, state): ")
if not address:
    address = "Hyderabad, Telangana, India"

# Prompt user for start and end dates
start_date = input("Enter start date (YYYY-MM-DD): ")
if not start_date:
    start_date = "2025-08-21"

end_date = input("Enter end date (YYYY-MM-DD): ")
if not end_date:
    end_date = "2025-08-25"
latitude, longitude = get_coordinates(address)

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Weather API parameters
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": latitude,
    "longitude": longitude,
    "hourly": [
        "temperature_2m", "relative_humidity_2m", "apparent_temperature", "rain",
        "showers", "snow_depth", "surface_pressure", "cloud_cover", "cloud_cover_low",
        "cloud_cover_high", "vapour_pressure_deficit", "wind_direction_80m",
        "wind_gusts_10m", "wind_speed_120m", "soil_moisture_3_to_9cm",
        "soil_moisture_9_to_27cm"
    ],
    "start_date": start_date,
    "end_date": end_date,
}
responses = openmeteo.weather_api(url, params=params)

# Process first location
response = responses[0]
print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
print(f"Elevation: {response.Elevation()} m asl")
print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

# Process hourly data
hourly = response.Hourly()
hourly_data = {"date": pd.date_range(
    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
    freq=pd.Timedelta(seconds=hourly.Interval()),
    inclusive="left"
)}

# Extract variables
variables = [
    "temperature_2m", "relative_humidity_2m", "apparent_temperature", "rain",
    "showers", "snow_depth", "surface_pressure", "cloud_cover",
    "cloud_cover_low", "cloud_cover_high", "vapour_pressure_deficit",
    "wind_direction_80m", "wind_gusts_10m", "wind_speed_120m",
    "soil_moisture_3_to_9cm", "soil_moisture_9_to_27cm"
]

for i, var in enumerate(variables):
    hourly_data[var] = hourly.Variables(i).ValuesAsNumpy()

# Convert to DataFrame
hourly_df = pd.DataFrame(data=hourly_data)
hourly_df.set_index("date", inplace=True)
print("\nHourly Data\n", hourly_df.head())

# --- DAILY AGGREGATION ---

# Function for circular mean (wind direction)
def daily_wind_direction(hourly_series):
    radians = np.deg2rad(hourly_series)
    sin_avg = np.mean(np.sin(radians))
    cos_avg = np.mean(np.cos(radians))
    mean_angle = np.rad2deg(np.arctan2(sin_avg, cos_avg))
    return (mean_angle + 360) % 360  # normalize to 0-360

# Aggregate daily
daily_df = pd.DataFrame({
    "temp_mean": hourly_df["temperature_2m"].resample("D").mean(),
    "temp_max": hourly_df["temperature_2m"].resample("D").max(),
    "temp_min": hourly_df["temperature_2m"].resample("D").min(),
    "apparent_temp_mean": hourly_df["apparent_temperature"].resample("D").mean(),
    "apparent_temp_max": hourly_df["apparent_temperature"].resample("D").max(),
    "apparent_temp_min": hourly_df["apparent_temperature"].resample("D").min(),
    "humidity_mean": hourly_df["relative_humidity_2m"].resample("D").mean(),
    "rain_sum": hourly_df["rain"].resample("D").sum(),
    "showers_sum": hourly_df["showers"].resample("D").sum(),
    "snow_depth_sum": hourly_df["snow_depth"].resample("D").sum(),
    "surface_pressure_mean": hourly_df["surface_pressure"].resample("D").mean(),
    "cloud_cover_mean": hourly_df["cloud_cover"].resample("D").mean(),
    "cloud_cover_low_mean": hourly_df["cloud_cover_low"].resample("D").mean(),
    "cloud_cover_high_mean": hourly_df["cloud_cover_high"].resample("D").mean(),
    "vapour_pressure_deficit_mean": hourly_df["vapour_pressure_deficit"].resample("D").mean(),
    "wind_gusts_max": hourly_df["wind_gusts_10m"].resample("D").max(),
    "wind_speed_120m_mean": hourly_df["wind_speed_120m"].resample("D").mean(),
    "soil_moisture_3_to_9cm_mean": hourly_df["soil_moisture_3_to_9cm"].resample("D").mean(),
    "soil_moisture_9_to_27cm_mean": hourly_df["soil_moisture_9_to_27cm"].resample("D").mean(),
})

# Apply wind direction properly
daily_df["wind_direction_80m_mean"] = hourly_df["wind_direction_80m"].resample("D").apply(daily_wind_direction)

print("\nDaily Data\n", daily_df.head())

# --- SAVE TO JSON ---
# Save hourly data
hourly_df_reset = hourly_df.reset_index()
hourly_df_reset["date"] = hourly_df_reset["date"].apply(lambda x: x.isoformat() if hasattr(x, "isoformat") else str(x))
hourly_json = hourly_df_reset.to_dict(orient="records")
hourly_json_path = f"weather_hourly_{latitude:.4f}_{longitude:.4f}_{start_date}_to_{end_date}.json"
with open(hourly_json_path, "w", encoding="utf-8") as f:
    import json
    json.dump(hourly_json, f, ensure_ascii=False, indent=2)
print(f"\n✅ Hourly data saved to {hourly_json_path}")

# Save daily data
_daily_df = daily_df.copy()
_daily_df["date"] = daily_df.index.strftime("%Y-%m-%d")
daily_json = _daily_df.reset_index(drop=True).to_dict(orient="records")
daily_json_path = f"weather_daily_{latitude:.4f}_{longitude:.4f}_{start_date}_to_{end_date}.json"
with open(daily_json_path, "w", encoding="utf-8") as f:
    json.dump(daily_json, f, ensure_ascii=False, indent=2)
print(f"✅ Daily data saved to {daily_json_path}")

