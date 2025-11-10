
import threading
import pygame
import sys
import os
import time

from client.client import ChessClientSocket
from client.gui import ChessGUI
from lobby_menu import LobbyMenu
from common.message import Message
from player_id_screen import PlayerIDScreen

class ChessClient:
    def __init__(self):
        self.socket = ChessClientSocket()
        self.player_id = None
        self.game_id = None
        self.color = None
        self.gui = None
        self.is_spectator = False
        self.running = True
        self.message_thread = None
        self.chat_thread = None

    def start(self):
        # Khởi tạo pygame trước
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Cờ Vua Multiplayer")

        # Hiển thị thông báo kết nối
        font = pygame.font.Font(None, 36)
        screen.fill((255, 255, 255))
        connecting_text = font.render("Đang kết nối tới server...", True, (0, 0, 0))
        screen.blit(connecting_text, (screen.get_width() // 2 - connecting_text.get_width() // 2,
                                     screen.get_height() // 2 - connecting_text.get_height() // 2))
        pygame.display.flip()

        # Thử kết nối tới server
        self.socket.connect()
        if not self.socket.connected:
            # Hiển thị thông báo lỗi
            screen.fill((255, 255, 255))
            error_text = font.render("❌ Không thể kết nối tới server!", True, (255, 0, 0))
            error_text2 = font.render("Hãy chắc chắn server đang chạy.", True, (0, 0, 0))
            error_text3 = font.render("Nhấn phím bất kỳ để thoát...", True, (0, 0, 0))

            screen.blit(error_text, (screen.get_width() // 2 - error_text.get_width() // 2,
                                    screen.get_height() // 2 - 50))
            screen.blit(error_text2, (screen.get_width() // 2 - error_text2.get_width() // 2,
                                     screen.get_height() // 2))
            screen.blit(error_text3, (screen.get_width() // 2 - error_text3.get_width() // 2,
                                     screen.get_height() // 2 + 50))
            pygame.display.flip()

            # Chờ nhấn phím để thoát
            waiting = True
            while waiting:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                        waiting = False

            pygame.quit()
            sys.exit(1)

        # Hiển thị màn hình nhập Player ID
        player_id_screen = PlayerIDScreen(screen)
        self.player_id = player_id_screen.run()

        if not self.player_id:
            print("❌ Chưa nhập Player ID. Thoát chương trình...")
            self.shutdown()
            return

        # Khởi chạy thread nhận tin nhắn và chat
        self.message_thread = threading.Thread(target=self.receive_messages, daemon=True)
        self.chat_thread = threading.Thread(target=self.receive_chat, daemon=True)
        self.message_thread.start()
        self.chat_thread.start()

        # Hiển thị menu phòng chờ
        pygame.display.set_caption("Phòng chờ Cờ Vua")
        lobby_menu = LobbyMenu(self, screen, 800, 600)
        action = lobby_menu.run()

        if action == "QUIT":
            self.shutdown()
            return
        elif action == "NEW_GAME":
            print("🟢 Tham gia phòng chờ...")
            self.join_lobby()
        elif action == "JOIN":
            self.game_id = lobby_menu.get_selected_game()
            print(f"🟢 Tham gia game {self.game_id}")
            self.join_lobby()
        elif action == "SPECTATE":
            self.game_id = lobby_menu.get_selected_game()
            self.is_spectator = True
            print(f"👀 Quan sát game {self.game_id}")
            self.spectate_game()

        # Kiểm tra kết nối sau khi thực hiện hành động trong lobby
        if not self.socket.connected:
            print("❌ Mất kết nối sau lobby. Thoát chương trình...")
            self.shutdown()
            return

        # Tiến hành GUI trò chơi nếu vẫn còn kết nối
        self.gui = ChessGUI(self)
        self.gui.run()

        # Dọn dẹp sau khi GUI kết thúc
        self.shutdown()

    def join_lobby(self):
        if not self.socket.connected:
            print("❌ Không thể vào phòng chờ: Chưa kết nối server")
            return
        message = Message("JOIN_LOBBY", {"player_id": self.player_id})
        self.socket.send_message(message)

    def spectate_game(self):
        if not self.socket.connected:
            print("❌ Không thể quan sát game: Chưa kết nối server")
            return
        message = Message("SPECTATE", {"game_id": self.game_id})
        self.socket.send_message(message)

    def receive_messages(self):
        while self.running and self.socket.connected:
            try:
                message = self.socket.receive()
                if not message:
                    print("⚠ Mất kết nối server.")
                    self.socket.connected = False
                    self.running = False
                    if self.gui:
                        self.gui.shutdown()
                    break
                print(f"📩 Nhận message: {message.type}")
                if message.type == "WAITING":
                    print(message.data["message"])
                elif message.type == "GAME_START" or message.type == "SPECTATE_START":
                    self.game_id = message.data["game_id"]
                    if not self.is_spectator:
                        self.color = message.data["color"]
                        print(f"✅ Game bắt đầu! Bạn là quân {self.color}")
                    else:
                        print(f"👀 Quan sát game {self.game_id}")
                    if self.gui:
                        self.gui.update_board(message.data["board"])
                elif message.type == "GAME_UPDATE":
                    if self.gui:
                        self.gui.update_board(message.data["board"])
                        if message.data["game_over"]:
                            winner = message.data["winner"]
                            print(f"🏁 Trò chơi kết thúc! Người thắng: {winner}")
                            self.gui.show_game_over(winner)
                elif message.type == "INVALID_MOVE":
                    print(message.data["message"])
                elif message.type == "ERROR":
                    print(message.data["message"])
            except Exception as e:
                print(f"⚠ Lỗi khi nhận message: {e}")
                self.socket.connected = False
                self.running = False
                if self.gui:
                    self.gui.shutdown()
                break
        print("🛑 Thread nhận message đã dừng.")

    def receive_chat(self):
        while self.running and self.socket.connected:
            try:
                message = self.socket.receive_chat()
                if not message:
                    print("⚠ Kết nối chat đóng.")
                    self.socket.connected = False
                    self.running = False
                    break
                print(f"📩 Nhận tin nhắn chat: {message.type}")
                if message.type == "CHAT":
                    print(f"💬 Chat: {message.data['message']}")
                    if self.gui:
                        timestamp = message.data.get("timestamp", time.time())
                        print(f"⏱ Nhận message với timestamp: {timestamp}")
                        self.gui.display_chat(message.data["message"], timestamp)
            except Exception as e:
                print(f"⚠ Lỗi khi nhận chat: {e}")
                self.socket.connected = False
                self.running = False
                break
        print("🛑 Thread chat đã dừng.")

    def send_move(self, move):
        if not self.is_spectator and self.socket.connected:
            message = Message("MOVE", {"move": move})
            self.socket.send_message(message)
        else:
            print("❌ Không thể gửi nước đi: Không kết nối hoặc đang ở chế độ quan sát")

    def send_chat(self, message_text, timestamp=None):
        if self.socket.connected:
            if timestamp is None:
                timestamp = time.time()
            message = Message("CHAT", {
                "game_id": self.game_id,
                "message": f"{self.player_id}: {message_text}",
                "timestamp": timestamp
            })
            self.socket.send_chat(message)
        else:
            print("❌ Không thể gửi chat: Chưa kết nối server")

    def shutdown(self):
        if not self.running:
            return
        self.running = False
        # Chờ các thread kết thúc
        if self.message_thread and self.message_thread.is_alive():
            self.message_thread.join(timeout=1.0)
        if self.chat_thread and self.chat_thread.is_alive():
            self.chat_thread.join(timeout=1.0)
        self.socket.close()
        if self.gui:
            self.gui.shutdown()
        pygame.quit()
        print("🔻 Client đã tắt hoàn tất.")
        sys.exit(0)

def start_client():
    client = ChessClient()
    client.start()