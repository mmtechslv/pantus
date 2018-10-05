#Required modules
from http.server import HTTPServer, BaseHTTPRequestHandler 
import threading, webbrowser,time,requests, json, base64, xlrd, sqlite3, pylast

#Global Internal Variables. THESE VARIABLES ARE INITIALIZED BY pantus_base CLASS. DO NOT CHANGE THEM MANUALLY!
__PANTUS_HTTP_RESPONSE = False
__PANTUS_HTTP_TIMEOUT = False

class pantus_HTTPServer_RequestHandler(BaseHTTPRequestHandler): #This is current HTTP Request handler but it will probably be changed later.
    def setup(self):
        BaseHTTPRequestHandler.setup(self)        
        self.timeout = __PANTUS_HTTP_TIMEOUT
    def do_GET(self):
        global __PANTUS_HTTP_RESPONSE
        redirect_path = self.path # Get complete url path
        try:
            __PANTUS_HTTP_RESPONSE = {k:v for k,v in [elem.split('=') for elem in redirect_path[(redirect_path.find('?')+1):len(redirect_path)].split('&')]} # Convert parameters from path string into dictionary
        except ValueError:
            print("\nPantus: ValueError in redirect_path parsing. Probably only one argument received.\n")
        except:
            print("\nPantus: Unknown Error Occured.\n")
        #HTML response string
        try:
            if 'error' in __PANTUS_HTTP_RESPONSE.keys(): 
                html_response = '\nPantus: An error occured during authorization code flow. <br/> Redirect Path:'+redirect_path+'\n'
            else:
                html_response = '\nPantus: Authorization code was successfully received. This page can be closed now!\n'
        except AttributeError:
            html_response = '\nPantus: An error occured during authorization code flow. <br/> Redirect Path:'+redirect_path+'\n'
            
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.wfile.write(bytes(html_response, "utf8")) #Echo response string
        return

class pantus_base(object): #Base pantus class
    def __init__(self):
        self.tokens = False #Variable where necessary tokens will be stored
        self.API_params = {'key': False,'secret': False} #Dict where API key and secret are stored
        self.host = '127.0.0.1' #Default local host
        self.port = 8000 # Default localhost port. This number is modified by class method new_port() in order to avoid httpd overlaps
        self.error_msg = False #Error Messages
        self.http_timeout = 30 # Default timeout in seconds
        self.redirect_path = '/pantus_callback' # Default callback path
        self.redirect_uri = 'http://'+self.host+':'+str(self.port)+self.redirect_path #Default  complete redirect URI
        self.init_ready = False #Initialization check
        self.exchange_code = False #Exchange URI parameter. "token" for last.fm and "code" for spotify
        self.http_thread = False #Thread handle
     
    def get_latest_error(self):  #Retrieve latest error message
        print('\nPantus: '+self.error_msg+'\n')
        return self.error_msg
        
    def set_redirect_path(self,path):# Set redirect path and evaluate its URI
        self.redirect_path = path
        self.redirect_uri = 'http://'+str(self.host)+':'+self.port+path
        return True
    
    def set_API_params(self,key,secret): #Set API params
        self.API_params['key'] = key
        self.API_params['secret'] = secret
        return True
    
    def check_thread(self): #Check if thread is alive
        return self.http_thread.isAlive() if self.http_thread else False
    
    def wait_for_timeout(self):#Wait until thread is dead. Does not work at this point needs correction
        while self.check_thread():
            time.sleep(0.2)
        return 

    def get_auth_code(self,authorization_url): #This function returns authorization code
        global __PANTUS_HTTP_RESPONSE
        global __PANTUS_HTTP_TIMEOUT
        __PANTUS_HTTP_TIMEOUT = self.http_timeout #Declares timeout global so that request handler also use it
        server_address = (self.host,self.port) #Server host and port
        httpd = HTTPServer(server_address, pantus_HTTPServer_RequestHandler)#Create HTTP server object
        self.http_thread = threading.Thread(target = httpd.serve_forever) #Pass handle_request to different thread in order to continue code flow
        self.http_thread.start()#Start HTTP server and allow handle_request to listen 
        webbrowser.open_new(authorization_url) #Go to authorization url from the default browser
        retval = False
        timeout = time.time()+__PANTUS_HTTP_TIMEOUT #Timeout for the following loop
        while True: # Listen to reply from authorization url and save recieved authorization code
            if time.time() > timeout: #Check for timeout
                retval = 'HTTP Timeout('+str(self.http_timeout)+'s).' #Return timeout error
                break;
            time.sleep(0.5)
            if not type(__PANTUS_HTTP_RESPONSE)==bool: #Check if response was retrieved in HTTP request handler
                if 'error' in __PANTUS_HTTP_RESPONSE.keys():
                    retval = __PANTUS_HTTP_RESPONSE['error'] #Return response error
                    break;
                if self.exchange_code in __PANTUS_HTTP_RESPONSE.keys():
                    retval = __PANTUS_HTTP_RESPONSE[self.exchange_code] #Return exchange code such as authorization token for spotify or last.fm
                    break;
        __PANTUS_HTTP_RESPONSE = False #Reset global response variable
        __PANTUS_HTTP_TIMEOUT = False #Reset global timeout variable
        httpd.server_close() #Close HTTP server
        return retval 
     
