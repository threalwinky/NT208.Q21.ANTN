# Studify v1.0.6

Studify là nền tảng web full-stack dành cho sinh viên Trường Đại học Công nghệ Thông tin - ĐHQG-HCM. Bản `1.0.6` sửa các điểm quan trọng của `1.0.5`: chatbot biết dùng hồ sơ học vụ cá nhân của sinh viên đang đăng nhập, auth chuyển sang cookie `HttpOnly`, Docker chạy bằng bridge network trên Docker Desktop, health check kiểm tra dependency thật hơn.

## 1. Cấu trúc phiên bản

Trong thư mục cha `1.0.6/`:

```text
1.0.6/
├── local/     # chạy máy cá nhân: .env thật, dữ liệu thử, cache, artifact
└── deploy/    # thư mục an toàn để đưa lên GitHub/triển khai
```

Không đưa secret thật vào `deploy/`. File `.env.example` chỉ chứa placeholder.

## 2. Stack

- Frontend: Next.js + TypeScript + Tailwind CSS.
- Backend: FastAPI + SQLAlchemy.
- Database: PostgreSQL.
- Queue/cache: Redis.
- Vector DB: Qdrant.
- Generation: MiMo v2.5 qua Anthropic-compatible API/SSE hoặc Ollama fallback.
- Embedding: Ollama `nomic-embed-text`.
- Web search: Selenium + headless Chromium tìm DuckDuckGo, sau đó đọc nhiều trang nguồn song song bằng `httpx.AsyncClient`.
- Worker: Python worker đọc Redis queue cho crawl, reindex, reminder và refresh corpus.
- Reverse proxy/load balancing: Nginx Alpine với upstream pool cho frontend và backend.

## 3. Cấu hình quan trọng

```env
APP_VERSION=1.0.6
APP_ENV=development

LLM_PROVIDER=mimo
MIMO_BASE_URL=https://token-plan-ams.xiaomimimo.com/v1
MIMO_ANTHROPIC_BASE_URL=https://token-plan-ams.xiaomimimo.com/anthropic/v1
MIMO_API_KEY=replace_me
MIMO_CHAT_MODEL=mimo-v2.5-pro
MIMO_TEMPERATURE=0.2
MIMO_TOP_P=0.9
MIMO_MAX_COMPLETION_TOKENS=1200
MIMO_TIMEOUT_SECONDS=120

EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBED_MODEL=nomic-embed-text

ENABLE_MIMO_STREAMING=true
ENABLE_WEB_SEARCH=true
WEB_SEARCH_MAX_RESULTS=5
ENABLE_WELLBEING=true
ENABLE_SPOTIFY=false
ENABLE_AI_NOTE_REFLECTION=false
```

Backend image đã cài `chromium`, `chromium-driver` và set:

```env
CHROMIUM_BIN=/usr/bin/chromium
CHROMEDRIVER_BIN=/usr/bin/chromedriver
```

Khi `APP_ENV=production`, backend sẽ fail startup nếu các secret quan trọng còn là placeholder như `secret`, `changeme`, `studify123`, `replace_me` hoặc `replace-this-with-a-long-random-secret`.

## 4. Chạy local

```bash
cp .env.example .env
docker compose up --build
```

Service chính:

- frontend: `http://localhost:3000`
- nginx/load balancer: `http://localhost:8080`
- backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Qdrant: `http://localhost:6333`
- PostgreSQL: `localhost:5432` trong compose network
- Redis: `localhost:6379`

Fresh setup khi clone mới hoặc muốn tạo DB sạch:

```bash
./scripts/fresh_start.sh
```

Script này khởi động PostgreSQL/Redis/Qdrant, chạy `init_db()`, stamp Alembic head, seed dữ liệu mẫu rồi build toàn bộ stack.

