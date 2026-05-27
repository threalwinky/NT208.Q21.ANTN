# Studify v1.0.4

Studify là nền tảng web full-stack dành cho sinh viên Trường Đại học Công nghệ Thông tin - ĐHQG-HCM. Bản `1.0.4` được nâng từ `1.0.3`, thêm MiMo v2.5 cho generation, giữ Ollama cho embedding, nâng cấp RAG tiếng Việt và bổ sung các module học vụ/wellbeing để demo như sản phẩm thật.

## 1. Cấu trúc phiên bản

Trong thư mục cha `1.0.4/`:

```text
1.0.4/
├── local/     # chỉ để chạy máy cá nhân: .env thật, dữ liệu thử, cache, artifact
└── deploy/    # thư mục an toàn để đưa lên GitHub/triển khai
```

Không đưa secret thật vào `deploy/`. File `.env.example` chỉ chứa placeholder.

## 2. Stack

- Frontend: Next.js + TypeScript + Tailwind CSS.
- Backend: FastAPI + SQLAlchemy.
- Database: PostgreSQL.
- Queue/cache: Redis.
- Vector DB: Qdrant.
- Generation: MiMo v2.5 OpenAI-compatible API hoặc Ollama fallback.
- Embedding: Ollama `nomic-embed-text`.
- Worker: Python worker đọc Redis queue cho crawl, reindex, reminder và refresh corpus.

## 3. Cấu hình quan trọng

```env
APP_VERSION=1.0.4
APP_ENV=development

LLM_PROVIDER=mimo
MIMO_BASE_URL=https://token-plan-ams.xiaomimimo.com/v1
MIMO_API_KEY=replace_me
MIMO_CHAT_MODEL=mimo-v2.5-pro
MIMO_TEMPERATURE=0.2
MIMO_TOP_P=0.9
MIMO_MAX_COMPLETION_TOKENS=1200

EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBED_MODEL=nomic-embed-text

ENABLE_WELLBEING=true
ENABLE_SPOTIFY=false
ENABLE_AI_NOTE_REFLECTION=false
```

Khi `APP_ENV=production`, backend sẽ fail startup nếu các secret quan trọng còn là placeholder như `secret`, `changeme`, `studify123`, `replace_me` hoặc `replace-this-with-a-long-random-secret`.

## 4. Chạy local

```bash
cp .env.example .env
docker compose up --build
```

Service chính:

- frontend: `http://localhost:3000`
- backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Qdrant: `http://localhost:6333`
- PostgreSQL: `localhost:5432` trong compose network
- Redis: `localhost:6379`

Health check:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/dependencies
```

## 5. Module chính

### Chat/RAG

- Frontend: `/assistant`
- API: `/api/v1/chat`
- Generation qua `get_llm_provider()`.
- Embedding qua `get_embedding_provider()`.
- Query rewrite hỗ trợ viết tắt UIT: `dkhp`, `tkb`, `ctdt`, `cntt`, `khmt`, `ktmt`, `mmt`, `httt`, `kkht`.
- Retrieval dùng scoring kết hợp vector, lexical, topic, nguồn chính thức và freshness.
- Citation validator loại URL không nằm trong retrieved contexts.
- Câu hỏi học vụ thiếu nguồn chắc trả lời: `Mình chưa tìm thấy nguồn UIT đủ chắc để trả lời chính xác câu này.`

### Học vụ và học tập

- `/academic`: trung tâm học vụ.
- `/advisor`: degree audit, prerequisite graph, semester plan, academic risk.
- `/courses`: danh mục môn học.
- `/gpa`: tính GPA và mô phỏng GPA tích lũy.
- API mới: `/profile`, `/courses`, `/gpa`, `/academic-risk`, `/documents`, `/search`, `/feedback`.

### Wellbeing

- `/wellbeing`: overview.
- `/wellbeing/checkin`: mood check-in nhiều chiều.
- `/wellbeing/notes`: ghi chú riêng tư, xóa mềm.
- `/wellbeing/music`: nhạc theo mood với Spotify fallback.
- `/settings/privacy`: nguyên tắc riêng tư và crisis guardrail.
- `/settings/integrations/spotify`: trạng thái Spotify optional.

Wellbeing không chẩn đoán, không thay thế tư vấn tâm lý và không tự gửi full private note sang LLM.

### Quản trị

- `/admin`: nguồn crawl, crawler log, queue, config, reindex, upload tài liệu.
- `/api/v1/admin/feedback`: admin xử lý phản hồi người dùng.

## 6. Crawl, import và reindex

Chạy crawl từ UI admin hoặc API:

```bash
POST /api/v1/admin/sources/{source_id}/crawl
```

Reindex toàn bộ:

```bash
POST /api/v1/admin/reindex
```

Reindex một tài liệu:

```bash
POST /api/v1/documents/{document_id}/reindex
```

Import snapshot:

```bash
cd backend
python -m app.scripts.import_snapshot_data
```

Đánh giá RAG:

```bash
cd backend
python -m app.scripts.evaluate_rag
```

Suite mẫu: `backend/data/evaluation/uit_rag_suite.json`.

## 7. Tài khoản seed

- Sinh viên: `24522045` / `24522045`
- Sinh viên: `24520033` / `24520033`
- Admin: `admin` / `admin`

## 8. Kiểm thử

Backend:

```bash
cd backend
python -m pytest
```

Frontend:

```bash
cd frontend
npm install
npm run lint
npm run build
```

Docker config:

```bash
docker compose config
```

Secret scan trước khi push `deploy/`:

```bash
grep -R "tp-\|MIMO_API_KEY\|SPOTIFY_CLIENT_SECRET\|SPOTIFY_REFRESH_TOKEN\|JWT_SECRET\|studify123" . \
  --exclude=".env.example" \
  --exclude-dir=".git" \
  --exclude-dir="node_modules" \
  --exclude-dir=".next" \
  --exclude-dir="__pycache__"
```

Kỳ vọng: không có secret thật trong `deploy/`; các dòng placeholder trong `.env.example` đã được exclude.

## 9. Tài liệu bổ sung

- `docs/DEMO_SCRIPT.md`
- `docs/EVALUATION_REPORT.md`
- `docs/WELLBEING_SAFETY.md`
- `docs/WELLBEING_FEATURE_SPEC.md`
- `docs/SPOTIFY_INTEGRATION.md`
- `docs/KNOWN_LIMITATIONS.md`
