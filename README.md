# Studify

Studify là đồ án web hỗ trợ sinh viên UIT quản lý học tập và đời sống cá nhân. Hệ thống cung cấp trợ lý AI dùng RAG, tra cứu thông tin học vụ, tư vấn lộ trình môn học, tính GPA, lập kế hoạch và lịch ôn tập, quản lý tài liệu, nhật ký, sức khỏe tinh thần và các chức năng quản trị.

## Công nghệ

- Frontend: Next.js, React, TypeScript và Tailwind CSS.
- Backend: FastAPI, SQLAlchemy và REST API.
- Dữ liệu: PostgreSQL, Redis và Qdrant.
- AI: GPT/MiMo/Ollama, tìm kiếm ngữ nghĩa, trích dẫn nguồn và tìm kiếm web.
- Triển khai: Docker Compose và Nginx.

## Chức năng chính

- Đăng nhập bằng session cookie `HttpOnly`, quản lý hồ sơ sinh viên.
- Dashboard, thông báo, môn học, GPA và cảnh báo học vụ.
- Tư vấn chương trình đào tạo, môn tiên quyết và kế hoạch học kỳ.
- Chatbot AI trả lời theo dữ liệu UIT và hồ sơ của người dùng.
- Quản lý tài liệu, tìm kiếm, nhắc việc, lịch học và ôn tập.
- Nhật ký, mood check-in, gợi ý nhạc và thiết lập riêng tư.
- Trang quản trị nguồn dữ liệu, crawl, reindex và phản hồi.

## Cấu trúc và cách chạy

Các thư mục `1.0.x` lưu từng phiên bản của đồ án; mã nguồn hiện hành nằm trong `1.0.6/`.

```bash
cd 1.0.6
cp .env.example .env
docker compose up --build
```

Sau khi khởi động:

- Website: `http://localhost:3000`
- Nginx: `http://localhost:8080`
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

Trước khi triển khai thực tế, cần thay toàn bộ mật khẩu, API key và `JWT_SECRET` mẫu trong file `.env`.

### Chúng em đã biết làm web và hiểu hệ thống web hoạt động như thế nào.
