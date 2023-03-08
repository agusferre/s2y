import os
import spotipy
from googleapiclient.discovery import build
from spotipy.oauth2 import SpotifyOAuth
from google.oauth2 import service_account
from ytmusicapi import YTMusic
import unidecode

os.environ['SPOTIPY_CLIENT_ID'] = '29edce36af8f42efae7e6fc73175ffeb'
os.environ['SPOTIPY_CLIENT_SECRET'] = 'a310671dd5b74fdf95e47717cf368d1c'
os.environ['SPOTIPY_REDIRECT_URI'] = 'http://example.com'

# Google auth data
client_secret_file = 'credentials.json'
googleScope = ['https://www.googleapis.com/auth/spreadsheets']
googleCredentials = service_account.Credentials.from_service_account_file(client_secret_file, scopes=googleScope)
spreadsheet_id = '1iwRP4GYJ6w-1_o_NfAGuUvcWiprqC8HyJqd-yvRBOPg'
service = build('sheets', 'v4', credentials=googleCredentials)
spreadsheet = service.spreadsheets().values()
sheet = spreadsheet.get(spreadsheetId=spreadsheet_id, range='Artists').execute().get('values')

# Spoty auth data
spotyScope = 'playlist-modify-private,playlist-read-collaborative,playlist-read-private,playlist-modify-public,user-library-read,user-follow-read'
spoty = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=spotyScope))

# YT auth data
ytmusic = YTMusic('headers_auth.json')

def parseFromSpoty():
    spoty_artists_metadata = spoty.current_user_followed_artists(limit=1, after=None)
    lefts = spoty_artists_metadata['artists']['total']
    after = None
    limit = 50
    artists = []
    while lefts >= 0:
        spoty_artists_metadata = spoty.current_user_followed_artists(limit=limit, after=after)
        spoty_artists = spoty_artists_metadata['artists']['items']
        after = spoty_artists_metadata['artists']['cursors']['after']
        for spoty_artist in spoty_artists:
            artist = []
            artist.append(spoty_artist['name'])
            genres = spoty_artist['genres'].pop(0) if len(spoty_artist['genres']) else ''
            for genre in spoty_artist['genres']:
                genres += ', ' + genre
            artist.append(genres)
            artist.append(spoty_artist['external_urls']['spotify'])
            artist.append(spoty_artist['followers']['total'])
            artists.append(artist)
        lefts -= limit
        limit = 1 if lefts < 50 else limit
    spreadsheet.append(spreadsheetId=spreadsheet_id, valueInputOption='RAW', range='Artists', body={'values': artists}).execute()
    print('Parsed from Spotify')

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
    try:
        ytArtist = ytmusic.search(query=artistName, filter='artists', limit=1)[0]
        artist = {
            'name': artistName,
            'nameYT': ytArtist['artist'],
            'youtube': 'https://music.youtube.com/channel/' + ytArtist['browseId'],
            'matchSpotyYT': highMatchRate(artistName, ytArtist['artist'])
        }
        return artist
    except Exception as e: 
        print(e)
        print(artistName)

def highMatchRate(dbArtist, newArtist):
    try:
        dbArtist = unidecode.unidecode(dbArtist).lower()
        newArtist = unidecode.unidecode(newArtist).lower()
        errors = 0
        if dbArtist != newArtist:
            for i, letter in enumerate(newArtist):
                if i < len(dbArtist) and letter == dbArtist[i] or letter == dbArtist[i-1] or letter == dbArtist[i+1]: #-1 first letter is last in other array
                    continue
                else:
                    errors += 1
        return errors < 2
    except Exception as e: 
        print(e)
        print(dbArtist)

def storeToSheet(artists):
    body = {   
        'data': [{
            'range': 'Artists!2:' + str(len(sheet) + 1),
            'values': artists
        }],
        'valueInputOption': 'RAW'
    }
    spreadsheet.batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    print('Stored to sheet')

def getArtistsFromSheet():
    names = []
    i = 0
    for artistRow in sheet[1:]:
        names.append(findYT(artistRow[0]))
        i = i + 1
        if i == 30:
            break
    return names

def subscribeToYT(artists):
    for artist in artists:
        try:
            ytmusic.subscribe_artists([artist['youtube'].split("channel/")[1]])
        except Exception as e: print(e)
        print(artist['name'] + ' subscribed')
        
def main():
    try:
        artists = getArtistsFromSheet()
        artistsRows = artistsToRow(artists) #formated in row for sheets
        storeToSheet(artistsRows)
        #subscribeToYT(artists)
    except Exception as e: print(e)
    #arts = ytmusic.get_library_subscriptions(limit=500, order='recently_added')

if __name__ == '__main__':
    main()