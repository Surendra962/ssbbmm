from datetime import datetime
import json
import os
from bs4 import BeautifulSoup
import gspread
import pandas as pd
import requests
import re


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
# 2. SCRAPE SBM DASHBOARD
# =========================================================

url = "https://sbm.gov.in/sbmgdashboard/statesdashboard.aspx"

response = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(
    response.text,
    "html.parser"
)

lines = [
    re.sub(r"\s+", " ", x).strip()
    for x in soup.get_text("\n").splitlines()
    if x.strip()
]


# =========================================================
# FUNCTIONS
# =========================================================

def is_number(text):
    return bool(
        re.fullmatch(
            r"\+?\s*[\d,]+(?:\.\d+)?\s*\*?",
            text.strip()
        )
    )


def clean_number(text):
    return re.sub(
        r"[+,* ]",
        "",
        text
    )


def get_values_after(lines, index, count=4):

    values = []

    for x in lines[
        index + 1 :
        index + 1 + count
    ]:

        if is_number(x):
            values.append(x)

        elif values:
            break

    change = ""
    total = ""

    if len(values) >= 2:

        change = clean_number(
            values[0]
        )

        total = clean_number(
            values[1]
        )

    elif len(values) == 1:

        total = clean_number(
            values[0]
        )

    return change, total


# =========================================================
# DATA STORAGE
# =========================================================

data = []


def add(indicator, change, total):

    data.append({
        "Indicator": indicator,
        "Change": change,
        "Total": total
    })


# =========================================================
# 3. TEXT-BASED INDICATORS
# =========================================================

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

            change, total = get_values_after(
                lines,
                i
            )

            if total:

                add(
                    metric,
                    change,
                    total
                )

            break


# =========================================================
# 4. ODF PLUS MODEL
# =========================================================

model_indexes = [
    i
    for i, line in enumerate(lines)
    if line.lower() == "odf plus model"
]

if len(model_indexes) >= 1:

    i = model_indexes[0]

    change, total = get_values_after(
        lines,
        i
    )

    add(
        "ODF Plus Model",
        change,
        total
    )


# =========================================================
# 5. DISTRICTS
# =========================================================

for i, line in enumerate(lines):

    if line.lower() == "districts":

        for j in range(
            i + 1,
            min(i + 10, len(lines))
        ):

            if (
                lines[j].lower() == "odf plus"
                and
                j + 1 < len(lines)
                and
                is_number(lines[j + 1])
            ):

                add(
                    "Districts - ODF Plus",
                    "",
                    clean_number(
                        lines[j + 1]
                    )
                )

            if (
                lines[j].lower() == "odf plus model"
                and
                j + 1 < len(lines)
                and
                is_number(lines[j + 1])
            ):

                add(
                    "Districts - ODF Plus Model",
                    "",
                    clean_number(
                        lines[j + 1]
                    )
                )

        break


# =========================================================
# 6. BLOCKS
# =========================================================

for i, line in enumerate(lines):

    if line.lower() == "blocks":

        for j in range(
            i + 1,
            min(i + 10, len(lines))
        ):

            if (
                lines[j].lower() == "odf plus"
                and
                j + 1 < len(lines)
                and
                is_number(lines[j + 1])
            ):

                add(
                    "Blocks - ODF Plus",
                    "",
                    clean_number(
                        lines[j + 1]
                    )
                )

            if (
                lines[j].lower() == "odf plus model"
                and
                j + 1 < len(lines)
                and
                is_number(lines[j + 1])
            ):

                add(
                    "Blocks - ODF Plus Model",
                    "",
                    clean_number(
                        lines[j + 1]
                    )
                )

        break


# =========================================================
# 7. GRAM PANCHAYATS
# =========================================================

for i, line in enumerate(lines):

    if line.lower() == "gram panchyats":

        for j in range(
            i + 1,
            min(i + 10, len(lines))
        ):

            if (
                lines[j].lower() == "odf plus"
                and
                j + 1 < len(lines)
                and
                is_number(lines[j + 1])
            ):

                add(
                    "Gram Panchyats - ODF Plus",
                    "",
                    clean_number(
                        lines[j + 1]
                    )
                )

            if (
                lines[j].lower() == "odf plus model"
                and
                j + 1 < len(lines)
                and
                is_number(lines[j + 1])
            ):

                add(
                    "Gram Panchyats - ODF Plus Model",
                    "",
                    clean_number(
                        lines[j + 1]
                    )
                )

        break


