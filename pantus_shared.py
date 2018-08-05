from http.server import HTTPServer, BaseHTTPRequestHandler 
import sqlite3, threading, xlrd, webbrowser, spotipy

spotify_response = False

class pantus_HTTPServer_RequestHandler(BaseHTTPRequestHandler): #Request handler for HTTP Server. This function will save spotify authorization code in spotify_response 
  def do_GET(self):
        global spotify_response
        global html_response
        redirect_path = self.path # Get complete url path
        spotify_response = {k:v for k,v in [elem.split('=') for elem in redirect_path[(redirect_path.find('?')+1):len(redirect_path)].split('&')]} # Convert parameters from path string into dictionary
        #HTML response string
        if 'error' in spotify_response.keys(): 
            html_response = 'Pantus: An error occured during authorization code flow. <br/> Error:'+spotify_response['error']
        else:
            html_response = 'Pantus: Spotify authorization code was successfully received. Please,  close this page!'
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.wfile.write(bytes(html_response, "utf8")) #Echo response string
        return


def get_spotify_code(authorization_url,host = '127.0.0.1', port = 8000): #This function returns spotify authorization code
    global spotify_response
    server_address = (host,port)
    httpd = HTTPServer(server_address, pantus_HTTPServer_RequestHandler)#Create HTTP server object
    httpd_thread = threading.Thread(target = httpd.handle_request)#Pass handle_request to different thread in order to continue code flow
    httpd_thread.start()#Start HTTP server and allow handle_request to listen 
    webbrowser.open_new(authorization_url) #Go to authorization url from the default browser
    retval = False
    while True: # Listen to reply from authorization url and save recieved authorization code
        if not type(spotify_response)==bool:
            if 'error' in spotify_response.keys():
                retval = spotify_response['error']
                break;
            elif 'code' in spotify_response.keys():
                retval = spotify_response['code']
                break;
    spotify_response = False
    httpd.server_close() #Close HTTP server
    return retval #Return spotify authorization code

def get_spotipy_handle(in_client_id,in_client_secret,in_redirect_uri,in_scope): #This function returns spotify object
    sp_oauth = spotipy.oauth2.SpotifyOAuth(in_client_id, in_client_secret,in_redirect_uri,scope=in_scope) # Run authorization flow for given client_id, client_secret, scope and redirect_uri
    authorization_url = sp_oauth.get_authorize_url() # Get authorization url in URL format
    code = get_spotify_code(authorization_url) # Use get_spotify_code to get authorization code from https://accounts.spotify.com/authorize
    token_info = sp_oauth.get_access_token(code) # Get authorization token info for provided  authorization code from https://accounts.spotify.com/authorize
    token = token_info['access_token'] #Set token to authorization token
    return spotipy.Spotify(auth=token) #Use authorization token and return usefull spotify object
    

# DATABASE STUFF
def reload_db(pantus_obj,xls_filename): # This function clears database and reloads database with new data from excel file
    pantus_obj.db_truncate_all() #Clear database data
    workbook = xlrd.open_workbook(xls_filename) #Load excel file
    sheet = workbook.sheet_by_index(0) #Select first workbook sheet
    data = [sheet.col_values(0,1), sheet.col_values(1,1), sheet.col_values(2,1), sheet.col_values(3,1), sheet.col_values(4,1), sheet.col_values(5,1)] #Form list with new data as [Artist, TrackName, Genres, Tags, Decade, Exceptional]
    for i in range(len(data[0])): #This loop interates data list and adds each records to database
        new_artist = data[0][i]
        new_track = data[1][i]
        new_genres = data[2][i]
        new_tags = data[3][i]
        new_decade = data[4][i]
        new_mark1 = 1 if data[5][i]=='x' else 0
        pantus_obj.add_new_record(new_artist,new_track,new_genres,new_decade,new_tags,mark1=new_mark1)
    return True
        
