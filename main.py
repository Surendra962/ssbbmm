import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
import os
import gspread


# =========================================================
# 1. GOOGLE SHEETS AUTHENTICATION
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

worksheet = spreadsheet.get_worksheet(0)

print("\n========================================")
print("GOOGLE SHEETS")
print("========================================")
print("Spreadsheet :", spreadsheet.title)
print("Worksheet   :", worksheet.title)
print("URL         :", spreadsheet.url)


# =========================================================
# 2. GET SBM(G) DASHBOARD
# =========================================================

url = "https://sbm.gov.in/sbmgdashboard/statesdashboard.aspx"

response = requests.get(
    url,
    headers={
        "User-Agent": "Mozilla/5.0"
    },
    timeout=30
)

response.raise_for_status()

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

print("\n========================================")
print("SBM(G) DASHBOARD")
print("========================================")
print("Dashboard loaded.")
print("Text length:", len(text))


# =========================================================
# 3. GENERIC NUMBER CLEANER
# =========================================================

def clean_number(value):

    if value is None:
        return None

    value = str(value)

    value = value.replace(",", "")
    value = value.strip()

    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


# =========================================================
# 4. GENERIC INDICATOR EXTRACTION
# =========================================================

def get_value(label):

    pattern = (
        rf"{re.escape(label)}"
        r"\s*(?:\+\s*)?"
        r"([\d,]+)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    return clean_number(
        match.group(1)
    )


# =========================================================
# 5. INDICATORS
# =========================================================

indicators = [

    # -----------------------------------------
    # BASIC COVERAGE
    # -----------------------------------------

    "Total Districts",
    "Total Blocks",
    "Total Gram Panchayats",
    "SBM Villages",

    # -----------------------------------------
    # ODF PLUS
    # -----------------------------------------

    "ODF Plus Villages",
    "ODF Plus Model",

    # -----------------------------------------
    # WASTE MANAGEMENT
    # -----------------------------------------

    "Villages having arrangement of Solid Waste Management",
    "Villages having arrangement of Liquid Waste Management",

    # -----------------------------------------
    # COMMUNITY ASSETS
    # -----------------------------------------

    "Community Compost pits",
    "Waste collection & Segregation sheds",
    "Vehicles for collection and Transportation of waste",
    "Community Soak/Leach/Magic pits",
    "Drainage facility",
    "Phytorid/ DEWATS/ Wetlands/ Duckweed Pond",
    "WSP 3/5 Pond System",

    # -----------------------------------------
    # OTHER ASSETS
    # -----------------------------------------

    "Faecal Sludge Management Plant",
    "Plastic Waste Management Unit",
    "Community Sanitary Complexes",
    "Household Toilets constructed",

    # -----------------------------------------
    # HOUSEHOLD SLWM
    # -----------------------------------------

    "Soak/Leach/Magic Pit at HH Level",
    "Kitchen Garden at HH Level",
    "Bio gas plants at HH Level",
    "Compost Pits at HH Level"
]


# =========================================================
# 6. EXTRACT STANDARD INDICATORS
# =========================================================

data = []

print("\n========================================")
print("EXTRACTING INDICATORS")
print("========================================")

for indicator in indicators:

    value = get_value(indicator)

    if value is not None:

        data.append([
            indicator,
            value
        ])

        print(
            f"✓ {indicator}: {value:,}"
        )

    else:

        print(
            f"✗ {indicator}: NOT FOUND"
        )


# =========================================================
# 7. ODF PLUS STATUS
# =========================================================

status_patterns = {

    "Districts - ODF Plus": (
        r"Districts\s+ODF Plus\s+([\d,]+)"
    ),

    "Districts - ODF Plus Model": (
        r"Districts\s+ODF Plus\s+[\d,]+"
        r"\s+ODF Plus Model\s+([\d,]+)"
    ),

    "Blocks - ODF Plus": (
        r"Blocks\s+ODF Plus\s+([\d,]+)"
    ),

    "Blocks - ODF Plus Model": (
        r"Blocks\s+ODF Plus\s+[\d,]+"
        r"\s+ODF Plus Model\s+([\d,]+)"
    ),

    "Gram Panchyats - ODF Plus": (
        r"Gram Panchyats\s*-?\s*ODF Plus\s+([\d,]+)"
    ),

    "Gram Panchyats - ODF Plus Model": (
        r"Gram Panchyats\s*-?\s*ODF Plus\s+[\d,]+"
        r"\s+ODF Plus Model\s+([\d,]+)"
    )
}


print("\n========================================")
print("ODF PLUS STATUS")
print("========================================")


for indicator, pattern in status_patterns.items():

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:

        value = clean_number(
            match.group(1)
        )

        data.append([
            indicator,
            value
        ])

        print(
            f"✓ {indicator}: {value:,}"
        )

    else:

        print(
            f"✗ {indicator}: NOT FOUND"
        )


# =========================================================
# 8. BIOGAS PLANTS
# =========================================================

biogas_pattern = (
    r"Total Number of Biogas Plants\s*\(SBM-G\)"
    r".*?Registered\s+([\d,]+)"
    r".*?Functional\s+([\d,]+)"
)

