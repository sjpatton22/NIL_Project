import pandas as pd
import math
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


players_path = "/Users/sampatton/Downloads/NIL_Project/2024.csv"
cities_path = "/Users/sampatton/Downloads/NIL_Project/uscities.csv"
schools_path = "/Users/sampatton/Downloads/NIL_Project/ncaa_d1_football_schools.csv"
output_path = "/Users/sampatton/Downloads/NIL_Project/2024_coordinates_distance.csv"

school_col = "CommittedTo"


# -------------------------
# Helpers
# -------------------------
def make_key(s):
    return (
        s.astype(str)
        .str.lower()
        .str.replace(r"[^a-z0-9 ]", "", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def haversine_miles(lat1, lon1, lat2, lon2):

    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return None

    R = 3958.8

    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.asin(math.sqrt(a))

    return R * c


# -------------------------
# Load data
# -------------------------
players = pd.read_csv(players_path)
cities = pd.read_csv(cities_path)
schools = pd.read_csv(schools_path)

players["City"] = players["City"].astype(str).str.strip()
players["State"] = players["State"].astype(str).str.strip()
players[school_col] = players[school_col].astype(str).str.strip()

cities["city"] = cities["city"].astype(str).str.strip()
cities["state_id"] = cities["state_id"].astype(str).str.strip()

schools["School"] = schools["School"].astype(str).str.strip()
schools["School_City"] = schools["School_City"].astype(str).str.strip()
schools["School_State"] = schools["School_State"].astype(str).str.strip()


# -------------------------
# Add hometown coordinates from uscities.csv
# -------------------------
cities["city_key"] = make_key(cities["city"])
cities["state_key"] = cities["state_id"].str.upper().str.strip()

players["city_key"] = make_key(players["City"])
players["state_key"] = players["State"].str.upper().str.strip()

players = players.merge(
    cities[["city_key", "state_key", "lat", "lng"]],
    on=["city_key", "state_key"],
    how="left"
)

players = players.rename(
    columns={
        "lat": "Latitude",
        "lng": "Longitude"
    }
)

players = players.drop(columns=["city_key", "state_key"])


# -------------------------
# Geocoder setup
# Only used for missing hometowns
# -------------------------
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


# -------------------------
# Fill missing hometown coords with Nominatim
# -------------------------
missing_places = (
    players[players["Latitude"].isna()][["City", "State"]]
    .drop_duplicates()
)

print("Missing hometown city/state pairs:", len(missing_places))

for i, row in missing_places.iterrows():

    city = row["City"]
    state = row["State"]
    place = f"{city}, {state}, USA"

    print(f"Geocoding hometown: {place}")

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
            print(f"Could not find hometown: {place}")

    except Exception as e:
        print(f"Error for {place}: {e}")


# -------------------------
# Fix school name differences
# -------------------------
school_name_map = {
    "Miami (FL)": "Miami",
    "Miami": "Miami",
    "Hawaii": "Hawaiʻi",
    "Ole Miss": "Ole Miss",
    "Northern Illinois": "Northern Illinois",
    "Colorado State": "Colorado State",
    "Alabama": "Alabama",
    "Florida": "Florida"
}

players["School_Matched_Name"] = players[school_col].replace(school_name_map)


# -------------------------
# Merge school info from saved NCAA school CSV
# -------------------------
players["School_Key"] = make_key(players["School_Matched_Name"])
schools["School_Key"] = make_key(schools["School"])

players = players.merge(
    schools[
        [
            "School_Key",
            "School_City",
            "School_State",
            "Conference",
            "Division",
            "School_Latitude",
            "School_Longitude"
        ]
    ],
    on="School_Key",
    how="left"
)

players = players.rename(
    columns={
        "Conference": "School_Conference",
        "Division": "School_Division"
    }
)


# -------------------------
# Distance from hometown to school
# -------------------------
players["Distance_To_School_Miles"] = players.apply(
    lambda row: haversine_miles(
        row["Latitude"],
        row["Longitude"],
        row["School_Latitude"],
        row["School_Longitude"]
    ),
    axis=1
)


# -------------------------
# Clean up and save
# -------------------------
players = players.drop(
    columns=["School_Key", "School_Matched_Name"],
    errors="ignore"
)

players.to_csv(output_path, index=False)

print("Done!")
print(f"Saved to {output_path}")

print("Missing hometown coordinates:", players["Latitude"].isna().sum())
print("Missing school coordinates:", players["School_Latitude"].isna().sum())

print("Schools still missing coordinates or unmatched:")
print(
    players[
        players["School_Latitude"].isna()
    ][school_col].drop_duplicates()
)