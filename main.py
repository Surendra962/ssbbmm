import json
import os
import gspread


# =========================================================
# GOOGLE SHEETS WRITE TEST
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


print("Spreadsheet:", spreadsheet.title)
print("Worksheet:", worksheet.title)
print("URL:", spreadsheet.url)

# ---------------------------------------------------------
# Show service account being used
# ---------------------------------------------------------

print("\nService account:")
print(credentials_dict.get("client_email"))


# ---------------------------------------------------------
# Write a very simple test
# ---------------------------------------------------------

test_data = [
    ["TEST", "VALUE"],
    ["SBM TEST", "12345"]
]

worksheet.update(
    "A1",
    test_data,
    value_input_option="USER_ENTERED"
)


# ---------------------------------------------------------
# Read it back
# ---------------------------------------------------------

result = worksheet.get(
    "A1:B2"
)

print("\nData read back from Google Sheet:")
print(result)


if result == test_data:

    print("\n===================================")
    print("✅ GOOGLE SHEETS WRITE SUCCESSFUL")
    print("===================================")

else:

    print("\n===================================")
    print("❌ GOOGLE SHEETS WRITE FAILED")
    print("===================================")