class pantus_db: #This is main class responsible for working with SQLite database file

    def __init__(self,value): 
        self.db_filename  = value #Save database filename
        self.db_connection = sqlite3.connect(value) #Connect to SQLite database
        self.db_cursor = self.db_connection.cursor() #Save SQLite database cursor
        self.invalid_init = not self.validate_db_structure() #Check structural validity of the database file
        
    def validate_db_structure(self): #This method checks for validity of the database
        #Check structure of the GENRES_TABLE
        self.db_cursor.execute('PRAGMA table_info(GENRES_TABLE)')
        genres_table = self.db_cursor.fetchall()
        genres_table_valid = (len(genres_table)>0) and \
        (genres_table[0][1] == 'id') and (genres_table[1][1] == 'name') and \
        (genres_table[0][2] == 'INTEGER') and (genres_table[1][2] == 'TEXT')
        
        #Check structure of the TAGS_TABLE
        self.db_cursor.execute('PRAGMA table_info(TAGS_TABLE)')
        tags_table = self.db_cursor.fetchall()
        tags_table_valid = (len(tags_table)>0) and \
        (tags_table[0][1] == 'id') and (tags_table[1][1] == 'name') and \
        (tags_table[0][2] == 'INTEGER') and (tags_table[1][2] == 'TEXT')
        
        #Check structure of the RECORD_TAG_RTABLE
        self.db_cursor.execute('PRAGMA table_info(RECORD_TAG_RTABLE)')
        record_tag_rtable = self.db_cursor.fetchall()
        record_tag_rtable_valid = (len(record_tag_rtable)>0) and \
        (record_tag_rtable[0][1] == 'id') and (record_tag_rtable[1][1] == 'tag_id') and (record_tag_rtable[2][1] == 'record_id') and \
        (record_tag_rtable[0][2] ==  record_tag_rtable[1][2] == record_tag_rtable[2][2] ==  'INTEGER')
        
        #Check structure of the RECORD_GENRE_RTABLE
        self.db_cursor.execute('PRAGMA table_info(RECORD_GENRE_RTABLE)')
        record_genre_rtable = self.db_cursor.fetchall()
        record_genre_rtable_valid = (len(record_genre_rtable)>0) and \
        (record_genre_rtable[0][1] == 'id') and (record_genre_rtable[1][1] == 'genre_id') and (record_genre_rtable[2][1] == 'record_id')and \
        (record_genre_rtable[0][2] == record_genre_rtable[1][2] == record_genre_rtable[2][2] ==  'INTEGER')
        
        #Check structure of the RECORDS_TABLE
        self.db_cursor.execute('PRAGMA table_info(RECORDS_TABLE)')
        records_table = self.db_cursor.fetchall()
        records_table_valid = (len(records_table)>0) and (records_table[0][1] == 'id') and (records_table[1][1] == 'artist') and (records_table[2][1] == 'track') and (records_table[3][1] == 'genres') and (records_table[4][1] == 'decade') and (records_table[5][1] == 'tags') and (records_table[6][1] == 'links') and (records_table[7][1] == 'mark1') and (records_table[8][1] == 'mark2') and (records_table[9][1] == 'mark3') and\
        (records_table[0][2] == records_table[7][2] == records_table[8][2] == records_table[9][2] == 'INTEGER') and (records_table[1][2] == records_table[2][2] == records_table[3][2] == 'TEXT(255)') and (records_table[4][2] == 'TEXT(20)') and (records_table[5][2] == records_table[6][2] == 'TEXT')
        
        #Return overall validity
        overall_validity = genres_table_valid and tags_table_valid and record_genre_rtable_valid and record_tag_rtable_valid and records_table_valid
        return overall_validity
    
    def invalid_db(self): #Method for response for invalid initiation 
        print('DB Structure is not valid. Please use .reload_db(filename) method to reload database.')
        return False
    def get_all_records(self): #Get all records from database
        if self.invalid_init:
            return self.invalid_db()
        self.db_cursor.execute("SELECT * FROM RECORDS_TABLE")
        return self.db_cursor.fetchall()
    
    def get_all_tags(self):#Get all tags from database
        if self.invalid_init:
            return self.invalid_db()
        self.db_cursor.execute("SELECT * FROM TAGS_TABLE")
        return self.db_cursor.fetchall()
    
    def get_all_genres(self):#Get all genres from database
        if self.invalid_init:
            return self.invalid_db()
        self.db_cursor.execute("SELECT * FROM GENRES_TABLE")
        return self.db_cursor.fetchall()
    
    def get_genres_by_names(self,genre_list):#Get genre records by genre names given in genre_list 
        if self.invalid_init:
            return self.invalid_db()
        self.db_cursor.execute("SELECT * FROM GENRES_TABLE WHERE name IN ("+(','.join(["'"+elem+"'" for elem in genre_list]))+")")
        result  = self.db_cursor.fetchall()
        return result
    
    def get_tags_by_names(self,tag_list):#Get tag records by genre names given in genre_list 
        if self.invalid_init:
            return self.invalid_db()
        self.db_cursor.execute("SELECT * FROM TAGS_TABLE WHERE name IN ("+(','.join(["'"+elem+"'" for elem in tag_list]))+")")
        result  = self.db_cursor.fetchall()
        return result
    
    def get_genre_id_by_name(self,genre_name):#Get genre id by genre name
        if self.invalid_init:
            return self.invalid_db()
        self.db_cursor.execute("SELECT id FROM GENRES_TABLE WHERE name=? LIMIT 1", (genre_name,))
        result  = self.db_cursor.fetchone()
        return False if result == None else result[0]
    
    def get_tag_id_by_name(self,tag_name):#Get tag id by tag name
        if self.invalid_init:
            return self.invalid_db()
        self.db_cursor.execute("SELECT id FROM TAGS_TABLE WHERE name=? LIMIT 1", (tag_name,))
        result  = self.db_cursor.fetchone()
        return False if result == None else result[0]
    
    def get_records_by_genre_id(self, genre_id):#Get records by genre id 
        if self.invalid_init:
            return self.invalid_db()
        self.db_cursor.execute("SELECT * FROM RECORD_GENRE_RTABLE WHERE genre_id=?", (genre_id,))
        record_id_list = [elem[2] for elem in self.db_cursor.fetchall()]
        self.db_cursor.execute("SELECT * FROM RECORDS_TABLE WHERE id IN ("+(','.join(["'"+str(elem)+"'" for elem in record_id_list]))+")")
        return self.db_cursor.fetchall()
    
    def get_records_by_tag_id(self, tag_id):#Get records by tag id
        if self.invalid_init:
            return self.invalid_db()
        self.db_cursor.execute("SELECT * FROM RECORD_TAG_RTABLE WHERE tag_id=?", (tag_id,))
        record_id_list = [elem[2] for elem in self.db_cursor.fetchall()]
        self.db_cursor.execute("SELECT * FROM RECORDS_TABLE WHERE id IN ("+(','.join(["'"+str(elem)+"'" for elem in record_id_list]))+")")
        return self.db_cursor.fetchall()
    
    def get_records_by_genre_name(self,genre_name): #Get records by genre name
        if self.invalid_init:
            return self.invalid_db()
        genre_id = self.get_genre_id_by_name(genre_name)
        results = self.get_records_by_genre_id(genre_id)
        return results
    
    def get_records_by_tag_name(self,tag_name):#Get records by tag name
        if self.invalid_init:
            return self.invalid_db()
        tag_id = self.get_tag_id_by_name(tag_name)
        results = self.get_records_by_tag_id(tag_id)
        return results
    
    def add_new_tags(self,tag_names):# Add new tag(s)
        if self.invalid_init:
            return self.invalid_db()
        retval = False
        tag_names = tag_names if type(tag_names)==list else [tag_names]
        for tag_name in tag_names:
            if not self.get_tag_id_by_name(tag_name):
                self.db_cursor.execute("INSERT INTO TAGS_TABLE (name) VALUES (?)", (tag_name,))
                retval = self.db_connection.commit()
        return retval
    
    def add_new_genres(self,genre_names):# Add new genre(s)
        if self.invalid_init:
            return self.invalid_db()
        retval = False
        genre_names = genre_names if type(genre_names)==list else [genre_names]
        for genre_name in genre_names:
            if not self.get_genre_id_by_name(genre_name):
                retval = self.db_cursor.execute("INSERT INTO GENRES_TABLE (name) VALUES (?)", (genre_name,))
                self.db_connection.commit()
        return retval
    
    def get_autoinc_value(self,table_name):# Get auto increment value for given table_name
        if self.invalid_init:
            return self.invalid_db()
        self.db_cursor.execute("SELECT seq FROM  sqlite_sequence WHERE name = ?", (table_name,))
        result  = self.db_cursor.fetchone()
        return int(result[0])+1
    
    def add_new_record(self,artist,track,genres,decade,tags='',links='',mark1=0,mark2=0,mark3=0): #Add new record
        if self.invalid_init:
            return self.invalid_db()
        self.db_cursor.execute("SELECT id FROM RECORDS_TABLE WHERE artist=? AND track=? LIMIT 1", (artist, track))
        if not self.db_cursor.fetchone() == None:
            return 'Error! (Record with given artist and track name already exists in the database)'
        new_id = self.get_autoinc_value("RECORDS_TABLE") #Get next id for RECORDS_TABLE
        genre_list = genres.split('/') # Explode genres string into list
        self.add_new_genres(genre_list) # Add missing genres into the database
        genre_id_list = [str(elem[0]) for elem in self.get_genres_by_names(genre_list)] # Convert tag names into tag IDs
        self.relate_genres_to_record(new_id,genre_id_list) # Correlate genres with new record
        if len(tags)>1: #Check if any tags are present
            tag_list = tags.split('/') # Explode tags string into list
            self.add_new_tags(tag_list) # Add missing tags into the database
            tag_id_list = [str(elem[0]) for elem in self.get_tags_by_names(tag_list)]# Convert tag names into tag IDs
            self.relate_tags_to_record(new_id,tag_id_list)# Correlate tags with new record
        else:
            tag_id_list = False
        links = str(links)
        decade = str(decade)
        #Add new record into database
        retval = self.db_cursor.execute("INSERT INTO RECORDS_TABLE (artist,track,genres,decade,tags,links,mark1,mark2,mark3) VALUES (:artist,:track,:genres,:decade,:tags,:links,:mark1,:mark2,:mark3)",{"artist":artist,"track":track,"genres":(','.join(genre_id_list)),"decade":decade,"tags":None if not tag_id_list else (','.join(tag_id_list)),"links":links,"mark1":str(mark1),"mark2":str(mark2),"mark3":str(mark3)})
        self.db_connection.commit()
        return retval
    
    def relate_genres_to_record(self, record_id, genres): #Correlate new genre IDs with record id
        if self.invalid_init:
            return self.invalid_db()
        retval = False
        for genre in genres:
            self.db_cursor.execute("SELECT id FROM RECORD_GENRE_RTABLE WHERE genre_id=? AND record_id=? LIMIT 1", (genre, record_id))
            if self.db_cursor.fetchone() == None:
                retval = self.db_cursor.execute("INSERT INTO RECORD_GENRE_RTABLE (genre_id, record_id) VALUES(?,?)", (genre, record_id))
        return retval
    
    def relate_tags_to_record(self, record_id, tags): #Correlate new tag IDs with record id
        if self.invalid_init:
            return self.invalid_db()
        retval = False
        for tag in tags:
            self.db_cursor.execute("SELECT id FROM RECORD_TAG_RTABLE WHERE tag_id=? AND record_id=? LIMIT 1", (tag, record_id))
            if self.db_cursor.fetchone() == None:
                retval = self.db_cursor.execute("INSERT INTO RECORD_TAG_RTABLE (tag_id, record_id) VALUES(?,?)", (tag, record_id))
        return retval
    
    def del_record_by_id(self,record_id): #Delete record from database
        if self.invalid_init:
            return self.invalid_db()
        retval = self.db_cursor.execute("DELETE FROM RECORDS_TABLE WHERE id = ?" (record_id,))
        self.db_connection.commit()
        return retval
    
    def del_tag_by_id(self,tag_id):#Delete tag from database
        if self.invalid_init:
            return self.invalid_db()
        retval = self.db_cursor.execute("DELETE FROM TAGS_TABLE WHERE id = ?",(tag_id,))
        self.db_connection.commit()
        return retval
    
    def del_genre_by_id(self,genre_id):#Delete genre from database
        if self.invalid_init:
            return self.invalid_db()
        retval = self.db_cursor.execute("DELETE FROM GENRES_TABLE WHERE id = ?",(genre_id,))
        self.db_connection.commit()
        return retval
    
    def db_truncate_all(self):# Clear database tables
        if self.invalid_init:
            return self.invalid_db()
        self.db_cursor.execute("DELETE FROM TAGS_TABLE")
        self.db_cursor.execute("DELETE FROM RECORDS_TABLE")
        self.db_cursor.execute("DELETE FROM RECORD_TAG_RTABLE")
        self.db_cursor.execute("DELETE FROM GENRES_TABLE")
        self.db_cursor.execute("DELETE FROM RECORD_GENRE_RTABLE")
        return self.db_connection.commit()