class pantus_spotify(pantus_base): #This is class that works with spotify
    def __init__(self): # Adding missing attributes for the spotify class
        super(pantus_spotify,self).__init__()
        self.spotify_scope = False
        self.exchange_code = 'code'
        
    def get_authorize_url(self): #Get authorization url for spotify 
        return 'https://accounts.spotify.com/authorize/?client_id='+self.API_params['key']+'&response_type=code&redirect_uri='+self.redirect_uri+'&scope='+self.spotify_scope
    
    def check_init(self):# Check if spotify class is ready to go for authorization flow
        if (self.API_params['key'] and self.API_params['secret'] and self.spotify_scope and self.redirect_uri):
            self.init_ready = True
        else:
            self.init_ready = False
        return self.init_ready
    
    def get_spotify_tokens(self,auth_code): # Get spotify access and refresh tokens 
        response = requests.post(url = "https://accounts.spotify.com/api/token/", headers = {"content-type":'application/x-www-form-urlencoded'}, data={'grant_type': 'authorization_code', 'code': auth_code, 'redirect_uri': self.redirect_uri,'client_id':self.API_params['key'], 'client_secret':self.API_params['secret']})
        if response.status_code == 200:
            return json.loads(str(response.text))
        else:
            self.error_msg = 'Spotify Tokens can not be retrieved. Status Code: '+ str(response.status_code) + '. Reason: '+ str(response.reason)
            return False
        
    def get_spotify_handle(self): # Get spotify handle but for now only returns spotify acess tokens
        if not self.check_init(): #Check if everything is ready
            self.error_msg = "Spotify error can not initialize"
            return False
        if self.check_thread(): # Check if thread is ready. Does not work properly
            self.wait_for_timeout()
        auth_url = self.get_authorize_url() #Get authorization url
        code = self.get_auth_code(auth_url) #Get authorization code
        tokens = self.get_spotify_tokens(code) #Get access and refresh tokens
        return tokens
    
class pantus_lastfm(pantus_base): #This is class that works with last.fm
    def __init__(self): #Adding missing attributes for the last.fm class
        super(pantus_lastfm,self).__init__()
        self.exchange_code = 'token'
        
    def get_authorize_url(self): # Get authorization url
        return "http://www.last.fm/api/auth/?api_key="+self.API_params['key']+'&cb='+self.redirect_uri
    
    def check_init(self): #Check if last.fm class is ready to go for authorization flow
        if (self.API_params['key'] and self.API_params['secret']):
            self.init_ready = True
        return self.init_ready
    
    def get_lastfm_token(self): #Get last.fm access tokens
        if not self.check_init(): #Chekc if everything is ready
            self.error_msg = "last.fm API parameters are not initialized!"
            return False
        if self.check_thread(): #Check if thread is ready. Does not work properly
            self.wait_for_timeout()
        auth_url = self.get_authorize_url() # Get authorization url
        token = self.get_auth_code(auth_url) # Get access/authorization token for last.fm
        return token
    
# AT THIS POINT DATABASE METHODS START

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

