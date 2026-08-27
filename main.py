import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
import os
from datetime import datetime
import gspread


# =========================================================
# 1. AUTHENTICATE GOOGLE SHEETS
# =========================================================

credentials_dict = json.loads(
    os.environ["GCP_CREDENTIALS_JSON"]
)

gc = gspread.service_account_from_dict(
    credentials_dict
)

spreadsheet = gc.open_by_key(
    "1Uj72MCqn26u6v0A_g720k_sXg2OJQ1nR2VeNOlMCH60"
)

worksheet = spreadsheet.sheet1


# =========================================================
# 2. CONNECT TO SBM(G) DASHBOARD
# =========================================================

url = "https://sbm.gov.in/sbmgdashboard/statesdashboard.aspx"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}


# Create session with retry
session = requests.Session()

retry_strategy = Retry(
    total=5,
    connect=5,
    read=5,
    backoff_factor=5,
    status_forcelist=[
        429,
        500,
        502,
        503,
        504
    ],
    allowed_methods=["GET"],
    raise_on_status=False
)

adapter = HTTPAdapter(
    max_retries=retry_strategy
)

session.mount(
    "https://",
    adapter
)

session.mount(
    "http://",
    adapter
)


print("🔄 Connecting to SBM(G) dashboard...")


try:

    response = session.get(
        url,
        headers=headers,
        timeout=(90, 180)
    )

    response.raise_for_status()

    print(
        f"✅ SBM(G) dashboard connected — HTTP {response.status_code}"
    )

except requests.exceptions.RequestException as e:

    print(
        f"❌ SBM(G) dashboard connection failed: {e}"
    )

    raise SystemExit(
        "SBM(G) dashboard is currently unreachable "
        "from the GitHub Actions runner."
    )


# =========================================================
# 3. PARSE DASHBOARD
# =========================================================

soup = BeautifulSoup(
    response.text,
    "html.parser"
)

text = soup.get_text(
    " ",
    strip=True
)

text = re.sub(
    r"\s+",
    " ",
    text
)


# =========================================================
# 4. GENERIC VALUE EXTRACTION
# =========================================================

def get_value(label):

    pattern = (
        rf"{re.escape(label)}"
        r"\s*(?:\+\s*([\d,]+)\s*)?"
        r"([\d,]+)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    change = (
        int(
            match.group(1).replace(",", "")
        )
        if match.group(1)
        else 0
    )

    value = int(
        match.group(2).replace(",", "")
    )

    return change, value


# =========================================================
# 5. DATA STORAGE
# =========================================================

data = []


def add_data(indicator, change, value):

    if value is not None:

        data.append([
            indicator,
            change,
            value
        ])


# =========================================================
# 6. STANDARD INDICATORS
# =========================================================

indicators = [

    # Basic Coverage
    "Total Districts",
    "Total Blocks",
    "Total Gram Panchayats",
    "SBM Villages",

    # ODF Plus
    "Villages having arrangement of Solid Waste Management",
    "Villages having arrangement of Liquid Waste Management",

    # Community Assets
    "Community Compost pits",
    "Waste collection & Segregation sheds",
    "Vehicles for collection and Transportation of waste",
    "Community Soak/Leach/Magic pits",
    "Drainage facility",
    "Phytorid/ DEWATS/ Wetlands/ Duckweed Pond",
    "WSP 3/5 Pond System",

    # Other Assets
    "Faecal Sludge Management Plant",
    "Plastic Waste Management Unit",
    "Community Sanitary Complexes",
    "Household Toilets constructed",

    # Household SLWM Assets
    "Soak/Leach/Magic Pit at HH Level",
    "Kitchen Garden at HH Level",
    "Bio gas plants at HH Level",
    "Compost Pits at HH Level"
]


for indicator in indicators:

    result = get_value(indicator)

    if result:

        change, value = result

        add_data(
            indicator,
            change,
            value
        )


# =========================================================
# 7. ODF PLUS VILLAGES & ODF PLUS MODEL
# =========================================================

