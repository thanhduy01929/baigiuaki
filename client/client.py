import threading
import pygame
import sys
from client.client_socket import ChessClientSocket
from common.message import Message

class ChessClient:
    def __init__(self):
        self.socket = ChessClientSocket()
        self.player_id = None
        self.color = None
        self.opponent = None
        self.game_id = None
        self.gui = None
        self.running = True

    def start(self):
        self.socket.connect()
        if not self.socket.connected:
            print("Failed to connect to the server. Exiting...")
            sys.exit(1)

        self.player_id = input("Enter your player ID: ")
        threading.Thread(target=self.receive_messages, daemon=True).start()
        threading.Thread(target=self.receive_chat_messages, daemon=True).start()

    def join_lobby(self):
        if not self.socket.connected:
            print("Cannot join lobby: Not connected to server")
            return
        message = Message("JOIN_LOBBY", {"player_id": self.player_id})
        self.socket.send_message(message)

    def receive_messages(self):
        while self.running and self.socket.connected:
            try:
                message = self.socket.receive()
                if not message:
                    print("Connection to server lost.")
                    self.socket.connected = False
                    self.running = False
                    if self.gui:
                        self.gui.shutdown()
                    break
                print(f"Received message: {message.type}")
                if message.type == "WAITING":
                    print("Waiting for opponent...")
                elif message.type == "GAME_LIST":
                    print(f"Available games: {message.data.get('games', [])}")
                elif message.type == "GAME_START":
                    print(f"Game started! You are {message.data['color']}")
                    self.game_id = message.data["game_id"]
                    self.color = message.data["color"]
                    self.opponent = message.data["opponent"]
                    if self.gui:
                        self.gui.update_board(message.data["board"])
                elif message.type == "GAME_UPDATE":
                    if self.gui:
                        self.gui.update_board(message.data["board"])
                        if message.data["game_over"]:
                            self.gui.show_game_over(message.data["winner"])
                elif message.type == "INVALID_MOVE":
                    print("Invalid move!")
            except Exception as e:
                print(f"Error receiving message: {e}")
                self.socket.connected = False
                self.running = False
                if self.gui:
                    self.gui.shutdown()
                break

    def receive_chat_messages(self):
        while self.running and self.socket.connected:
            try:
                message = self.socket.receive_chat()
                if message and message.type == "CHAT":
                    if self.gui:
                        self.gui.display_chat(message.data["message"])
            except Exception as e:
                print(f"Error receiving chat: {e}")
                self.socket.connected = False
                self.running = False
                break

    def send_move(self, move):
        if not self.socket.connected:
            print("Cannot send move: Not connected to server")
            return
        message = Message("MOVE", {"move": move})
        self.socket.send_message(message)

    def send_chat(self, message):
        if not self.socket.connected:
            print("Cannot send chat: Not connected to server")
            return
        chat_message = Message("CHAT", {"game_id": self.game_id, "message": f"{self.player_id}: {message}"})
        self.socket.send_chat(chat_message)

    def shutdown(self):
        self.running = False
        self.socket.close()
        if self.gui:
            self.gui.shutdown()
