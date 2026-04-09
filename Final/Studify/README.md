# Studify

Studify là nền tảng web full-stack dành cho sinh viên Trường Đại học Công nghệ Thông tin - ĐHQG-HCM.
Hệ thống tập trung vào 5 mảng sử dụng thực tế:

- hỏi đáp học vụ bằng tiếng Việt với citation
- tổng hợp thông báo UIT
- quản lý lịch học, lịch thi, deadline và nhắc việc
- check-in cảm xúc nhẹ và góc đồng hành
- quản trị crawler, knowledge base và cấu hình prompt

## 1. Pattern rút ra từ `examples/`

Trước khi dựng project này, codebase đã bám theo 2 pattern chính trong thư mục `examples/`:

- `examples/NT208`
  - dùng monorepo tách `frontend` và `backend`
  - frontend theo Next.js App Router
  - backend theo FastAPI với route version hóa `api/v1`
  - cấu trúc router, config, deps khá gọn và dễ mở rộng
- `examples/Studify`
  - ưu tiên tư duy RAG thay vì fine-tune cứng
  - tách rõ phần chat, document processing, vector retrieval và luồng knowledge base
  - workflow admin cập nhật kho tri thức rồi để user chỉ cần hỏi

Từ đó, bản Studify cuối cùng chọn:

- frontend: Next.js 16 + TypeScript + Tailwind CSS
- backend: FastAPI + SQLAlchemy
- database: PostgreSQL
- queue/cache: Redis
- vector store: Qdrant
- LLM runtime: Ollama chạy trên máy host
- model mặc định: `minimax-m2.7:cloud`
- worker nền: Python worker riêng dùng Redis queue

## 2. Kiến trúc thư mục

```text
Studify/
├── .env.example
├── docker-compose.yml
├── README.md
├── frontend/
│   ├── app/
│   │   ├── login/
│   │   ├── dashboard/
│   │   ├── assistant/
│   │   ├── academic/
│   │   ├── planner/
│   │   ├── announcements/
│   │   ├── wellbeing/
│   │   └── admin/
│   ├── components/
│   └── lib/
└── backend/
    ├── app/
    │   ├── api/v1/endpoints/
    │   ├── core/
    │   ├── db/
    │   ├── models/
    │   ├── schemas/
    │   ├── scripts/
    │   ├── services/
    │   └── worker/
    ├── data/
    │   ├── source_registry.json
    │   ├── snapshots/
    │   └── processed/
    └── tests/
```

## 3. Các module chính

### Chatbot Studify

- route frontend: `/assistant`
- mode hiện có:
  - `ACADEMIC`: hỏi học vụ, thông báo, thủ tục, CTĐT
  - `WELLBEING`: đồng hành nhẹ khi buồn, stress, quá tải
- backend dùng retrieval từ:
  - `collected_documents`
  - `document_chunks`
  - Qdrant vector search
- câu trả lời sinh bởi Ollama và trả kèm citation

### Trung tâm học vụ

- route frontend: `/academic`
- hiển thị:
  - tài liệu học vụ
  - mốc học vụ
  - hướng dẫn thủ tục

### Lịch và nhắc việc

- route frontend: `/planner`
- có:
  - lịch học
  - lịch thi
  - task list
  - tạo task mới
  - nhắc việc nội bộ qua worker

### Bảng thông báo UIT

- route frontend: `/announcements`
- gộp thông báo theo nhóm
- có nút lưu để đọc lại sau

### Góc đồng hành

- route frontend: `/wellbeing`
- chỉ hỗ trợ ở mức:
  - buồn
  - stress
  - quá tải
  - cần một nơi để thả lỏng
- không có logic nhạy cảm sâu hơn
- có:
  - check-in cảm xúc
  - nhật ký ngắn
  - tài nguyên hỗ trợ trong trường

### Quản trị

- route frontend: `/admin`
- có:
  - danh sách nguồn crawl
  - bật/tắt nguồn
  - chạy crawl lại
  - reindex toàn bộ vector
  - sửa prompt hệ thống
  - xem log crawler

## 4. Mô hình dữ liệu chính

Các bảng cốt lõi:

- `users`
- `student_profiles`
- `chat_sessions`
- `chat_messages`
- `data_sources`
- `collected_documents`
- `document_chunks`
- `content_categories`
- `announcements`
- `academic_events`
- `class_schedules`
- `exam_schedules`
- `tasks`
- `reminders`
- `mood_states`
- `mood_journals`
- `system_configs`
- `crawler_logs`
- `faqs`
- `departments`
- `support_resources`
- `saved_announcements`
- `in_app_notifications`

## 5. Cách chạy local

### 5.1. Chuẩn bị Ollama trên máy host

Bạn đã có sẵn model `minimax-m2.7:cloud`, nên backend và worker sẽ gọi Ollama qua host tunnel:

- `OLLAMA_BASE_URL=http://host.docker.internal:11435`
- `OLLAMA_HOST_PORT=11434`
- `OLLAMA_PROXY_PORT=11435`
- `OLLAMA_CHAT_MODEL=minimax-m2.7:cloud`

Kiểm tra nhanh:

```bash
ollama list
ollama ps
```