# =========================================================
# 8. BIOGAS PLANTS
# =========================================================

for i, line in enumerate(lines):

    if (
        line.lower()
        ==
        "total number of biogas plants (sbm-g)"
    ):

        for j in range(
            i + 1,
            min(i + 10, len(lines))
        ):

            if (
                lines[j].lower()
                ==
                "registered"
                and
                j + 1 < len(lines)
            ):

                add(
                    "Total Number of Biogas Plants (SBM-G) Registered",
                    "",
                    clean_number(
                        lines[j + 1]
                    )
                )

            elif (
                lines[j].lower()
                ==
                "functional"
                and
                j + 1 < len(lines)
            ):

                add(
                    "Total Number of Biogas Plants (SBM-G) Functional",
                    "",
                    clean_number(
                        lines[j + 1]
                    )
                )

        break


# =========================================================
# 9. NEW: EXTRACT 3 INDICATORS DIRECTLY BY HTML ID
# =========================================================

id_mapping = {

    "ContentPlaceHolder1_lblModelVerified":
        "ODF Plus Model (1st Verification)",

    "ContentPlaceHolder1_lblModelVerified2ndLevel":
        "ODF Plus Model (2nd Verification)",

    "ContentPlaceHolder1_lblHHVehiclescoll":
        "Vehicles for Collection and Transportation of Waste"
}


for html_id, indicator in id_mapping.items():

    element = soup.find(
        id=html_id
    )

    if element:

        value = element.get_text(
            strip=True
        )

        value = clean_number(
            value
        )

        add(
            indicator,
            "",
            value
        )

    else:

        print(
            f"⚠️ ID not found: {html_id}"
        )


# =========================================================
# 10. CREATE DATAFRAME
# =========================================================

df = pd.DataFrame(data)

df = df.drop_duplicates(
    subset=["Indicator"],
    keep="first"
).reset_index(drop=True)

df = df[
    ["Indicator", "Total"]
]


# =========================================================
# 11. ADD DATE
# =========================================================

current_datetime = datetime.now().strftime(
    "%d-%m-%Y %H:%M:%S"
)

date_row = pd.DataFrame({
    "Indicator": ["Date"],
    "Total": [current_datetime]
})

df = pd.concat(
    [date_row, df],
    ignore_index=True
)


# =========================================================
# 12. DESIRED ORDER
# =========================================================

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

    "ODF Plus Model (1st Verification)",

    "ODF Plus Model (2nd Verification)",

    "Villages having arrangement of Solid Waste Management",

    "Villages having arrangement of Liquid Waste Management",

    "Community Compost pits",

    "Waste collection & Segregation sheds",

    "Vehicles for Collection and Transportation of Waste",

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


# =========================================================
# 13. SORT
# =========================================================

df["sort_order"] = df["Indicator"].map(
    {
        name: i
        for i, name in enumerate(
            desired_order
        )
    }
)

df = (
    df
    .sort_values("sort_order")
    .drop(columns="sort_order")
    .reset_index(drop=True)
)


df = df[
    ["Indicator", "Total"]
]


# =========================================================
# 14. TRANSPOSE
# =========================================================

df_transposed = (
    df
    .set_index("Indicator")
    .T
)


# =========================================================
# 15. PUSH TO GOOGLE SHEETS
# =========================================================

headers = (
    df_transposed
    .columns
    .tolist()
)

row = (
    df_transposed
    .iloc[0]
    .tolist()
)


existing_data = worksheet.get_all_values()


if not existing_data:

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

    next_row = len(
        existing_data
    ) + 1

    worksheet.update(
        f"A{next_row}",
        [row],
        value_input_option="USER_ENTERED"
    )


print(
    f"✅ Data pushed to row {next_row}"
)
