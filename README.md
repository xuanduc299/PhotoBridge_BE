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

### 6. Admin console (login + CRUD users)

- Mở `http://localhost:8000/admin` (hoặc domain bạn deploy) để truy cập giao diện quản trị thuần HTML/JS.
- Đăng nhập bằng user có role `admin`. Token đăng nhập được lưu tạm thời trên browser và dùng để gọi các API quản trị.
- Tính năng có sẵn:
  - Xem danh sách user, roles, trạng thái active.
  - Tạo user mới (set username, password, display name, roles, trạng thái active).
  - Sửa user (đổi display name, roles, trạng thái, đặt lại password).
  - Xóa user khác (không thể xóa hoặc vô hiệu hóa tài khoản đang đăng nhập).
- Endpoint phục vụ giao diện và API quản trị:
  - `GET /admin` → trả về trang HTML.
  - `GET /admin/users` → trả danh sách user (chỉ admin).
  - `POST /admin/users` → tạo user mới.
  - `PUT /admin/users/{user_id}` → cập nhật user.
  - `DELETE /admin/users/{user_id}` → xóa user (trừ user đang đăng nhập).

### 7. Deploy (Render/AWS/etc.)

1. Push backend folder lên repo riêng hoặc cùng repo.
2. Tạo service (Render Web Service, Elastic Beanstalk, ECS, v.v.) dùng image Python và chạy `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
3. Cấu hình biến môi trường: `DATABASE_URL` (chuỗi Neon), `JWT_SECRET_KEY`.
4. Mở cổng 80/443 và trỏ domain `api.yourdomain.com` tới service.

### 8. PhotoBridge desktop configuration

Trên máy client đặt:

```
set PHOTOBRIDGE_API_BASE=https://api.yourdomain.com  # hoặc http://localhost:8000 nếu chạy cùng máy
```

Sau đó mở ứng dụng PhotoBridge → đăng nhập bằng tài khoản bạn đã tạo ở bước 3.

### 9. Docker (build & run trên AWS EC2)

1. Cài Docker trên EC2 (Amazon Linux 2023):
   ```
   sudo dnf install docker -y
   sudo systemctl enable --now docker
   sudo usermod -aG docker ec2-user  # đăng xuất & vào lại để áp dụng
   ```
2. Chuẩn bị file cấu hình môi trường `backend/.env` với `DATABASE_URL`, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`.
3. Build image (chạy từ thư mục gốc repo):
   ```
   docker build -t photobridge-auth backend
   ```
4. Chạy container:
   ```
   docker run -d \
     --name photobridge-auth \
     --env-file backend/.env \
     -p 8000:8000 \
     photobridge-auth
   ```
   - Container dùng `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
   - Dừng / cập nhật: `docker stop photobridge-auth && docker rm photobridge-auth` rồi build lại image.
5. Bật security group / firewall cho cổng 80/443 (khuyến nghị đặt reverse proxy như Nginx hoặc ALB và chỉ mở port nội bộ 8000).

> Nếu bạn muốn push image lên ECR thay vì build trực tiếp trên EC2, đổi bước 3 thành `docker buildx build --platform linux/amd64 -t <aws_account>.dkr.ecr.../photobridge-auth:latest backend` rồi `docker push ...`.

