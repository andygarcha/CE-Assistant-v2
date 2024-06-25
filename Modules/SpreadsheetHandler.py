"""
This module is for pushing and pulling information from Google Sheets.
Used Schmole's code to learn how to push to Google Sheets.
"""

import re
import pandas

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