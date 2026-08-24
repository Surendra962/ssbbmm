from datetime import datetime
import json
import os
from bs4 import BeautifulSoup
import gspread
import pandas as pd
import requests
import re

# 1. Authenticate using GitHub Secrets (No Google Colab popup needed)
credentials_dict = json.loads(os.environ["GCP_CREDENTIALS_JSON"])
gc = gspread.service_account_from_dict(credentials_dict)

# Open Google Sheet by its ID
spreadsheet = gc.open_by_key("1Uj72MCqn26u6v0A_g720k_sXg2OJQ1nR2VeNOlMCH60")
worksheet = spreadsheet.sheet1

# 2. Scrape the SBM Dashboard
url = "https://sbm.gov.in/sbmgdashboard/statesdashboard.aspx"
response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
lines = [
    re.sub(r"\s+", " ", x).strip() for x in soup.get_text("\n").splitlines() if x.strip()
]


# =========================================================
# FUNCTIONS
# =========================================================
def is_number(text):
  return bool(re.fullmatch(r"\+?\s*[\d,]+(?:\.\d+)?\s*\*?", text.strip()))


def clean_number(text):
  return re.sub(r"[+,* ]", "", text)


def get_values_after(lines, index, count=4):
  values = []
  for x in lines[index + 1 : index + 1 + count]:
    if is_number(x):
      values.append(x)
    elif values:
      break
  change, total = "", ""
  if len(values) >= 2:
    change = clean_number(values[0])
    total = clean_number(values[1])
  elif len(values) == 1:
    total = clean_number(values[0])
  return change, total


# =========================================================
# DATA STORAGE & EXTRACTION
# =========================================================
data = []


def add(indicator, change, total):
  data.append({"Indicator": indicator, "Change": change, "Total": total})


unique_metrics = [
    "Total Districts",
    "Total Blocks",
    "Total Gram Panchayats",
    "SBM Villages",
    "ODF Plus Villages",
    "Villages having arrangement of Solid Waste Management",
    "Villages having arrangement of Liquid Waste Management",
    "Community Compost pits",
    "Waste collection & Segregation sheds",
    "Vehicles for collection and Transportation of waste",
    "Community Soak/Leach/Magic pits",
    "Drainage facility",
    "Phytorid/ DEWATS/ Wetlands/ Duckweed Pond",
    "WSP 3/5 Pond System",
    "Faecal Sludge Management Plant",
    "Plastic Waste Management Unit",
    "Community Sanitary Complexes",
    "Household Toilets constructed",
    "Soak/Leach/Magic Pit at HH Level",
    "Kitchen Garden at HH Level",
    "Bio gas plants at HH Level",
    "Compost Pits at HH Level",
]

for metric in unique_metrics:
  for i, line in enumerate(lines):
    if line.lower() == metric.lower():
      change, total = get_values_after(lines, i)
      if total:
        add(metric, change, total)
      break

model_indexes = [i for i, line in enumerate(lines) if line.lower() == "odf plus model"]
if len(model_indexes) >= 1:
  i = model_indexes[0]
  change, total = get_values_after(lines, i)
  add("ODF Plus Model", change, total)

for i, line in enumerate(lines):
  if "1st Verfication" in line:
    change, total = get_values_after(lines, i)
    if total:
      add("ODF Plus Model (1st Verfication)", change, total)
  elif "2nd Verfication" in line:
    change, total = get_values_after(lines, i)
    if total:
      add("ODF Plus Model (2nd Verfication)", change, total)

for i, line in enumerate(lines):
  if line.lower() == "districts":
    for j in range(i + 1, min(i + 10, len(lines))):
      if lines[j].lower() == "odf plus" and j + 1 < len(lines) and is_number(lines[j + 1]):
        add("Districts - ODF Plus", "", clean_number(lines[j + 1]))
      if lines[j].lower() == "odf plus model" and j + 1 < len(lines) and is_number(lines[j + 1]):
        add("Districts - ODF Plus Model", "", clean_number(lines[j + 1]))
    break