### 5.2. Tạo file `.env`

```bash
cp .env.example .env
```

### 5.3. Chạy toàn hệ thống

```bash
docker-compose up --build
```

Các service chính:

- frontend: `http://localhost:3000`
- backend: `http://localhost:8000`
- ollama tunnel: `http://host.docker.internal:11435` từ bên trong container
- qdrant: `http://localhost:6333`
- postgres: `localhost:15432` nếu máy đã chiếm `5432`, ngược lại dùng cổng trong `.env`
- redis: `localhost:6379`

## 6. Tài khoản seed

- sinh viên:
  - username: `22520001`
  - password: `22520001`
- quản trị:
  - username: `admin`
  - password: `admin`

## 7. Cách backend bootstrap dữ liệu

Project này **không dùng Alembic**.
Schema được tạo tự động từ model bằng:

```python
Base.metadata.create_all(bind=engine)
```

Luồng khởi tạo:

1. backend start
2. `app.db.init_db.init_db()` tạo schema nếu chưa có
3. `python -m app.scripts.seed` nạp dữ liệu mẫu UIT

## 8. Crawler và indexing

### Registry nguồn crawl

Seed sẵn 6 nguồn UIT:

- `https://www.uit.edu.vn`
- `https://daa.uit.edu.vn`
- `https://student.uit.edu.vn`
- `https://ctsv.uit.edu.vn`
- `https://courses.uit.edu.vn`
- `https://oep.uit.edu.vn/vi`

### Bước chuẩn bị corpus trước Docker

Nếu bạn muốn chuẩn bị trước dữ liệu RAG ngay trên máy host, chạy:

```bash
python train.py --target-documents 30
```

Lệnh này không fine-tune model. Nó chỉ:

- thu thập tài liệu công khai từ UIT
- trích text từ HTML và PDF
- lưu snapshot vào `backend/data/snapshots`
- lưu PDF vào `backend/data/pdfs`
- tạo corpus chuẩn hóa tại `backend/data/processed/uit_documents.jsonl`

Ghi chú:

- `train.py` mặc định bỏ qua `courses.uit.edu.vn` trong bước chuẩn bị corpus vì phần public của LMS không mang nhiều giá trị cho RAG
- nếu máy có thêm OCR runtime, script có thể mở rộng để lấy text tốt hơn từ PDF scan
- worker sẽ tự làm mới corpus định kỳ mỗi `72` giờ, sau đó import lại vào PostgreSQL và re-index vector

### Crawler hỗ trợ

- follow link cùng domain
- max page per source
- dedup theo `url` + `content_hash`
- clean HTML text
- đọc PDF public nếu gặp link `.pdf`
- chunk nội dung
- embedding qua Ollama
- upsert vector vào Qdrant
- tạo/đồng bộ `announcements`

### Chạy crawl

Từ UI admin hoặc gọi API:

```bash
POST /api/v1/admin/sources/{source_id}/crawl
```

### Reindex toàn bộ

```bash
POST /api/v1/admin/reindex
```

Worker sẽ đọc job từ Redis queue `studify_jobs`.

### Làm mới corpus định kỳ 3 ngày/lần

- worker kiểm tra lịch mỗi 5 phút
- nếu đã quá `72` giờ từ lần thành công gần nhất, worker sẽ tự queue job làm mới corpus
- job này sẽ:
  - thu thập thêm tài liệu từ các nguồn UIT đang bật
  - chuẩn hóa lại `backend/data/processed/uit_documents.jsonl`
  - import/update tài liệu trong PostgreSQL
  - re-embed và đồng bộ lại vector vào Qdrant
- admin có thể bấm `Làm mới corpus` trong trang quản trị để chạy thủ công ngay

## 9. Chat và RAG

Luồng trả lời:

1. user gửi câu hỏi
2. backend phân loại `ACADEMIC`, `ANNOUNCEMENT`, `WELLBEING`, `GENERAL`
3. RAG lấy embedding query
4. search Qdrant
5. fallback keyword search nếu vector chưa có
6. dựng context block
7. gọi Ollama model `minimax-m2.7:cloud`
8. trả lời tiếng Việt + citation

## 10. Kiểm tra đã chạy

Đã kiểm tra:

- `python3 -m compileall Studify/backend/app`
- `cd Studify/backend && .venv/bin/pytest -q`
- `cd Studify/frontend && npm run lint`
- `cd Studify/frontend && npm run build`

## 11. Giới hạn hiện tại

- frontend hiện render statically và gọi API client-side
- Qdrant/Ollama cần service thật để retrieval hoạt động đầy đủ
- notification hiện ở mức in-app notification qua worker
- chưa có email sender thực
- crawler mới là generic crawler theo domain, chưa có selector riêng cho từng site UIT
- calendar hiện là list-first UI, chưa có month grid chuyên dụng

## 12. Gợi ý bước tiếp theo

- thêm selector riêng cho từng nguồn UIT để tăng chất lượng metadata
- bổ sung OCR nếu muốn đọc ảnh scan tốt hơn
- thêm kanban/calendar chuyên dụng cho planner
- thêm upload PDF nội bộ cho admin knowledge base
- thêm authentication thật bằng SSO nếu có tích hợp về sau
