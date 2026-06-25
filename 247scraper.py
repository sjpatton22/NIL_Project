import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

options = Options()
options.add_argument("--headless=new")
options.add_argument("--blink-settings=imagesEnabled=false")
options.page_load_strategy = "eager"

driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(15)

url = "https://247sports.com/season/2025-football/compositerecruitrankings/"

print("Opening page...")

try:
    driver.get(url)
except:
    print("Page load timed out, continuing anyway...")

time.sleep(3)

print("URL:", driver.current_url)
print("Title:", driver.title)

clicks = 0

while True:
    try:
        load_more = driver.find_element(
            By.XPATH,
            "//a[@data-js='showmore']"
        )

        clicks += 1
        print(f"Clicking Load More {clicks}")

        driver.execute_script(
            "arguments[0].click();",
            load_more
        )

        time.sleep(2)

        cards_now = driver.find_elements(
            By.XPATH,
            "//li[contains(@class,'rankings-page__list-item')]"
        )

        print("Cards loaded:", len(cards_now))

    except:
        print("No more Load More button.")
        break

cards = driver.find_elements(
    By.XPATH,
    "//li[contains(@class,'rankings-page__list-item')]"
)

print("Final cards:", len(cards))

names = []
position_list = []
heights = []
weights = []

high_schools = []
cities = []
states = []
committed_to = []

national_ranks = []
position_ranks = []
state_ranks = []

for card in cards:

    try:
        name = card.find_element(
            By.XPATH,
            ".//a[contains(@class,'rankings-page__name-link')]"
        ).text.strip()
    except:
        name = ""

    try:
        pos = card.find_element(
            By.XPATH,
            ".//div[contains(@class,'position')]"
        ).text.strip()
    except:
        pos = ""

    try:
        metrics = card.find_element(
            By.XPATH,
            ".//div[contains(@class,'metrics')]"
        ).text.strip()

        height = metrics.split("/")[0].strip()
        weight = metrics.split("/")[1].strip()

    except:
        height = ""
        weight = ""

    try:
        loc = card.find_element(
            By.XPATH,
            ".//span[contains(@class,'meta')]"
        ).text.strip()

        high_school = loc.split("(")[0].strip()

        city_state = (
            loc.split("(")[1]
            .replace(")", "")
            .strip()
        )

        city = city_state.split(",")[0].strip()
        state = city_state.split(",")[1].strip()

    except:
        high_school = ""
        city = ""
        state = ""

    try:
        committed = card.find_element(
            By.XPATH,
            ".//div[contains(@class,'status')]//img[@title]"
        ).get_attribute("title")
    except:
        committed = ""

    try:
        national_rank = card.find_element(
            By.XPATH,
            ".//a[contains(@class,'natrank')]"
        ).text.strip()
    except:
        national_rank = ""

    try:
        position_rank = card.find_element(
            By.XPATH,
            ".//a[contains(@class,'posrank')]"
        ).text.strip()
    except:
        position_rank = ""

    try:
        state_rank = card.find_element(
            By.XPATH,
            ".//a[contains(@class,'sttrank')]"
        ).text.strip()
    except:
        state_rank = ""

    if name != "":
        names.append(name)
        position_list.append(pos)
        heights.append(height)
        weights.append(weight)

        high_schools.append(high_school)
        cities.append(city)
        states.append(state)
        committed_to.append(committed)

        national_ranks.append(national_rank)
        position_ranks.append(position_rank)
        state_ranks.append(state_rank)

df = pd.DataFrame({
    "Player": names,
    "Position": position_list,
    "Height": heights,
    "Weight": weights,
    "NationalRank": national_ranks,
    "PositionRank": position_ranks,
    "StateRank": state_ranks,
    "HighSchool": high_schools,
    "City": cities,
    "State": states,
    "CommittedTo": committed_to
})

print(df.head())
print("\nTotal players:", len(df))

driver.quit()

print("Done.")