match = re.search(
    biogas_pattern,
    text,
    re.IGNORECASE
)

print("\n========================================")
print("BIOGAS PLANTS")
print("========================================")

if match:

    registered = clean_number(
        match.group(1)
    )

    functional = clean_number(
        match.group(2)
    )

    data.extend([
        [
            "Biogas Plants - Registered",
            registered
        ],
        [
            "Biogas Plants - Functional",
            functional
        ]
    ])

    print(
        f"✓ Biogas Plants - Registered: "
        f"{registered:,}"
    )

    print(
        f"✓ Biogas Plants - Functional: "
        f"{functional:,}"
    )

else:

    print(
        "✗ Biogas Plants: NOT FOUND"
    )


# =========================================================
# 9. ODF PLUS MODEL VERIFICATION
# =========================================================

verification_patterns = {

    "ODF Plus Model (1st Verification)": (
        r"ODF Plus Model\s*"
        r"\(\s*1\s*st\s+Verfication\s*\)"
        r".*?([\d,]+)"
    ),

    "ODF Plus Model (2nd Verification)": (
        r"ODF Plus Model\s*"
        r"\(\s*2\s*nd\s+Verfication\s*\)"
        r".*?([\d,]+)"
    )
}


print("\n========================================")
print("ODF PLUS MODEL VERIFICATION")
print("========================================")


for indicator, pattern in verification_patterns.items():

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:

        value = clean_number(
            match.group(1)
        )

        data.append([
            indicator,
            value
        ])

        print(
            f"✓ {indicator}: {value:,}"
        )

    else:

        print(
            f"✗ {indicator}: NOT FOUND"
        )


# =========================================================
# 10. CREATE DATAFRAME
# =========================================================

df = pd.DataFrame(
    data,
    columns=[
        "Indicator",
        "Value"
    ]
)


# =========================================================
# 11. REMOVE EMPTY VALUES
# =========================================================

df = df.dropna(
    subset=["Value"]
)


# =========================================================
# 12. REMOVE DUPLICATES
# =========================================================

df = df.drop_duplicates(
    subset="Indicator",
    keep="first"
)


# =========================================================
# 13. ADD DATE
# =========================================================

current_date = pd.Timestamp.now().strftime(
    "%Y-%m-%d %H:%M:%S"
)

df = pd.concat(
    [
        df,
        pd.DataFrame({
            "Indicator": ["Date"],
            "Value": [current_date]
        })
    ],
    ignore_index=True
)


# =========================================================
# 14. REQUIRED COLUMN ORDER
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
# 15. REORDER DATA
# =========================================================

df = (
    df
    .set_index("Indicator")
    .reindex(indicator_order)
)


# =========================================================
# 16. CONVERT TO ONE ROW
# =========================================================

headers = df.index.tolist()

row = df["Value"].tolist()


# =========================================================
# 17. CONVERT VALUES TO GOOGLE SHEETS SAFE VALUES
# =========================================================

headers = [
    str(x)
    for x in headers
]

row = [
    "" if pd.isna(x) else x
    for x in row
]


# =========================================================
# 18. SHOW FINAL DATA BEFORE UPLOAD
# =========================================================

print("\n========================================")
print("FINAL DATA")
print("========================================")

print(
    "Number of indicators:",
    len(headers)
)

for header, value in zip(headers, row):

    print(
        f"{header}: {value}"
    )


# =========================================================
# 19. CLEAR EXISTING GOOGLE SHEET
# =========================================================

print("\n========================================")
print("CLEARING GOOGLE SHEET")
print("========================================")

worksheet.clear()

print(
    "✓ Existing sheet data cleared."
)


# =========================================================
# 20. WRITE HEADERS
# =========================================================

worksheet.update(
    range_name="A1",
    values=[headers],
    value_input_option="USER_ENTERED"
)

print(
    "✓ Headers written to row 1."
)


# =========================================================
# 21. WRITE DATA
# =========================================================

worksheet.update(
    range_name="A2",
    values=[row],
    value_input_option="USER_ENTERED"
)

print(
    "✓ Dashboard data written to row 2."
)


# =========================================================
# 22. READ BACK FROM GOOGLE SHEETS
# =========================================================

print("\n========================================")
print("VERIFYING GOOGLE SHEET")
print("========================================")

written_data = worksheet.get(
    "A1:AZ2"
)

print(
    "Rows returned:",
    len(written_data)
)

if len(written_data) >= 2:

    print(
        "✓ Headers found."
    )

    print(
        "✓ Data row found."
    )

    print(
        "✓ Google Sheet write verified successfully."
    )

else:

    print(
        "❌ Data verification failed."
    )


# =========================================================
# 23. FINAL STATUS
# =========================================================

print("\n========================================")
print("SUCCESS")
print("========================================")

print(
    "✅ SBM(G) dashboard data uploaded."
)

print(
    "Spreadsheet:",
    spreadsheet.title
)

print(
    "Worksheet:",
    worksheet.title
)

print(
    "Columns:",
    len(headers)
)

print(
    "Date:",
    current_date
)

print(
    "Google Sheet:",
    spreadsheet.url
)

print("========================================")
