# ZeroMQ Reliable Pub-Sub (ROUTER-DEALER)

This project is a robust implementation of the **Publish-Subscribe** pattern using **ZeroMQ** in Python. It was developed as part of a Concurrent Computing course to solve the classic problem of the standard PUB-SUB pattern: message loss when subscribers disconnect.

To ensure that **no message is lost**, the system moves away from traditional PUB/SUB sockets in favor of a **ROUTER-DEALER** architecture backed by **SQLite** database persistence.

## System Architecture

The system consists of two main components:

1. **Publisher (ROUTER):**
   - Periodically generates messages and saves them to a local database (`mensajes.db`).
   - Broadcasts new messages to all known clients.
   - Each new message includes a validation payload (`previous_id`, `last_id`) so clients can verify their synchronization.
   - Listens for recovery requests: if a client has missed messages, the server queries the database and securely forwards them using the socket's identity.

2. **Subscriber (DEALER):**
   - Connects to the server using a unique Identity (`zmq.IDENTITY`).
   - Maintains its own state (`last_id`) securely saved via transactions in a local database (`estado_clientes.db`).
   - Verifies every incoming message. If it detects a desynchronization (the server's `previous_id` does not match its `last_id`), it automatically requests the missing messages to catch up.

## Prerequisites

Make sure you have Python 3.x and the ZeroMQ library for Python installed:

```bash
pip install pyzmq
