import zmq
import json
import time
import sys
import sqlite3

if len(sys.argv) < 2:
    print("Use: python subscriber.py <NameClient>")
    sys.exit(1)

#retrieve the client name
name_client = sys.argv[1]
identidad = name_client.encode('utf-8')

db_file = "estado_clientes.db"
conn = sqlite3.connect(db_file)

with conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS estado (nombre TEXT PRIMARY KEY, last_id INTEGER)""")

cursor = conn.cursor()
cursor.execute("SELECT last_id FROM estado WHERE nombre = ?", (name_client,))
row = cursor.fetchone()

if row:
    last_id = row[0]
else:
    last_id = 0
    #If new client, insert the initial state securely using a transaction
    with conn:
        conn.execute("INSERT INTO estado (nombre, last_id) VALUES (?, ?)", (name_client, last_id))

#configure dealer
context = zmq.Context()
subscriber = context.socket(zmq.DEALER)
subscriber.setsockopt(zmq.IDENTITY, identidad)
subscriber.connect("tcp://localhost:55555")

print(f"[{name_client}]. Mi last ID is {last_id}...")
subscriber.send_string(str(last_id))

#helper to persist the state
def save_state(new_id):
    try:
        with conn:
            conn.execute("UPDATE estado SET last_id = ? WHERE nombre = ?", (new_id, name_client))
        
    except sqlite3.Error as e:
        print(f"Critical Database Error saving state: {e}")

while True:

    #receive multipart message [Msg ID, JSON Payload]
    msg_recibido = subscriber.recv_multipart()
    msg_id = int(msg_recibido[0].decode('utf-8'))
    payload = json.loads(msg_recibido[1].decode('utf-8'))

    #differentiate live broadcast - catchup msg
    if "previous_id" in payload:
        prev_id = payload["previous_id"]
        
        #check if we are synchronized
        if prev_id == last_id:
            print(f"New msg -> [ID: {msg_id}]: {payload['last_message']}")
            last_id = msg_id 
            save_state(last_id) #persist new state
        else:
            #the client missed msg
            print(f"The previous_id is {prev_id}, but my last id is {last_id}.")
            subscriber.send_string(str(last_id))        
    else:
        #if it is a catch up msg 
        print(f"Retrieved msg -> [ID: {msg_id}]: {payload}")
        last_id = msg_id 
        save_state(last_id)

    time.sleep(0.1)