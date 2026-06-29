import pandas as pd
import requests
from io import StringIO
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


cities_path = "/Users/sampatton/Downloads/NIL_Project/uscities.csv"
output_path = "/Users/sampatton/Downloads/NIL_Project/ncaa_d1_football_schools.csv"


# -------------------------
# State name to abbreviation map
# -------------------------
state_name_to_abbr = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "District of Columbia": "DC"
}


# -------------------------
# Load city data
# -------------------------
cities = pd.read_csv(cities_path)

cities["city"] = cities["city"].astype(str).str.strip()
cities["state_id"] = cities["state_id"].astype(str).str.strip()

cities["city_key"] = (
    cities["city"]
    .str.lower()
    .str.replace(r"[^a-z0-9 ]", "", regex=True)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

cities["state_key"] = cities["state_id"].str.upper().str.strip()


# -------------------------
# Scrape NCAA program tables
# -------------------------
def scrape_ncaa_programs(url, division):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    print(f"Downloading {division} table...")

    html = requests.get(url, headers=headers).text
    tables = pd.read_html(StringIO(html))

    for table in tables:

        if isinstance(table.columns, pd.MultiIndex):
            table.columns = [
                " ".join([str(x) for x in col if str(x) != "nan"]).strip()
                for col in table.columns
            ]
        else:
            table.columns = [str(c).strip() for c in table.columns]

        table.columns = (
            pd.Series(table.columns)
            .str.replace(r"\[[^\]]*\]", "", regex=True)
            .str.replace("\n", " ")
            .str.replace("  ", " ")
            .str.strip()
        )

        cols = list(table.columns)

        if division == "FBS":
            team_col = "School"
        else:
            team_col = "Team"

        if team_col in cols and "City" in cols and "State" in cols:

            conference_col = None

            for col in cols:
                if "conference" in col.lower():
                    conference_col = col
                    break

            if conference_col is None:
                continue

            df = table[[team_col, "City", "State", conference_col]].copy()

            df = df.rename(
                columns={
                    team_col: "School",
                    "City": "School_City",
                    "State": "School_State",
                    conference_col: "Conference"
                }
            )

            df["Division"] = division

            for col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(r"\[[^\]]*\]", "", regex=True)
                    .str.replace("\xa0", " ")
                    .str.strip()
                )

            df["School"] = df["School"].replace({
                "Miami (FL)": "Miami"
            })

            df["School_State"] = df["School_State"].replace(state_name_to_abbr)

            # Wikipedia lists UTRGV as Brownsville & Edinburg.
            # Use Edinburg so it matches uscities.csv.
            df.loc[df["School"] == "UTRGV", "School_City"] = "Edinburg"

            return df

    raise ValueError(f"No usable table found for {division}")


# -------------------------
# Scrape FBS and FCS
# -------------------------
fbs_url = "https://en.wikipedia.org/wiki/List_of_NCAA_Division_I_FBS_football_programs"
fcs_url = "https://en.wikipedia.org/wiki/List_of_NCAA_Division_I_FCS_football_programs"

fbs = scrape_ncaa_programs(fbs_url, "FBS")
fcs = scrape_ncaa_programs(fcs_url, "FCS")

schools = pd.concat([fbs, fcs], ignore_index=True)

schools = schools.drop_duplicates(
    subset=["School", "School_City", "School_State", "Conference", "Division"]
)


# -------------------------
# Make clean city/state keys for matching
# -------------------------
schools["city_key"] = (
    schools["School_City"]
    .str.lower()
    .str.replace(r"[^a-z0-9 ]", "", regex=True)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

schools["state_key"] = schools["School_State"].str.upper().str.strip()


# -------------------------
# Add coordinates from uscities.csv
# -------------------------
schools = schools.merge(
    cities[["city_key", "state_key", "lat", "lng"]],
    on=["city_key", "state_key"],
    how="left"
)

schools = schools.rename(
    columns={
        "lat": "School_Latitude",
        "lng": "School_Longitude"
    }
)


# -------------------------
# Nominatim fallback for missing coords
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

missing_schools = schools[
    schools["School_Latitude"].isna()
].copy()

print("Schools needing fallback geocode:", len(missing_schools))

for i, row in missing_schools.iterrows():

    school = row["School"]
    city = row["School_City"]
    state = row["School_State"]

    place = f"{city}, {state}, USA"

    print(f"Fallback geocoding: {school} | {place}")

    try:
        location = geocode(place)

        if location:
            schools.loc[i, "School_Latitude"] = location.latitude
            schools.loc[i, "School_Longitude"] = location.longitude

        else:
            print(f"Could not find: {place}")

    except Exception as e:
        print(f"Error for {place}: {e}")


# -------------------------
# Clean up and save
# -------------------------
schools = schools.drop(
    columns=["city_key", "state_key"],
    errors="ignore"
)

schools.to_csv(output_path, index=False)

print("Done!")
print(f"Saved to {output_path}")
print("Rows:", len(schools))

print("Missing coordinates:", schools["School_Latitude"].isna().sum())

print("Schools still missing coordinates:")
print(
    schools[
        schools["School_Latitude"].isna()
    ][["School", "School_City", "School_State", "Division"]]
)