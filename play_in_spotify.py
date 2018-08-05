import pantus_shared as pantus

#Set spotify parameters
client_id='33ecbcf3e4ab41f0958d4997bbf8d030'
client_secret='37fbf6456c994f5981f771d1323efd81'
redirect_uri = 'http://127.0.0.1:8000/spotipy_callback' #This redirect_uri must be added into "Redirect URIs", which can be found in the dashboard settings of spotify for developers page

#Required genre filter and spotify playlist name
playlist_genre = 'Rock'

pt = pantus.pantus_db('pantus_db.db') #Creating pantus_db instance for music_db.db
if not pt.invalid_init: # If database is valid then do following
    pantus.reload_db(pt,'song_collection.xls') #Reload database with music.xls file
    records_by_genre = pt.get_records_by_genre_name(playlist_genre) # Generate records for required genre name


spotify = pantus.get_spotipy_handle(client_id,client_secret,redirect_uri,'playlist-modify-public') #Get spotipy Spotify object handle

track_uri_list = [] #Spotift track uris
for elem in records_by_genre: #Generate track_uri_list
    found_track = spotify.search('artist:'+elem[1]+' track:'+elem[2],limit=1) # Search for track by artist and track name
    if len(found_track['tracks']['items'])>0: #If track(s) is found then append FIRST ELEMENT into track_uri_list
        track_uri_list.append(found_track['tracks']['items'][0]['uri'])
user_info = spotify.me() #Get spotify user info
playlist_list = spotify.current_user_playlists() #Get current user playlists
playlist_list_names = [elem['name'] for elem in playlist_list['items']] # Generate list with current user playlist names
if not (playlist_genre in playlist_list_names): # If new playlist does not exist among  playlist_list_names
    spotify.user_playlist_create(user_info['id'],playlist_genre,public=True) #Create new public playlist
playlist_list = spotify.current_user_playlists()#Get refreshed current user playlists
new_playlist_uri = [elem['uri'] for elem in playlist_list['items'] if elem['name']==playlist_genre][0] #Get new playlist uri
spotify.user_playlist_add_tracks(user_info['id'],new_playlist_uri,track_uri_list)# Add every track in track_uri_list into new playlist

spotify = pantus.get_spotipy_handle(client_id,client_secret,redirect_uri,'streaming') # Get new spotify object with "streaming" scope 

spotify.start_playback(context_uri=new_playlist_uri) #Play new playlist in active device