for i, line in enumerate(lines):
  if line.lower() == "blocks":
    for j in range(i + 1, min(i + 10, len(lines))):
      if lines[j].lower() == "odf plus" and j + 1 < len(lines) and is_number(lines[j + 1]):
        add("Blocks - ODF Plus", "", clean_number(lines[j + 1]))
      if lines[j].lower() == "odf plus model" and j + 1 < len(lines) and is_number(lines[j + 1]):
        add("Blocks - ODF Plus Model", "", clean_number(lines[j + 1]))
    break

for i, line in enumerate(lines):
  if line.lower() == "gram panchyats":
    for j in range(i + 1, min(i + 10, len(lines))):
      if lines[j].lower() == "odf plus" and j + 1 < len(lines) and is_number(lines[j + 1]):
        add("Gram Panchyats - ODF Plus", "", clean_number(lines[j + 1]))
      if lines[j].lower() == "odf plus model" and j + 1 < len(lines) and is_number(lines[j + 1]):
        add("Gram Panchyats - ODF Plus Model", "", clean_number(lines[j + 1]))
    break

for i, line in enumerate(lines):
  if line.lower() == "total number of biogas plants (sbm-g)":
    for j in range(i + 1, min(i + 10, len(lines))):
      if lines[j].lower() == "registered" and j + 1 < len(lines):
        add("Total Number of Biogas Plants (SBM-G) Registered", "", clean_number(lines[j + 1]))
      elif lines[j].lower() == "functional" and j + 1 < len(lines):
        add("Total Number of Biogas Plants (SBM-G) Functional", "", clean_number(lines[j + 1]))
    break

df = pd.DataFrame(data)
df = df.drop_duplicates(subset=["Indicator"], keep="first").reset_index(drop=True)
df = df[["Indicator", "Total"]]

current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
date_row = pd.DataFrame({"Indicator": ["Date"], "Total": [current_datetime]})
df = pd.concat([date_row, df], ignore_index=True)

desired_order = [
    "Date",
    "Total Districts",
    "Districts - ODF Plus",
    "Districts - ODF Plus Model",
    "Total Blocks",
    "Blocks - ODF Plus",
    "Blocks - ODF Plus Model",
    "Total Gram Panchayats",
    "Gram Panchyats - ODF Plus",
    "Gram Panchyats - ODF Plus Model",
    "SBM Villages",
    "ODF Plus Villages",
    "ODF Plus Model",
    "ODF Plus Model (1st Verfication)",
    "ODF Plus Model (2nd Verfication)",
    "Villages having arrangement of Solid Waste Management",
    "Villages having arrangement of Liquid Waste Management",
    "Community Compost pits",
    "Waste collection & Segregation sheds",
    "Vehicles for collection and Transportation of waste",
    "Community Soak/Leach/Magic pits",
    "Drainage facility",
    "Phytorid/ DEWATS/ Wetlands/ Duckweed Pond",
    "WSP 3/5 Pond System",
    "Total Number of Biogas Plants (SBM-G) Registered",
    "Total Number of Biogas Plants (SBM-G) Functional",
    "Faecal Sludge Management Plant",
    "Plastic Waste Management Unit",
    "Community Sanitary Complexes",
    "Household Toilets constructed",
    "Soak/Leatch/Magic Pit at HH Level",
    "Kitchen Garden at HH Level",
    "Bio gas plants at HH Level",
    "Compost Pits at HH Level",
]

df["sort_order"] = df["Indicator"].map({name: i for i, name in enumerate(desired_order)})
df = df.sort_values("sort_order").drop(columns="sort_order").reset_index(drop=True)

df = df[["Indicator", "Total"]]
df_transposed = df.set_index("Indicator").T

# =========================================================
# PUSH TO GOOGLE SHEETS
# =========================================================
headers = df_transposed.columns.tolist()
row = df_transposed.iloc[0].tolist()

existing_data = worksheet.get_all_values()

if not existing_data:
  worksheet.update(f"A1", [headers], value_input_option="USER_ENTERED")
  worksheet.update(f"A2", [row], value_input_option="USER_ENTERED")
  next_row = 2
else:
  next_row = len(existing_data) + 1
  if next_row == 1:
    worksheet.update(f"A1", [headers], value_input_option="USER_ENTERED")
    next_row = 2
  worksheet.update(f"A{next_row}", [row], value_input_option="USER_ENTERED")

print(f"✅ Data pushed to row {next_row}")
