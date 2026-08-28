import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
import os
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
# 2. GET DASHBOARD DATA
# =========================================================

url = "https://sbm.gov.in/sbmgdashboard/statesdashboard.aspx"

response = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)
response.raise_for_status()

text = BeautifulSoup(
    response.text,
    "html.parser"
).get_text(
    " ",
    strip=True
)

text = re.sub(
    r"\s+",
    " ",
    text
)


# =========================================================
# 3. GENERIC EXTRACTION FUNCTION
# =========================================================

def get_value(label):

    pattern = (
        rf"{re.escape(label)}"
        r"\s*(?:\+\s*([\d,]+)\s*)?([\d,]+)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    change = (
        int(match.group(1).replace(",", ""))
        if match.group(1)
        else 0
    )

    value = int(
        match.group(2).replace(",", "")
    )

    return change, value


# =========================================================
# 4. STANDARD INDICATORS
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


# =========================================================
# 5. EXTRACT STANDARD INDICATORS
# =========================================================

data = []

for indicator in indicators:

    result = get_value(indicator)

    if result:

        change, value = result

        data.append([
            indicator,
            change,
            value
        ])


# =========================================================
# 6. ODF PLUS VILLAGES & ODF PLUS MODEL
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

    return (
        int(
            match.group(1).replace(",", "")
        )
        if match
        else None
    )


odf_plus_villages = extract_dashboard_value(
    "ODF Plus Villages"
)

odf_plus_model = extract_dashboard_value(
    "ODF Plus Model"
)

data.extend([
    [
        "ODF Plus Villages",
        0,
        odf_plus_villages
    ],
    [
        "ODF Plus Model",
        0,
        odf_plus_model
    ]
])


# =========================================================
# 7. ODF PLUS STATUS
#    Districts / Blocks / Gram Panchayats
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

        data.extend([
            [
                f"{level} - ODF Plus",
                0,
                odf_plus
            ],
            [
                f"{level} - ODF Plus Model",
                0,
                odf_plus_model
            ]
        ])


# =========================================================
# 8. BIOGAS & CBG PLANTS
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
    ),

    # Vehicles for collection and Transportation of waste
    "Vehicles": (
        r"Total Number of Vehicles\s*\(Collection & Transportation of Waste\)"
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

        vehicles = int(
            match.group(2).replace(",", "")
        )

        data.extend([
            [
                f"{plant} - Registered",
                0,
                registered
            ],
            [
                f"{plant} - Functional",
                0,
                functional
            ],
            [
                f"{plant} - Vehicles",
                0,
                vehicles
            ]
        ])


# =========================================================
# 9. ODF PLUS MODEL VERIFICATION
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

        data.append([
            indicator,
            change,
            value
        ])


# =========================================================
# 10. CREATE DATAFRAME
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
# 11. REMOVE DUPLICATES & EMPTY VALUES
# =========================================================

df = (
    df
    .dropna(
        subset=["Value"]
    )
    .drop_duplicates(
        subset="Indicator",
        keep="first"
    )
    .reset_index(
        drop=True
    )
)


# =========================================================
# 12. KEEP ONLY INDICATOR AND VALUE
# =========================================================

df = df[
    ["Indicator", "Value"]
].copy()


# =========================================================
# 13. ADD CURRENT DATE & TIME
# =========================================================

df = pd.concat(
    [
        df,
        pd.DataFrame({
            "Indicator": ["Date"],
            "Value": [
                pd.Timestamp.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ]
        })
    ],
    ignore_index=True
)


# =========================================================
# 14. REQUIRED INDICATOR ORDER
# =========================================================

indicator_order = [

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
    "ODF Plus Model (1st Verification)",
    "ODF Plus Model (2nd Verification)",

    "Villages having arrangement of Solid Waste Management",
    "Villages having arrangement of Liquid Waste Management",

    "Community Compost pits",
    "Waste collection & Segregation sheds",
    "Vehicles for collection and Transportation of waste",
    "Community Soak/Leach/Magic pits",
    "Drainage facility",
    "Phytorid/ DEWATS/ Wetlands/ Duckweed Pond",
    "WSP 3/5 Pond System",

    "Biogas Plants - Registered",
    "Biogas Plants - Functional",

    "Faecal Sludge Management Plant",
    "Plastic Waste Management Unit",
    "Community Sanitary Complexes",
    "Household Toilets constructed",

    "Soak/Leach/Magic Pit at HH Level",
    "Kitchen Garden at HH Level",
    "Bio gas plants at HH Level",
    "Compost Pits at HH Level"
]


# =========================================================
# 15. REORDER AND CONVERT TO ONE ROW
# =========================================================

df = (
    df
    .set_index("Indicator")
    .reindex(indicator_order)
    .dropna(how="all")
    .T
)

# Remove the index name "Indicator"
df.index.name = None

# Reset row index without creating any extra column
df = df.reset_index(
    drop=True
)


# =========================================================
# 16. PREPARE GOOGLE SHEET DATA
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
# 17. PUSH TO GOOGLE SHEETS
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
# 18. FINAL STATUS
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
