
import zmq
import sqlite3
import json
import time

#connect sql dadtabase
conn = sqlite3.connect('mensajes.db')
cursor = conn.cursor()

#create table
with open('esquema.sql', 'r') as f:
    cursor.executescript(f.read())
conn.commit()

#configure router
context = zmq.Context()
publisher = context.socket(zmq.ROUTER)
publisher.bind("tcp://*:55555")

#use poller to handle incoming requests
poller = zmq.Poller()
poller.register(publisher, zmq.POLLIN)

know_clients = set()

#recover last inserted ID from db
cursor.execute("SELECT MAX(id) FROM mensajes")
resultado = cursor.fetchone()[0]

#set the counter to the maxID
contador = resultado if resultado is not None else 0

ciclos=0

print(f"Publisher (ROUTER) started. Resuming from message count: {contador}")

while True:

    events = dict(poller.poll(1000))

    # listen clients (dealer)
    if publisher in events:
        msg_recibido = publisher.recv_multipart()
        id_client = msg_recibido[0]
        last_id_client = int(msg_recibido[1].decode('utf-8'))

        print(f"[{id_client.decode('utf-8')}] connected. Last msg was with ID: {last_id_client}")
        know_clients.add(id_client)

        #query db for any msg the client missed
        cursor.execute("SELECT id, mensaje_json FROM mensajes WHERE id > ? ORDER BY id ASC", (last_id_client,))
        msg_lost = cursor.fetchall()

        #forward missing msg directly
        for i in msg_lost:
            id_db = i[0]
            json_db = i[1]

            publisher.send_multipart([id_client, str(id_db).encode('utf-8'), json_db.encode('utf-8')])
            print(f"Forward ID {id_db} to [{id_client.decode('utf-8')}]")
    
    # simulate new messages
    ciclos += 1
    if ciclos % 5 == 0:

        contador += 1
        
        #generate and store the new message
        new_json = json.dumps({"text": f"Message {contador}"})
        cursor.execute("INSERT INTO mensajes (mensaje_json) VALUES (?)", (new_json,))
        conn.commit()

        #retrieve the last two msg 
        cursor.execute("SELECT id, mensaje_json FROM mensajes ORDER BY id DESC LIMIT 2")
        last_two = cursor.fetchall()
        last_two.reverse()

        #ensure we have at least two msg
        if len(last_two) == 2:
            prev_id, prev_json = last_two[0]
            last_id, last_json = last_two[1]

            #build the payload containing previous and current state
            response = json.dumps({
                "previous_id": prev_id,
                "previous_message": json.loads(prev_json),
                "last_id": last_id,
                "last_message": json.loads(last_json)
            })

            print(f"NEW MESSAGE -> ID: {last_id}")

            #broadcast
            for client in know_clients:
                publisher.send_multipart([client, str(last_id).encode('utf-8'), response.encode('utf-8')])