## PhotoBridge Auth API (FastAPI + PostgreSQL)

This backend exposes `/auth/login` for the desktop app and is preconfigured to use the Neon database you shared (`postgresql://neondb_owner:...@ep-misty-mode-a12npd2z.../neondb`). Override by setting `DATABASE_URL`.

### 1. Install dependencies

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate  # hoặc source .venv/bin/activate trên macOS/Linux
pip install -r requirements.txt
```

> Lưu ý: Requirements đã được cố định cho FastAPI 0.115 + Pydantic 2. Chỉ cần cài đúng `requirements.txt`, không cần pin thêm thư viện thủ công.

### 2. Configure environment

Create `backend/.env` (never commit secrets) if you want to override defaults:

```
DATABASE_URL=postgresql://neondb_owner:...@ep-misty-mode-a12npd2z-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
JWT_SECRET_KEY=super-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

### 3. Initialize schema and seed roles/admin

> Cần chạy script từ thư mục gốc dự án để module `backend` được tìm thấy.

```bash
cd ..  # quay về thư mục gốc D:\AutoTool\PhotoBridge nếu đang ở backend
python -m backend.init_data
# Script sẽ tạo bảng + role mặc định và hỏi bạn có muốn tạo user admin hay không
```

Nếu cần tạo hash thủ công (để cập nhật mật khẩu trực tiếp trong DB), dùng:

```bash
python -m backend.hash_password --password 12345678
# hoặc bỏ --password để chương trình hỏi qua getpass
```

### 4. Run API locally

```bash
cd ..
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### 5. Auth endpoints

- `POST /auth/login`: nhận JSON `{"username": "...", "password": "..."}` và trả về `access_token`, `refresh_token`, thông tin user.
- `POST /auth/refresh`: nhận JSON `{"refresh_token": "..."}` để lấy cặp token mới (token cũ bị thu hồi). Dùng cho tính năng auto login của desktop app.
- Tài khoản role `viewer` tự động được gán trạng thái dùng thử (`account_settings.status = "trial"`) trong 1 ngày. Khi `trial_ends_at` đã qua, backend trả 403 và chuyển trạng thái thành `expired`. Các role khác mặc định `active`. Có thể chỉnh thủ công bảng `account_settings`.

### 5. Deploy (Render/AWS/etc.)

1. Push backend folder lên repo riêng hoặc cùng repo.
2. Tạo service (Render Web Service, Elastic Beanstalk, ECS, v.v.) dùng image Python và chạy `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
3. Cấu hình biến môi trường: `DATABASE_URL` (chuỗi Neon), `JWT_SECRET_KEY`.
4. Mở cổng 80/443 và trỏ domain `api.yourdomain.com` tới service.

### 6. PhotoBridge desktop configuration

Trên máy client đặt:

```
set PHOTOBRIDGE_API_BASE=https://api.yourdomain.com  # hoặc http://localhost:8000 nếu chạy cùng máy
```

Sau đó mở ứng dụng PhotoBridge → đăng nhập bằng tài khoản bạn đã tạo ở bước 3.

