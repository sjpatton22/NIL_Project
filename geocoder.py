import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

players_path = "/Users/sampatton/Downloads/NIL_Project/2025.csv"
cities_path = "/Users/sampatton/Downloads/NIL_Project/uscities.csv"
output_path = "/Users/sampatton/Downloads/NIL_Project/2025_coordinates.csv"

players = pd.read_csv(players_path)
cities = pd.read_csv(cities_path)

# clean text
players["City"] = players["City"].str.strip()
players["State"] = players["State"].str.strip()

cities["city"] = cities["city"].str.strip()
cities["state_id"] = cities["state_id"].str.strip()

# merge from local database first
players = players.merge(
    cities[["city", "state_id", "lat", "lng"]],
    left_on=["City", "State"],
    right_on=["city", "state_id"],
    how="left"
)

players = players.drop(columns=["city", "state_id"])

players = players.rename(
    columns={
        "lat": "Latitude",
        "lng": "Longitude"
    }
)

# geopy only for missing cities
geolocator = Nominatim(
    user_agent="nil_project",
    timeout=10
)

geocode = RateLimiter(
    geolocator.geocode,
    min_delay_seconds=1.5,
    max_retries=2,
    error_wait_seconds=5
)

missing_places = (
    players[players["Latitude"].isna()][["City", "State"]]
    .drop_duplicates()
)

print("Missing city/state pairs:", len(missing_places))

for i, row in missing_places.iterrows():

    city = row["City"]
    state = row["State"]
    place = f"{city}, {state}, USA"

    print(f"Geocoding: {place}")

    try:
        location = geocode(place)

        if location:
            mask = (
                (players["City"] == city) &
                (players["State"] == state) &
                (players["Latitude"].isna())
            )

            players.loc[mask, "Latitude"] = location.latitude
            players.loc[mask, "Longitude"] = location.longitude

        else:
            print(f"Could not find: {place}")

    except Exception as e:
        print(f"Error for {place}: {e}")

save final file
players.to_csv(output_path, index=False)

print("Done!")
print(f"Saved to {output_path}")

# check remaining missing
missing = players[players["Latitude"].isna()]
print("Still missing:", len(missing))
print(missing[["City", "State"]].drop_duplicates())