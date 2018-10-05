import pantus_shared

LASTFM_API_KEY = "" 
LASTFM_API_SECRET = ""

SPOTIFY_API_ID = ""  
SPOTIFY_API_SECRET = ""




pantus_lastfm= pantus_all.pantus_lastfm()
pantus_lastfm.set_API_params(LASTFM_API_KEY,LASTFM_API_SECRET)
lastfm_token = pantus_lastfm.get_lastfm_token()


pantus_spotify = pantus_all.pantus_spotify()
pantus_spotify.set_API_params(SPOTIFY_API_ID,SPOTIFY_API_SECRET)
pantus_spotify.spotify_scope = 'streaming'
spotify_tokens = pantus_spotify.get_spotify_handle()
