# How to enable Python Sheets API.
This is a tutorial on how to enable the Google Sheets API for Python. You can pull data without this API, but to push data, you'll need to use this. Thank you to [Schmole](https://github.com/Schmoley2) for showing me how to do this!

## Step 1: Enable the API in the console.

Use [this link](https://console.cloud.google.com/flows/enableapi?apiid=sheets.googleapis.com) to get to the Google Cloud console and enable the Python API. If this gets you to some type of error, make sure you set up your account as a Google Cloud user, and come back to this link.

Also make sure you've set up a separate project just for this. I called mine CE-Sheets, but you're welcome to whatever naming convention you'd like. Ensure that the project that's pulled up is the one you've created, then select enable.

![cesheets-0-gif](https://github.com/andykasen13/CE-Assistant-v2/assets/89205919/ac347904-9cbe-489e-aa2a-ee030545c3fe)

## Step 2: Set up your OAuth 2.0 Screen
Now you need to make your OAuth Screen. Unfortunately, the video I took was too long, but you can find it [here](https://youtu.be/tyl_PCsl3kU). NOTE: In this video, I start with [this link](https://console.cloud.google.com/apis/credentials), but the link below will get you to the same screen.

Go to [this page](https://console.cloud.google.com/apis/credentials/consent) (make sure you're on the right account and on the right project). This will ask you to set up the OAuth Screen. 

1. Select External on the first page and hit 'Create'.
2. For the 'App Name', pick whatever you want. I chose 'Web Client 1'. For the user support email, choose your email (it should already be an option). Ignore 'App Logo' and 'App Domain', and scroll to 'Developer contact information'. Put in your email address again. Click 'Save and continue'.
3. Nothing is important on this 'Scopes' page. Scroll to the bottom and click 'Save and continue'.
4. On the Test Users screen, click 'Add user' and enter your own email address. Click 'Add' and then 'Save and continue'.

You've now configured your OAuth Screen.

## Step 3: Getting your credentials.
We need to get credentials for our script to actually use. Go to [this page](https://console.cloud.google.com/apis/credentials) (and again, make sure you're still on the right account and on the right project!!)

1. Click 'Create Credentials' at the top, and select 'OAuth client ID'.
2. For Application Type, select 'Web application'. Leave the name as whatever it says, and scroll down to select 'Create'. (side note: you may be able to skip step 5 by adding `http://localhost:3000/` to 'Authorized redirect URLs', but I cannot confirm this.)
3. **Wait!** Don't click away yet. Click the 'Download JSON' button, and save it to your Downloads folder.

![gif2-setcredentials](https://github.com/andykasen13/CE-Assistant-v2/assets/89205919/3cc353f8-d8f6-4d52-9f6d-5ade5076321e)

## Step 4: Add credentials to project.
We need to add the credentials to the local folder for your Python script. Move the file you just downloaded to same folder as your current Python code. Rename this credentials file `credentials.json`. 

You'll need to `pip install` some stuff, so write the following in your terminal: `pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib`

Now, add the following code to your script:

```
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

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

        # this is commented out for now, so we can get our token - but later, we'll uncomment this so we can actually push to Google Sheets
        """
        # put it in
        sheet = service.spreadsheets()
        result = sheet.values().update(spreadsheetId=PERSONAL_SHEET_ID, # This is the ID of the Google Sheet you'd like to push to.
                                       range=range_name,
                                       valueInputOption="USER_ENTERED",
                                       body={"values" : valueData}
                                       ).execute()
        """
    except HttpError as err :
        print(err)

dump_to_sheet('','')
```

## Step 5: Set localhost:3000
(If you tried the additional instruction in Step 3, you may be able to skip this step, but I'm not sure.)

Go back to the [credentials page](https://console.cloud.google.com/apis/credentials). Navigate to the OAuth 2.0 Client IDs table, and click on the ID you set up earlier (I left it as the default 'Web client 1', but you may have changed it).

Scroll down to 'Authorized redirect URLs', and click 'Add url'. Type in `http://localhost:3000/`, and hit enter. This should send you back to the main credentials page.

![gif4-authorizeurl](https://github.com/andykasen13/CE-Assistant-v2/assets/89205919/aefb162b-61aa-43de-b6e2-705a9d2ce80b)

## Step 6: Get your token file.
Now you'll be getting your token for accessing the Google Sheets API. Run the code you just set up. 

This will take you to your web browser, where you'll choose an account. **Click the one you used to set up the project**, which should be the same one you added as a 'Test User' in Step 2.

It will take you to another page, where it asks whether or not you trust the app. Click 'Continue'. If it works, you should see a "The authentication flow has completed. You may close this window." Close the window.

![ezgif-4-96100f0e43](https://github.com/andykasen13/CE-Assistant-v2/assets/89205919/cabf86c4-1e67-4fbd-9dac-688ad77a3cf6)

## Final Check
Just to be sure it worked, check the directory your Python script and `credentials.json` exist in. If `token.json` is there, you're all set!!

# Actually using the function
To use the function, uncomment the lines we commented out. Pass the data you want to push to the sheet as a 2D array (each inner array is a row, each value within the inner array exists in order of the columns). For example,

| Month    | Savings |
| -------- | ------- |
| January  | $250    |
| February | $80     |
| March    | $420    |

would be passed as
`[["Month", "Savings"], ["January", "$250"], ["February", "$80"], ["March", "$420"]]`.

To set tab you want to send the data to, pass in `range_name` as "[Sheet Name]![Sheet Range]" (e.g. `"Sheet7!A1:E"`).

# Reading data from Google Sheets
We previously used `pandas` to grab the data from a Google Sheet, but this method is much quicker and much clearer. Like dumping, retrieving data this way will return a 2D array, with all values being strings and empty values being empty strings.

I personally took the first half of the write function and made it its own function, called `validate_credentials()`, that returns the credentials if `token.json` exists, and `None` otherwise. Here's my code.

```
def validate_credentials() :
    """Makes sure the token is still intact. Returns `creds`."""
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
    return creds
```

## Reading function
I took most of this straight from [Google's own guide](https://developers.google.com/sheets/api/quickstart/python). However, I made it a function that takes in a `range_name` (see above for syntax) and the `sheet_id`. I personally recommend keeping your sheet IDs as constants in your Python file (constants are denoted as variables in all caps). 

As I said above, the Sheet ID is the string after "https://docs.google.com/spreadsheets/d/" in your Google Sheet link. For example, in "https://docs.google.com/spreadsheets/d/11v1hvHphBGW_26gCxM4-DttZSId5Hvz-RPretD3VHK4/edit?gid=0#gid=0", "11v1hvHphBGW_26gCxM4-DttZSId5Hvz-RPretD3VHK4" is my Sheet ID.

This function returns a 2D array of values within the range specified. You should note that if you set your sheet range to include all rows (e.g. Sheet1!A1:D), it will stop returning values once there is no more data left. Meaning, if you have 11 rows of data, you will only get 11 arrays - not 1000.

```
def get_sheet_data(range_name : str, sheet_id : str) :
    creds = validate_credentials()

    try:
        service = build("sheets", "v4", credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=sheet_id, range=range_name)
            .execute()
        )
        values = result.get("values", [])

        if not values:
            print("No data found.")
            return None
    
        return values

    except HttpError as err:
        print(err)
```
