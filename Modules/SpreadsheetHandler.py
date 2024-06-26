"""
This module is for pushing and pulling information from Google Sheets.
Used Schmole's code to learn how to push to Google Sheets.
"""

import re
import pandas

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import Modules.CEAPIReader as CEAPIReader

import pickle
import asyncio

# ----------------------------- writing -----------------------------
PERSONAL_SHEET_ID = "1jvYRLshEu65s15NKLNmVxUeTFh-y73Ftd1Quy2uLs3M"
ROLL_INFO_GID = 1263165737
ROLL_INFO_RANGE_NAME = "Roll Info!A1:E"
PROVE_YOURSELF_GID = 1523840581
PROVE_YOURSELF_RANGE_NAME = "Prove Yourself (Fixed)!A2:E"

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


async def dump_prove_yourselves() :
    

    listy : list[list] = []

    # get the games
    database_name = await CEAPIReader.get_api_games_full()

    for game in database_name :
        for obj in game.all_objectives :
            if 'prove yourself' in obj.description.lower() :
                c = [
                    game.game_name, game.ce_id, f"https://cedb.me/game/{game.ce_id}", obj.name, obj.description
                ]
                listy.append(c)
    
    dump_to_sheet(listy, "Prove Yourself (Fixed)!A2:E")


def dump_to_sheet(valueData : list[list], range_name : str) :
    """Dumps the data from `valueData` onto the sheet range by `range_name`."""
    creds = None
    if os.path.exists("token.json") :
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid :
        if creds and creds.expired and creds.refresh_token :
            creds.refresh(Request())
        else :
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=3000)
        with open('token.json', 'w') as token :
            token.write(creds.to_json())
        
    try :
        # service
        service = build('sheets', 'v4', credentials=creds)

        # put it in
        sheet = service.spreadsheets()
        result = sheet.values().update(spreadsheetId=PERSONAL_SHEET_ID,
                                       range=range_name,
                                       valueInputOption="USER_ENTERED",
                                       body={"values" : valueData}
                                       ).execute()

    except HttpError as err :
        print(err)

asyncio.run(dump_prove_yourselves())
# ----------------------------- reading -----------------------------

async def __get_sheet_url(url : str) -> str :
    """Takes in the link to a Google Sheet and returns the .csv link."""
    # Regular expression to match and capture the necessary part of the URL
    pattern = r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)(/edit#gid=(\d+)|/edit.*)?'

    # Replace function to construct the new URL for CSV export
    # If gid is present in the URL, it includes it in the export URL, otherwise, it's omitted
    replacement = lambda m: f'https://docs.google.com/spreadsheets/d/{m.group(1)}/export?' + (f'gid={m.group(3)}&' if m.group(3) else '') + 'format=csv'

    # Replace using regex
    new_url = re.sub(pattern, replacement, url)

    return new_url

async def get_roles() -> list[tuple[str, str]] :
    """Returns the roles as a list of 2D tuples.\n
    The first entry is the name of the role, and the second entry is the description."""
    # define role link
    ROLE_LINK = "https://docs.google.com/spreadsheets/d/1BIxKr3vqiQ909u1xCZbJR-RgDdPBocoMafy0Ov7ep04/edit#gid=0"

    # grab the correct url
    new_url = await __get_sheet_url(ROLE_LINK)

    # read and slim the data as a .csv
    data_frame = pandas.read_csv(new_url)
    slimmed_df = data_frame.iloc[:, [2, 3]]

    # turn the DataFrame into a list of tuples
    final_data : list[tuple[str, str]] = []
    for index, row in slimmed_df.iterrows():
        final_data.append((str(row[0]), str(row[1])))
    return final_data

async def get_steamhunters() -> dict[str, int] :
    """
    Returns the SteamHunters average completion time as a list of 2D tuples.\n
    The first entry is the Steam App ID, and the second entry is the average completion time.
    """
    # define steamhunters link
    STEAMHUNTERS_LINK = "https://docs.google.com/spreadsheets/d/1oAUw5dZdqZa1FWqrBV9MQQTr8Eq8g33zwEb49vk3hrk/edit#gid=2053407537"

    # grab the correct url
    new_url = await __get_sheet_url(STEAMHUNTERS_LINK)

    # read and slim the data as a .csv
    data_frame = pandas.read_csv(new_url)
    slimmed_df : pandas.DataFrame = data_frame.iloc[:, ["sh_appid", "sh_median"]]

    # turn the DataFrame into a list of tuples
    final_data : dict[str, str] = {}
    for index, row in slimmed_df.iterrows():
        final_data[str(int(row["sh_appid"]))] = row['sh_median']
    return final_data