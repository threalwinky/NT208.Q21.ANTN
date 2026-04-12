# Dữ liệu UIT cho Studify

Thư mục này chứa snapshot tài liệu công khai liên quan tới sinh viên UIT để phục vụ RAG.

Các lớp dữ liệu:

- `source_registry.json`
  - danh sách nguồn UIT và cấu hình crawl
- `snapshots/`
  - các file `.md` đã được crawl và trích text
- `processed/uit_documents.jsonl`
  - bản ghi chuẩn hóa dùng để import vào PostgreSQL + Qdrant

Lưu ý:

- dữ liệu ở đây dùng để index và retrieval
- không dùng để fine-tune cứng model
- có thể chạy lại crawler để cập nhật snapshot

Lệnh crawl:

```bash
cd backend
python -m app.scripts.crawl_uit_data --limit-per-source 4
```

Lệnh chuẩn bị corpus RAG trước khi chạy Docker:

```bash
cd ..
python3 train.py --target-documents 300
```

Script này thu thập tài liệu công khai từ 12 nguồn UIT, lưu snapshot vào `backend/data/`, trích text từ HTML/PDF/CSV/XLSX, OCR nếu có runtime phù hợp, và tạo `processed/uit_documents.jsonl` để import vào knowledge base.

Mặc định, bước train host sẽ bỏ qua `courses.uit.edu.vn` vì phần public chủ yếu là trang đăng nhập/chính sách và không hữu ích cho RAG sinh viên.

Sau khi hệ thống đã chạy bằng Docker, worker sẽ tiếp tục làm mới corpus định kỳ 3 ngày/lần và import lại vào knowledge base.

Lệnh import vào knowledge base:

```bash
cd backend
python -m app.scripts.import_snapshot_data
```
