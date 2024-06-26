# How to enable Python Sheets API.
This is a tutorial on how to enable the Google Sheets API for Python. You can pull data without this API, but to push data, you'll need to use this.

## Step 1: Enable the API in the console.

Use [this link](https://console.cloud.google.com/flows/enableapi?apiid=sheets.googleapis.com) to get to the Google Cloud console and enable the Python API. If this gets you to some type of error, make sure you set up your account as a Google Cloud user, and come back to this link.

Also make sure you've set up a separate project just for this. I called mine CE-Sheets, but you're welcome to whatever naming convention you'd like. Ensure that the project that's pulled up is the one you've created, then select enable.

![cesheets-0-gif](https://github.com/andykasen13/CE-Assistant-v2/assets/89205919/ac347904-9cbe-489e-aa2a-ee030545c3fe)

## Step 2: Set up your OAuth 2.0 Screen
Now you need to make your OAuth Screen. Unfortunately, the video I took was too long, but you can find it here (REMEMBER TO PUT IT HERE). Go to [this page](https://console.cloud.google.com/apis/credentials/consent) (make sure you're on the right account and on the right project). This will ask you to set up the OAuth Screen. 

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

![ezgif-1-83cddfe12d](https://github.com/andykasen13/CE-Assistant-v2/assets/89205919/3cc353f8-d8f6-4d52-9f6d-5ade5076321e)

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