Health check:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/dependencies
curl http://localhost:8080/nginx-health
curl http://localhost:8080/health
```

Nginx route `/` về frontend và route `/api/v1/*`, `/health`, `/docs`, `/openapi.json` về backend. Từ `1.0.6`, toàn bộ service chạy chung bridge network `studify`, backend truy cập dependency bằng service name như `postgres`, `redis`, `qdrant`.

Auth dùng cookie `studify_session` có `HttpOnly`, `SameSite=Lax`. Frontend chỉ lưu thông tin người dùng không nhạy cảm trong `localStorage`, không lưu JWT.

## 5. Module chính

### Chat/RAG

- Frontend: `/assistant`
- API: `/api/v1/chat`
- Streaming API: `POST /api/v1/chat/stream` trả Server-Sent Events, frontend render token/chunk dần.
- Generation qua `get_llm_provider()`; mặc định dùng MiMo Anthropic-compatible SSE.
- Embedding qua `get_embedding_provider()`; mặc định dùng Ollama `nomic-embed-text`.
- Query rewrite hỗ trợ viết tắt UIT: `dkhp`, `tkb`, `ctdt`, `cntt`, `khmt`, `ktmt`, `mmt`, `httt`, `kkht`.
- Retrieval dùng scoring kết hợp vector, lexical, topic, nguồn chính thức và freshness.
- Citation validator loại URL không nằm trong retrieved contexts.
- Câu hỏi học vụ thiếu nguồn chắc trả lời: `Mình chưa tìm thấy nguồn UIT đủ chắc để trả lời chính xác câu này.`

#### Chế độ Nhanh / Mở rộng

Chat UI có hai nút chọn mode:

- **Nhanh**: ưu tiên trả lời gọn, dùng ít context hơn. Nếu dữ liệu RAG không đủ hoặc câu hỏi cần thông tin mới, model vẫn được phép gọi web search nhưng giới hạn `max_results=2` để giảm thời gian chờ.
- **Mở rộng**: dùng context đầy đủ hơn và web search sâu hơn theo `WEB_SEARCH_MAX_RESULTS` (mặc định `5`). Phù hợp với câu hỏi cần kiểm chứng nhiều nguồn hoặc thông tin mới nhất.

Cả hai mode đều lưu vào cùng lịch sử chat; mỗi request gửi thêm `chat_mode: "quick" | "extended"`.

#### Web search riêng

Studify không dùng web search của MiMo. Tool `web_search` nằm trong backend:

1. Selenium + headless Chromium mở DuckDuckGo bằng URL query trực tiếp.
2. Lấy danh sách kết quả thật, bỏ link nội bộ DuckDuckGo.
3. Với mỗi URL nguồn, backend fetch song song bằng `httpx.AsyncClient + asyncio.gather`.
4. HTML được làm sạch bằng BeautifulSoup, bỏ `script/style/nav/header/footer`, rồi đưa excerpt vào context cho LLM.
5. UI hiển thị trạng thái `Đang tìm kiếm web` trong lúc tool chạy.

### Học vụ và học tập

- `/advisor`: degree audit, prerequisite graph, semester plan, academic risk và hồ sơ sinh viên.
- `/gpa`: tính GPA và mô phỏng GPA tích lũy.
- `/search`: tìm nhanh, học vụ, môn học và tài liệu trong một trang tab.
- API chính: `/profile`, `/courses`, `/gpa`, `/academic-risk`, `/documents`, `/search`, `/feedback`.

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
python -m py_compile app/services/chat_service.py app/services/web_search_service.py
```

Smoke test web search trong container backend:

```bash
docker run --rm -i --network host local_backend python - <<'PY'
import asyncio
from app.services.web_search_service import WebSearchService

async def main():
    text = await WebSearchService().search('site:daa.uit.edu.vn thông báo UIT', max_results=2)
    print(text[:1500])

asyncio.run(main())
PY
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

## 9. Sync local sang deploy

Dùng script:

```bash
bash local/sync-to-deploy.sh
```

Script copy `local/` sang `deploy/` và loại trừ các file dev-only: `.env`, `node_modules`, `.next`, `__pycache__`, `.pytest_cache`, `docker-compose.local.yml`, `sync-to-deploy.sh`, coverage artifact và `backend/data/uploads`.

Sau sync có thể kiểm tra nhanh:

```bash
python - <<'PY'
from pathlib import Path
local = Path('1.0.6/local')
deploy = Path('1.0.6/deploy')
print((local / 'README.md').read_bytes() == (deploy / 'README.md').read_bytes())
PY
```

## 10. Tài liệu bổ sung

- `docs/DEMO_SCRIPT.md`
- `docs/EVALUATION_REPORT.md`
- `docs/WELLBEING_SAFETY.md`
- `docs/WELLBEING_FEATURE_SPEC.md`
- `docs/SPOTIFY_INTEGRATION.md`
- `docs/KNOWN_LIMITATIONS.md`
- `explain.md`
