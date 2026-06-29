import pandas as pd
import math
import requests
from io import StringIO
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


players_path = "/Users/sampatton/Downloads/NIL_Project/2002.csv"
cities_path = "/Users/sampatton/Downloads/NIL_Project/uscities.csv"
output_path = "/Users/sampatton/Downloads/NIL_Project/2002_coordinates_distance.csv"

school_col = "CommittedTo"


# -------------------------
# Load player and city data
# -------------------------
players = pd.read_csv(players_path)
cities = pd.read_csv(cities_path)

players["City"] = players["City"].astype(str).str.strip()
players["State"] = players["State"].astype(str).str.strip()
players[school_col] = players[school_col].astype(str).str.strip()

cities["city"] = cities["city"].astype(str).str.strip()
cities["state_id"] = cities["state_id"].astype(str).str.strip()


# -------------------------
# Add hometown coordinates
# -------------------------
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


# -------------------------
# Scrape FBS school locations
# -------------------------
wiki_url = "https://en.wikipedia.org/wiki/List_of_NCAA_Division_I_FBS_football_stadiums"

headers = {
    "User-Agent": "Mozilla/5.0"
}

print("Downloading FBS school table...")

html = requests.get(wiki_url, headers=headers).text
tables = pd.read_html(StringIO(html))

fbs = tables[0]

fbs = fbs[["City", "State", "Team", "Conference"]]

fbs = fbs.rename(
    columns={
        "City": "School_City",
        "State": "School_State",
        "Team": "University"
    }
)

# Remove Wikipedia footnotes like [1], [a], [d]
fbs = fbs.replace(r"\[[^\]]*\]", "", regex=True)

for col in fbs.select_dtypes(include="object").columns:
    fbs[col] = fbs[col].astype(str).str.strip()

# Match keys
fbs["School_Key"] = fbs["University"].str.lower().str.strip()
players["School_Key"] = players[school_col].str.lower().str.strip()


# -------------------------
# Get school coordinates from uscities.csv
# -------------------------
fbs = fbs.merge(
    cities[["city", "state_id", "lat", "lng"]],
    left_on=["School_City", "School_State"],
    right_on=["city", "state_id"],
    how="left"
)

fbs = fbs.drop(columns=["city", "state_id"])

fbs = fbs.rename(
    columns={
        "lat": "School_Latitude",
        "lng": "School_Longitude"
    }
)


# -------------------------
# Merge school info onto players
# -------------------------
players = players.merge(
    fbs[
        [
            "School_Key",
            "School_City",
            "School_State",
            "University",
            "Conference",
            "School_Latitude",
            "School_Longitude"
        ]
    ],
    on="School_Key",
    how="left"
)

players = players.rename(
    columns={
        "University": "Matched_University",
        "Conference": "School_Conference"
    }
)


# -------------------------
# Geocoder setup
# Only used for missing hometowns and unmatched schools
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
# Fill missing hometown coords
# -------------------------
missing_places = (
    players[players["Latitude"].isna()][["City", "State"]]
    .drop_duplicates()
)

print("Missing city/state pairs:", len(missing_places))

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
# Fallback geocode for schools not matched by Wikipedia/uscities
# -------------------------
unmatched_schools = (
    players[
        players["School_Latitude"].isna()
    ][school_col]
    .dropna()
    .drop_duplicates()
)

print("Schools needing fallback geocode:", len(unmatched_schools))

for school in unmatched_schools:

    if str(school).lower() in ["nan", "none", ""]:
        continue

    place = f"{school}, USA"

    print(f"Fallback geocoding school: {place}")

    try:
        location = geocode(place)

        if location:
            mask = players[school_col] == school

            players.loc[mask, "School_Latitude"] = location.latitude
            players.loc[mask, "School_Longitude"] = location.longitude

        else:
            print(f"Could not find school: {place}")

    except Exception as e:
        print(f"Error for {place}: {e}")


# -------------------------
# Distance formula in miles
# -------------------------
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
players = players.drop(columns=["School_Key"])

players.to_csv(output_path, index=False)

print("Done!")
print(f"Saved to {output_path}")

print("Missing hometown coordinates:", players["Latitude"].isna().sum())
print("Missing school coordinates:", players["School_Latitude"].isna().sum())

print("Schools still missing coordinates:")
print(
    players[
        players["School_Latitude"].isna()
    ][school_col].drop_duplicates()
)