def extract_dashboard_value(label):

    pattern = (
        rf"{re.escape(label)}"
        r"\s*\+\s*[\d,]+"
        r"(?:\s*\*\s*)?"
        r"\s*([\d,]+)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    return int(
        match.group(1).replace(",", "")
    )


odf_plus_villages = extract_dashboard_value(
    "ODF Plus Villages"
)

odf_plus_model = extract_dashboard_value(
    "ODF Plus Model"
)


add_data(
    "ODF Plus Villages",
    0,
    odf_plus_villages
)

add_data(
    "ODF Plus Model",
    0,
    odf_plus_model
)


# =========================================================
# 8. ODF PLUS STATUS
#    DISTRICTS / BLOCKS / GRAM PANCHAYATS
# =========================================================

status_patterns = {

    "Districts": (
        r"Districts\s+ODF Plus\s+([\d,]+)"
        r"\s+ODF Plus Model\s+([\d,]+)"
    ),

    "Blocks": (
        r"Blocks\s+ODF Plus\s+([\d,]+)"
        r"\s+ODF Plus Model\s+([\d,]+)"
    ),

    "Gram Panchyats": (
        r"Gram Panchyats\s*-?\s*ODF Plus\s+([\d,]+)"
        r"\s+ODF Plus Model\s+([\d,]+)"
    )
}


for level, pattern in status_patterns.items():

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:

        odf_plus = int(
            match.group(1).replace(",", "")
        )

        odf_plus_model = int(
            match.group(2).replace(",", "")
        )

        add_data(
            f"{level} - ODF Plus",
            0,
            odf_plus
        )

        add_data(
            f"{level} - ODF Plus Model",
            0,
            odf_plus_model
        )


# =========================================================
# 9. BIOGAS & CBG PLANTS
# =========================================================

plant_patterns = {

    "Biogas Plants": (
        r"Total Number of Biogas Plants\s*\(SBM-G\)"
        r".*?Registered\s+([\d,]+)"
        r".*?Functional\s+([\d,]+)"
    ),

    "CBG Plants": (
        r"Total Number of CBG Plants"
        r".*?Registered\s+([\d,]+)"
        r".*?Functional\s+([\d,]+)"
    )
}


for plant, pattern in plant_patterns.items():

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:

        registered = int(
            match.group(1).replace(",", "")
        )

        functional = int(
            match.group(2).replace(",", "")
        )

        add_data(
            f"{plant} - Registered",
            0,
            registered
        )

        add_data(
            f"{plant} - Functional",
            0,
            functional
        )


# =========================================================
# 10. ODF PLUS MODEL VERIFICATION
# =========================================================

verification_patterns = {

    "ODF Plus Model (1st Verification)": (
        r"ODF Plus Model\s*\(\s*1\s*st\s+Verfication\s*\)"
        r"\s*(?:\+\s*([\d,]+))?\s*([\d,]+)"
    ),

    "ODF Plus Model (2nd Verification)": (
        r"ODF Plus Model\s*\(\s*2\s*nd\s+Verfication\s*\)"
        r"\s*(?:\+\s*([\d,]+))?\s*([\d,]+)"
    )
}


for indicator, pattern in verification_patterns.items():

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:

        change = (
            int(
                match.group(1).replace(",", "")
            )
            if match.group(1)
            else 0
        )

        value = int(
            match.group(2).replace(",", "")
        )

        add_data(
            indicator,
            change,
            value
        )


# =========================================================
# 11. CREATE DATAFRAME
# =========================================================

df = pd.DataFrame(
    data,
    columns=[
        "Indicator",
        "Daily_Change",
        "Value"
    ]
)


# =========================================================
# 12. REMOVE DUPLICATES & EMPTY VALUES
# =========================================================

df = (
    df
    .dropna(
        subset=["Value"]
    )
    .drop_duplicates(
        subset=["Indicator"],
        keep="first"
    )
    .reset_index(drop=True)
)


# =========================================================
# 13. KEEP ONLY INDICATOR & VALUE
# =========================================================

