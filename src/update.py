import datetime
import json
import os
import sys

import dotenv
import gspread
import pandas as pd
import requests

if not os.environ.get("IS_DOCKER", False):
    dotenv.load_dotenv()


def get_maps(maps_sheet):
    maps_raw = maps_sheet.get_values()
    maps = []

    headers = maps_raw[0]

    splits = [i for i, x in enumerate(maps_raw[1]) if x == ""] + [len(maps_raw[1])]
    min = 0

    for split_ind in splits:
        source_col = min
        dest_cols = [i for i in range(min + 1, split_ind)]
        min = split_ind + 1

        for dest_col in dest_cols:
            curr_map = {row[source_col]: row[dest_col] for row in maps_raw[1:]}
            maps.append(
                {
                    "source_col": headers[source_col],
                    "dest_col": headers[dest_col],
                    "map": curr_map,
                }
            )

    return maps


def simplefin_to_dataframe(simplefin_data, maps):
    df = pd.DataFrame()

    for account in simplefin_data["accounts"]:
        name = f"{account['org']['name']} - {account['name']}"

        if len(account["transactions"]) == 0:
            continue

        transactions = (
            pd.json_normalize(account["transactions"])
            .assign(
                period=lambda x: pd.to_datetime(x["posted"], unit="s").dt.strftime(
                    "%Y.%m"
                )
            )
            .assign(
                posted=lambda x: pd.to_datetime(x["posted"], unit="s").dt.strftime(
                    "%m/%d/%Y"
                )
            )
            .assign(account=name)
        )

        df = pd.concat([df, transactions])

    if len(df) == 0:
        return df

    for map in maps:
        df[map["dest_col"]] = df[map["source_col"]].map(map["map"])

    df = df.replace({pd.NA: ""})

    return df


def update_worksheet(ws: gspread.Worksheet, subset, columns):
    last_col = chr(ord("A") + len(columns) - 1)
    ws_data = pd.DataFrame(ws.get_values(f"A2:{last_col}"), columns=columns)
    sf_data = subset.copy()

    new_data = (
        pd.concat([ws_data, sf_data])
        .loc[:, columns]
        .drop_duplicates(subset=["id"], keep="first")
        .assign(posted=lambda x: pd.to_datetime(x["posted"]).dt.strftime("%m/%d/%Y"))
        .sort_values(by=["posted", "account"], ascending=[False, True])
        .fillna("")
        .values.tolist()
    )

    ws.update(f"A2:{last_col}", new_data, value_input_option="USER_ENTERED")


def run_update(days_to_fetch):
    # load credentials
    gs_auth = json.load(
        open(os.path.join(os.environ.get("CONFIG_PATH"), "google_auth.json"))
    )
    sf_auth = json.load(
        open(os.path.join(os.environ.get("CONFIG_PATH"), "simplefin_auth.json"))
    )

    gs = gspread.service_account_from_dict(gs_auth)
    sh = gs.open_by_key(os.environ.get("SHEET_ID"))

    # load sheets
    try:
        template_sheet = sh.get_worksheet_by_id(int(os.environ.get("TEMPLATE_GID")))
        maps_sheet = sh.get_worksheet_by_id(int(os.environ.get("MAPS_GID")))
    except Exception as e:
        print("Template or maps sheet GID not found. Exiting update.py.")
        exit()

    # fetch data from SimpleFIN
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=days_to_fetch)
    mparams = {
        "start-date": str(int(start.timestamp())),
        "end-date": str(int(end.timestamp())),
    }
    res = requests.get(
        sf_auth["url"], auth=(sf_auth["username"], sf_auth["password"]), params=mparams
    )
    data = res.json()

    # transform response into dataframe
    maps = get_maps(maps_sheet)
    df = simplefin_to_dataframe(data, maps)

    # get columns to update
    columns = [c.strip() for c in os.environ.get("TEMPLATE_COLUMNS").split(",")]

    # update affected sheets
    worksheets = {s.title: s.id for s in sh.worksheets()}
    for period in sorted(set(df["period"])):
        subset = df.loc[df["period"] == period, :].reset_index(drop=True)

        if period in worksheets.keys():
            ws = sh.get_worksheet_by_id(worksheets[period])
        else:
            ws = sh.duplicate_sheet(
                template_sheet.id, insert_sheet_index=1, new_sheet_name=period
            )
            worksheets[period] = ws.id

        update_worksheet(ws, subset, columns)

    print(f"Completed {days_to_fetch} day update at {datetime.datetime.now()}.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    else:
        days = 1
    run_update(days)
