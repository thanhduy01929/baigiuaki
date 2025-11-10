import socket
import time
from common.constants import HOST, PORT, CHAT_PORT
from common.message import Message
import json

class ChessClientSocket:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.chat_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False

    def connect(self):
        try:
            # Set a shorter connection timeout for initial connection
            self.sock.settimeout(5.0)
            self.chat_sock.settimeout(5.0)

            # Try to connect to the main server
            print(f"Connecting to server at {HOST}:{PORT}...")
            self.sock.connect((HOST, PORT))
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # Try to connect to the chat server
            print(f"Connecting to chat server at {HOST}:{CHAT_PORT}...")
            self.chat_sock.connect((HOST, CHAT_PORT))
            self.chat_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # Set longer timeouts for normal operation
            self.sock.settimeout(60.0)
            self.chat_sock.settimeout(60.0)

            self.connected = True
            print("Successfully connected to server and chat server")
        except socket.timeout:
            print("Connection timed out. Server might not be running.")
            self.connected = False
        except ConnectionRefusedError:
            print("Connection refused. Server is not running or not accepting connections.")
            self.connected = False
        except Exception as e:
            print(f"Error connecting to server: {e}")
            self.connected = False

    def send_message(self, message):
        if not self.connected:
            print("Cannot send message: Not connected to server")
            return
        try:
            json_data = message.to_json()
            print(f"Sending message: {json_data}")
            self.sock.send(json_data.encode('utf-8'))
            time.sleep(0.2)  # Increased delay to ensure server processes the message
        except Exception as e:
            print(f"Error sending message: {e}")
            self.connected = False
            raise

    def send_chat(self, message):
        if not self.connected:
            print("Cannot send chat: Not connected to server")
            return
        try:
            json_data = message.to_json()
            print(f"Sending chat message: {json_data}")
            self.chat_sock.send(json_data.encode('utf-8'))
            time.sleep(0.2)  # Increased delay to ensure server processes the message
        except Exception as e:
            print(f"Error sending chat: {e}")
            self.connected = False
            raise

    def receive(self):
        if not self.connected:
            print("Cannot receive message: Not connected to server")
            return None
        try:
            self.sock.settimeout(5.0)  # Set timeout for receiving
            data = self.sock.recv(1024).decode('utf-8')
            self.sock.settimeout(None)  # Reset timeout
            if not data:
                print("Server closed connection")
                self.connected = False
                return None
                
            # Handle potential JSON parsing errors
            try:
                return Message.from_json(data)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Problematic data: {data}")
                # Try to recover by extracting valid JSON if possible
                try:
                    # Find the first '{' and last '}' to extract potential valid JSON
                    start = data.find('{')
                    end = data.rfind('}') + 1
                    if start >= 0 and end > start:
                        valid_json = data[start:end]
                        return Message.from_json(valid_json)
                except:
                    pass
                self.connected = False
                return None
        except socket.timeout:
            print("Timeout waiting for server message")
            return None
        except socket.error as e:
            print(f"Socket error while receiving message: {e}")
            self.connected = False
            raise
        except Exception as e:
            print(f"Error receiving message: {e}")
            self.connected = False
            raise

    def receive_chat(self):
        if not self.connected:
            print("Cannot receive chat: Not connected to server")
            return None
        try:
            data = self.chat_sock.recv(1024)
            if not data:
                print("Received empty data from chat server")
                return None
            data_str = data.decode('utf-8')
            print(f"Raw chat data received: {data_str}")
            return Message.from_json(data_str)
        except socket.timeout:
            print("Timeout waiting for chat message")
            return None
        except socket.error as e:
            print(f"Socket error while receiving chat: {e}")
            self.connected = False
            raise
        except Exception as e:
            print(f"Error receiving chat: {e}")
            self.connected = False
            raise

    def close(self):
        try:
            self.sock.close()
            self.chat_sock.close()
            self.connected = False
            print("Client sockets closed")
        except Exception as e:
            print(f"Error closing sockets: {e}")
