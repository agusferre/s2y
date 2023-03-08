import os
import spotipy
import pickle
from googleapiclient.discovery import build
from spotipy.oauth2 import SpotifyOAuth
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

os.environ["SPOTIPY_CLIENT_ID"] = "29edce36af8f42efae7e6fc73175ffeb"
os.environ["SPOTIPY_CLIENT_SECRET"] = "a310671dd5b74fdf95e47717cf368d1c"
os.environ["SPOTIPY_REDIRECT_URI"] = "http://example.com"

# Google auth data
client_secret_file = "credentials.json"
googleScope = ["https://www.googleapis.com/auth/spreadsheets"]
googleCredentials = service_account.Credentials.from_service_account_file(client_secret_file, scopes=googleScope)
spreadsheet_id = "1iwRP4GYJ6w-1_o_NfAGuUvcWiprqC8HyJqd-yvRBOPg"
service = build("sheets", "v4", credentials=googleCredentials)
spreadsheet = service.spreadsheets().values()
sheet = spreadsheet.get(spreadsheetId=spreadsheet_id, range="Artists").execute().get("values")

# Spoty auth data
spotyScope = "playlist-modify-private,playlist-read-collaborative,playlist-read-private,playlist-modify-public,user-library-read,user-follow-read"
spoty = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=spotyScope))

# YT auth data
ytCredentials = None
if os.path.exists("token.pickle"):
    print("Loading Credentials From File...")
    with open("token.pickle", "rb") as token:
        ytCredentials = pickle.load(token)
if ytCredentials and ytCredentials.expired and ytCredentials.refresh_token:
    print("Refreshing Access Token...")
    ytCredentials.refresh(Request())
elif not ytCredentials or not ytCredentials.valid:
    print("Fetching New Tokens...")
    yt_client_secret_file = "yt_client_secret.json"
    ytScope = ["https://www.googleapis.com/auth/youtube.force-ssl"]
    flow = InstalledAppFlow.from_client_secrets_file(yt_client_secret_file, ytScope)
    flow.run_local_server(port=8080, prompt="consent", authorization_prompt_message="")
    ytCredentials = flow.credentials
    # Save the credentials for the next run
    with open("token.pickle", "wb") as f:
        print("Saving Credentials for Future Use...")
        pickle.dump(ytCredentials, f)
yt = build("youtube", "v3", credentials=ytCredentials)

def parseFromSpoty():
    spoty_artists_metadata = spoty.current_user_followed_artists(limit=1, after=None)
    lefts = spoty_artists_metadata["artists"]["total"]
    after = None
    limit = 50
    artists = []
    while lefts >= 0:
        spoty_artists_metadata = spoty.current_user_followed_artists(limit=limit, after=after)
        spoty_artists = spoty_artists_metadata["artists"]["items"]
        after = spoty_artists_metadata["artists"]["cursors"]["after"]
        for spoty_artist in spoty_artists:
            artist = []
            artist.append(spoty_artist["name"])
            genres = spoty_artist["genres"].pop(0) if len(spoty_artist["genres"]) else ""
            for genre in spoty_artist["genres"]:
                genres += ", " + genre
            artist.append(genres)
            artist.append(spoty_artist["external_urls"]["spotify"])
            artist.append(spoty_artist["followers"]["total"])
            artists.append(artist)
        lefts -= limit
        limit = 1 if lefts < 50 else limit
    spreadsheet.append(spreadsheetId=spreadsheet_id, valueInputOption="RAW", range="Artists", body={"values": artists}).execute()
    print("Parsed from Spotify")

def artistsToRow(artists):
    headers = [h.lower() for h in sheet[0]]
    rowArtists = []
    for artist in artists:
        rowArtist = [None]*len(headers)
        for attr in artist:
            for i, h in enumerate(headers):
                if attr.lower() == h:
                    rowArtist[i] = artist[attr]
                    break
        rowArtists.append(rowArtist)
    return rowArtists

def findYT(artistName):
    response = yt.search().list(q=artistName, part="snippet", maxResults=1, type="channel")
    ytArtist = response.execute()["items"][0]["snippet"]
    artist = {
        "name": artistName,
        "nameYT": ytArtist["title"],
        "youtube": "https://www.youtube.com/channel/" + ytArtist["channelId"],
        "matchSpotyYT": artistName.lower() == ytArtist["title"].lower()
    }
    return artist

def storeToSheet(artists):
    for artist in artists:
        for i, artistRow in enumerate(sheet):
            if artistRow[0] == artist[0]:
                body = {   
                    "data": [{
                        "range": "Artists!" + str(i+1) + ":" + str(i+1),
                        "values": [artist]
                    }],
                    "valueInputOption": "RAW"
                }
                spreadsheet.batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    print("Stored to sheet")

def subscribeArtists(artists):
    body = {"snippet": {"resourceId": {"kind": "youtube#channel"}}}
    for artist in artists:
        try:
            body["snippet"]["resourceId"]["channelId"] = artist["youtube"].split("channel/")[1]
            yt.subscriptions().insert(part="snippet", body=body).execute()
        except Exception as e: print(e)

def getArtistsFromYt(index):
    names = []
    for i, artistRow in enumerate(sheet):
        if (i == 0):
            continue
        names.append(findYT(artistRow[0]))
        if i == index:
            break
    return names

def main():
    artists = getArtistsFromYt(406)
    artistsRows = artistsToRow(artists) #formated in row for sheets
    storeToSheet(artistsRows)
    #subscribeArtists(artists)
    print("done")

if __name__ == "__main__":
    main()