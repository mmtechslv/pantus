import pantus_shared

LASTFM_API_KEY = "8d51f09419774877f365ea7ca50e7a00" 
LASTFM_API_SECRET = "4ec41182667d5308f419ee35794f6478"

SPOTIFY_API_ID = "33ecbcf3e4ab41f0958d4997bbf8d030"  
SPOTIFY_API_SECRET = "37fbf6456c994f5981f771d1323efd81"




pantus_lastfm= pantus_all.pantus_lastfm()
pantus_lastfm.set_API_params(LASTFM_API_KEY,LASTFM_API_SECRET)
lastfm_token = pantus_lastfm.get_lastfm_token()


pantus_spotify = pantus_all.pantus_spotify()
pantus_spotify.set_API_params(SPOTIFY_API_ID,SPOTIFY_API_SECRET)
pantus_spotify.spotify_scope = 'streaming'
spotify_tokens = pantus_spotify.get_spotify_handle()
