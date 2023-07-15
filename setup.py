import base64
import json
import os

import dotenv
import gspread
import requests

env = dotenv.dotenv_values()

###
# SimpleFIN setup
###
print("Setting up SimpleFIN credentials...")
sf_token = env["SIMPLEFIN_BRIDGE_TOKEN"]
res = requests.post(base64.b64decode(sf_token))

if res.status_code != 200:
    print(
        "SimpleFIN setup token invalid. Has it been used already? If so, delete the token from your account, generate a new one, and update .env."
    )
    exit()
else:
    print("SimpleFIN setup token valid. Saving access credentials.")

access_url = res.text
scheme, rest = access_url.split("//", 1)
auth, rest = rest.split("@", 1)
url = scheme + "//" + rest + "/accounts"
username, password = auth.split(":", 1)

simplefin_data = {"url": url, "username": username, "password": password}

# Save SimpleFIN access credentials to config file
with open(os.path.join(env["CONFIG_PATH"], "simplefin_auth.json"), "w+") as f:
    f.write(json.dumps(simplefin_data))
    print("SimpleFIN setup complete.")

###
# Google Sheets setup
###
print("Validating Google Sheets config...")
try:
    gc = gspread.service_account(
        filename=os.path.join(env["CONFIG_PATH"], "google_auth.json")
    )
    print("Google Sheets API access validated.")
except Exception as e:
    print(
        "Google Sheets API access invalid. Please check your credentials and try again. Specific setup information is available in the README."
    )
    exit()

try:
    sh = gc.open_by_key(env["SHEET_ID"])
except Exception as e:
    print(
        "Specified sheet ID invalid. Has the sheet been shared with the service account client email?"
    )
    exit()

print("Google Sheets config validated.")

print("Setup complete!")
