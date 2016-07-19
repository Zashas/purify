import requests, re, spotipy, sys, json
import spotipy.oauth2

SPOTIFY_SCOPE = 'playlist-read-private playlist-modify-private playlist-modify'

PUREFM_URL = "http://www.rtbf.be/purefm/conducteur"
config = None

try:
    with open("config.json") as f:
        config = json.load(f)
except (IOError, json.decoder.JSONDecodeError):
    print("Configuration file could not be read.")
    exit()

#Fetches tracks from PureFM "conducteur" page
#Returns an iterable of pairs (title, artist)
def fetch_tracks():
    r = requests.get(PUREFM_URL)

    if r.status_code != requests.codes.ok:
        print("Songs retrieval failed.")
        return None


    titles = re.findall("Titre:.\<strong\>(.*)\</strong\>", r.text)
    singers = re.findall("Artiste:.\<strong\>(.*)\</strong\>", r.text)
    return zip(titles, singers)

#Given a iterable of pairs (title, artist), fetches from Spotify
#the set of IDs of the given tracks
def get_tracks_id(sp, tracks):
    tracks_id = set()

    for track in tracks:
        s = sp.search(" ".join(track), type='track', limit=1)
        if len(s['tracks']['items']) > 0: #No track matched the query, ignoring
            tracks_id.add(s['tracks']['items'][0]['id'])

    return tracks_id 

#Returns a set containing the tracks' IDs of the playlist specified in the config file
def get_playlist_tracks(sp):
    playlist_ids = set()
    count = 0
    while True:
        playlist = sp.user_playlist_tracks(config['user_id'], config['playlist_id'], offset=count*100, limit=100)
        if len(playlist['items']) == 0:
            break

        for track in playlist['items']:
            playlist_ids.add(track['track']['uri'])

        count += 1

    return playlist_ids

#Adds tracks to the Spotify playlist specified in the config file, tracks is an iterable of tracks IDs
def add_tracks(sp, tracks):
    if len(tracks) > 0:
        sp.user_playlist_add_tracks(config['user_id'], config['playlist_id'], tracks)    

#Generates a new access token for accessing Spotify. If the token can not be automaticaly refreshed,
#triggers an interactive prompt asking the user to follow some auth steps.
def spotify_interactive_auth():
    sp_oauth = spotipy.oauth2.SpotifyOAuth(config['client_id'], config['client_secret'],
                config['redirect_uri'], scope=SPOTIFY_SCOPE,
                cache_path=".purify-cache")

    token_info = sp_oauth.get_cached_token()

    if not token_info:
        print('''
            User authentication requires interaction with your
            web browser. Once you enter your credentials and
            give authorization, you will be redirected to
            a url.  Paste that url you were directed to to
            complete the authorization.

        ''')
        auth_url = sp_oauth.get_authorize_url()
        try:
            subprocess.call(["xdg-open", auth_url])
            print("Opening %s in your browser" % auth_url)
        except:
            print("Please navigate here: %s" % auth_url)

        print()
        print()

        response = input("Enter the URL you were redirected to: ")

        print()
        print() 

        code = sp_oauth.parse_response_code(response)
        token_info = sp_oauth.get_access_token(code)

    return token_info


token = spotify_interactive_auth()
if token == None:
    print("Could not connect to Spotify.")
    exit()

sp = spotipy.Spotify(auth=token['access_token'])

new_tracks = fetch_tracks()
new_tracks_id = get_tracks_id(sp, new_tracks)
playlist_tracks_id = get_playlist_tracks(sp)

tracks_to_add = new_tracks_id - playlist_tracks_id
add_tracks(sp, tracks_to_add)

print("{} new tracks added.".format(len(tracks_to_add)))
