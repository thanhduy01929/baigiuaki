# ♟️ Cờ Vua Online Nhiều Người Chơi (Python + Socket)

Một hệ thống cờ vua **nhiều người chơi theo thời gian thực** sử dụng mô hình **Client–Server với Socket**, hỗ trợ ghép trận, chat, theo dõi ván đấu và kiểm tra nước đi hợp lệ.

---

## 🌟 Tính năng nổi bật

- 🔌 Kết nối nhiều người chơi cùng lúc qua Socket
- ♟️ Chơi cờ thời gian thực, đồng bộ bàn cờ giữa client
- 🧩 Hệ thống ghép trận (matchmaking)
- 👀 Chế độ xem trận (Spectator)
- 💬 Chat trong game
- ✅ Kiểm tra nước đi hợp lệ với `python-chess`
- ⏳ Quản lý lượt chơi và thời gian
- 🏁 Nhận diện thắng/thua/hòa (checkmate, stalemate)

---

## 🛠 Công nghệ sử dụng

| Thành phần | Công nghệ |
|----------|-----------|
| Ngôn ngữ | Python |
| Kết nối mạng | socket |
| Dữ liệu | json |
| Luật cờ | python-chess |
| Kiến trúc | Client – Server |

---

## 🧠 Kiến trúc hệ thống

### Client:
- Kết nối đến server
- Hiển thị bàn cờ (GUI/CLI)
- Gửi nước đi, tin nhắn chat
- Vào phòng, xem trận

### Server:
- Quản lý kết nối client
- Xử lý ghép trận
- Xác thực nước đi
- Đồng bộ trạng thái bàn cờ
- Phân phối chat và dữ liệu trận đấu

---

## 🔄 Luồng hoạt động

1. Client kết nối tới server
2. Tham gia lobby để ghép trận
3. Server tạo trận khi đủ 2 người
4. Người chơi đánh theo lượt
5. Server xác thực và gửi cập nhật
6. Khán giả có thể xem trận
7. Trận kết thúc → trả kết quả

---

