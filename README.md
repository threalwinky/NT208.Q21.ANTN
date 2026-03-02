# NT208.Q21.ANTN - Studify MVP

Studify là hệ thống hỗ trợ sinh viên gồm chatbot AI, ghi chú/nhiệm vụ học tập, gợi ý lịch học cơ bản và Pomodoro timer.

## 1) Kiến trúc nhanh

- `frontend` (React + Vite): giao diện đăng nhập/đăng ký/dashboard.
- `backend` (Node.js + Express + MongoDB): API nghiệp vụ, lưu dữ liệu user/note/task.
- `AI` (FastAPI): nhận message và trả lời theo intent.
- `nginx`: phục vụ frontend static + reverse proxy `/api` về backend.
- `db` (MongoDB): lưu trữ dữ liệu.

Tài liệu phân tích chi tiết: xem file `SYSTEM_ANALYSIS.md`.

## 2) Nâng cấp AI trong bản MVP này

AI service đã được nâng từ rule-based thuần sang mô hình lai:

- Nếu có model đã train (`AI/data/intent_model.joblib`) thì dùng model ML để phân loại intent.
- Nếu model chưa có hoặc confidence thấp thì fallback về rule-based keyword.

Kết quả `/chat` trả thêm:

- `source`: `ml` hoặc `rule`
- `confidence`: xác suất dự đoán (khi dùng ML)

## 3) Dataset và script train

- Dataset mẫu: `Studify/AI/data/intent_dataset.jsonl`
- Script train: `Studify/AI/scripts/train_intent.py`

### Định dạng dataset

Mỗi dòng là một JSON object:

```json
{"text": "Em đang stress vì deadline", "label": "mental_support"}
```

Các nhãn hiện dùng:

- `mental_support`
- `career`
- `study`
- `general`

### Train model AI (local)

Từ thư mục `Studify/AI`:

```bash
pip install -r requirements.txt
python scripts/train_intent.py
```

Artifact sinh ra:

- `data/intent_model.joblib`
- `data/intent_metrics.json`

Tuỳ chọn:

```bash
python scripts/train_intent.py --test-size 0.3 --min-confidence 0.5
```

## 4) Khởi chạy app bằng Docker

Từ thư mục `Studify`:

```bash
docker compose build
docker compose up -d
```

Truy cập app tại:

- `http://localhost:3000`

Kiểm tra nhanh health:

- `http://localhost:3000/api/health`
- `http://localhost:3000/api/ai/chat` (qua frontend hoặc gọi API)

> Lưu ý: nếu bạn train model sau khi container `ai` đã chạy, cần restart service AI để nạp model mới.

```bash
docker compose restart ai
```

## 5) Khởi chạy local không Docker

### 5.1 MongoDB

Chạy MongoDB local và đảm bảo có URI phù hợp (ví dụ `mongodb://localhost:27017/studify`).

### 5.2 AI service

Từ `Studify/AI`:

```bash
pip install -r requirements.txt
python scripts/train_intent.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5.3 Backend

Từ `Studify/backend`:

```bash
npm install
PORT=5000 MONGO_URI=mongodb://localhost:27017/studify AI_SERVICE_URL=http://localhost:8000 npm start
```

### 5.4 Frontend

Từ `Studify/frontend`:

```bash
npm install
VITE_API_URL=http://localhost:5000/api npm run dev
```

Mở trình duyệt tại URL Vite in ra terminal (thường là `http://localhost:5173`).

## 6) Luồng demo gợi ý

1. Đăng ký tài khoản mới với profile sinh viên.
2. Vào Dashboard:
	- Chatbot AI: hỏi câu học tập/nghề nghiệp/tinh thần.
	- Notes/Task: thêm note dạng ngôn ngữ tự nhiên và tạo task deadline.
	- Pomodoro: chạy timer 25 phút.
3. Quan sát API chat trả `source=ml` nếu model đã được train và nạp thành công.