df = df[
    ["Indicator", "Value"]
].copy()


# =========================================================
# 14. ADD DATE & TIME
# =========================================================

date_row = pd.DataFrame({
    "Indicator": ["Date"],
    "Value": [
        datetime.now().strftime(
            "%d-%m-%Y %H:%M:%S"
        )
    ]
})

df = pd.concat(
    [
        date_row,
        df
    ],
    ignore_index=True
)


# =========================================================
# 15. REQUIRED INDICATOR ORDER
# =========================================================

indicator_order = [

    "Date",

    # Districts
    "Total Districts",
    "Districts - ODF Plus",
    "Districts - ODF Plus Model",

    # Blocks
    "Total Blocks",
    "Blocks - ODF Plus",
    "Blocks - ODF Plus Model",

    # Gram Panchayats
    "Total Gram Panchayats",
    "Gram Panchyats - ODF Plus",
    "Gram Panchyats - ODF Plus Model",

    # Villages / ODF Plus
    "SBM Villages",
    "ODF Plus Villages",
    "ODF Plus Model",
    "ODF Plus Model (1st Verification)",
    "ODF Plus Model (2nd Verification)",

    # Waste Management
    "Villages having arrangement of Solid Waste Management",
    "Villages having arrangement of Liquid Waste Management",

    # Community Assets
    "Community Compost pits",
    "Waste collection & Segregation sheds",
    "Vehicles for Collection and Transportation of Waste",
    "Community Soak/Leach/Magic pits",
    "Drainage facility",
    "Phytorid/ DEWATS/ Wetlands/ Duckweed Pond",
    "WSP 3/5 Pond System",

    # Biogas / CBG
    "Biogas Plants - Registered",
    "Biogas Plants - Functional",
    "CBG Plants - Registered",
    "CBG Plants - Functional",

    # Other Assets
    "Faecal Sludge Management Plant",
    "Plastic Waste Management Unit",
    "Community Sanitary Complexes",
    "Household Toilets constructed",

    # Household SLWM
    "Soak/Leach/Magic Pit at HH Level",
    "Kitchen Garden at HH Level",
    "Bio gas plants at HH Level",
    "Compost Pits at HH Level"
]


# =========================================================
# 16. REORDER
# =========================================================

df = (
    df
    .set_index("Indicator")
    .reindex(indicator_order)
)


# =========================================================
# 17. CONVERT TO ONE ROW
# =========================================================

df = df.T

df.index.name = None

df = df.reset_index(
    drop=True
)


# =========================================================
# 18. REMOVE ANY COMPLETELY EMPTY COLUMNS
# =========================================================

df = df.dropna(
    axis=1,
    how="all"
)


# =========================================================
# 19. PREPARE GOOGLE SHEET DATA
# =========================================================

headers = df.columns.tolist()

row = df.iloc[0].tolist()


# Convert pandas/numpy values to normal Python values
headers = [
    str(x)
    for x in headers
]

row = [
    "" if pd.isna(x) else x
    for x in row
]


# =========================================================
# 20. PUSH TO GOOGLE SHEETS
# =========================================================

existing_data = worksheet.get_all_values()


if not existing_data:

    # First run:
    # Row 1 = headers
    # Row 2 = data

    worksheet.update(
        "A1",
        [headers],
        value_input_option="USER_ENTERED"
    )

    worksheet.update(
        "A2",
        [row],
        value_input_option="USER_ENTERED"
    )

    next_row = 2

else:

    # Subsequent runs:
    # Append new data row

    next_row = len(existing_data) + 1

    worksheet.update(
        f"A{next_row}",
        [row],
        value_input_option="USER_ENTERED"
    )


# =========================================================
# 21. FINAL STATUS
# =========================================================

print(
    f"✅ SBM(G) dashboard data pushed successfully."
)

print(
    f"✅ Google Sheet row: {next_row}"
)

print(
    f"✅ Number of columns: {len(headers)}"
)

print(
    f"✅ Date: {row[0]}"
)
