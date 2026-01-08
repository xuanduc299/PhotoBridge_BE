from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .config import get_settings
from .database import engine
from .deps import AuthenticatedUser, get_db, require_admin
from .security import create_access_token, generate_refresh_token, hash_password, verify_password


TRIAL_POLICY = {"operator": 2}  # days

models.Base.metadata.create_all(bind=engine)
settings = get_settings()

app = FastAPI(title="PhotoBridge Auth API", version="1.2.0")
admin_router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_APP_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <title>PhotoBridge Admin</title>
  <style>
    :root {
      color-scheme: light dark;
    }
    body {
      font-family: "Segoe UI", Roboto, sans-serif;
      margin: 0;
      background: #f5f7fb;
      color: #1f2328;
    }
    header {
      background: #111827;
      color: #fff;
      padding: 24px;
      text-align: center;
    }
    .container {
      max-width: 1100px;
      margin: 32px auto;
      padding: 0 16px 48px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 24px;
      margin-bottom: 32px;
    }
    .card {
      background: #fff;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 10px 30px rgba(17, 24, 39, 0.08);
    }
    h2 {
      margin-top: 0;
      font-size: 20px;
    }
    label {
      display: block;
      font-weight: 600;
      margin-top: 12px;
    }
    input, textarea {
      width: 100%;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid #d0d7de;
      margin-top: 6px;
      font-size: 15px;
      box-sizing: border-box;
    }
    input[readonly] {
      background: #f3f4f6;
    }
    button {
      border: none;
      border-radius: 8px;
      padding: 10px 16px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s ease;
    }
    .btn-primary {
      background: #2563eb;
      color: #fff;
    }
    .btn-primary:hover {
      background: #1d4ed8;
    }
    .btn-secondary {
      background: #e5e7eb;
      color: #111827;
    }
    .btn-danger {
      background: #dc2626;
      color: #fff;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
    }
    th {
      text-transform: uppercase;
      font-size: 12px;
      letter-spacing: 0.05em;
      color: #6b7280;
    }
    .status {
      padding: 8px 12px;
      border-radius: 8px;
      margin-bottom: 16px;
      font-weight: 600;
    }
    .status.error {
      background: #fee2e2;
      color: #b91c1c;
    }
    .status.success {
      background: #dcfce7;
      color: #166534;
    }
    .hidden {
      display: none !important;
    }
    .table-actions {
      display: flex;
      gap: 8px;
    }
    .toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .toolbar button {
      background: #111827;
      color: #fff;
    }
  </style>
</head>
<body>
  <header>
    <h1>PhotoBridge Admin Console</h1>
    <p>Quản lý tài khoản người dùng nhanh chóng, gọn nhẹ.</p>
  </header>
  <div class="container">
    <div id="status" class="status hidden"></div>

    <div id="login-view" class="card">
      <h2>Đăng nhập quản trị</h2>
      <form id="login-form">
        <label for="login-username">Username</label>
        <input id="login-username" name="username" required />
        <label for="login-password">Password</label>
        <input id="login-password" name="password" type="password" required />
        <button class="btn-primary" style="margin-top:16px;" type="submit">Đăng nhập</button>
      </form>
    </div>

    <div id="app-view" class="hidden">
      <div class="grid">
        <div class="card" style="grid-column: span 2;">
          <div class="toolbar">
            <h2>Danh sách người dùng</h2>
            <button id="logout-btn">Đăng xuất</button>
          </div>
          <div class="table-wrapper">
            <table id="users-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Username</th>
                  <th>Tên hiển thị</th>
                  <th>Roles</th>
                  <th>Trạng thái</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <h2 id="form-title">Tạo tài khoản mới</h2>
          <form id="user-form">
            <label for="user-username">Username</label>
            <input id="user-username" required />

            <label for="user-password">Password</label>
            <input id="user-password" type="password" required />

            <label for="user-display">Display name</label>
            <input id="user-display" />

            <label for="user-roles">Roles (cách nhau bằng dấu phẩy)</label>
            <input id="user-roles" placeholder="vd: admin,viewer" />

            <label style="display:flex;align-items:center;gap:8px;margin-top:18px;">
              <input id="user-active" type="checkbox" checked />
              Kích hoạt tài khoản
            </label>

            <div style="margin-top:18px; display:flex; gap:12px;">
              <button id="user-submit" class="btn-primary" type="submit">Tạo user</button>
              <button id="cancel-edit" class="btn-secondary hidden" type="button">Hủy chỉnh sửa</button>
            </div>
          </form>
        </div>

        <div class="card hidden" id="settings-card">
          <h2 id="settings-title">Account Settings</h2>
          <form id="settings-form">
            <input type="hidden" id="settings-user-id" />
            
            <label for="settings-username">Username</label>
            <input id="settings-username" readonly />

            <label for="settings-status">Status</label>
            <select id="settings-status" style="width:100%; padding:10px 12px; border-radius:8px; border:1px solid #d0d7de; margin-top:6px;">
              <option value="active">Active</option>
              <option value="trial">Trial</option>
              <option value="locked">Locked</option>
            </select>

            <label for="settings-max-devices">Max Devices (0 = unlimited)</label>
            <input id="settings-max-devices" type="number" min="0" max="100" placeholder="0 = unlimited" />
            <small style="color:#6b7280; display:block; margin-top:4px;">
              0/NULL = Unlimited | 1 = Single device | 2+ = Limited devices
            </small>

            <label for="settings-trial-ends">Trial Ends At (optional)</label>
            <input id="settings-trial-ends" type="datetime-local" />

            <div style="margin-top:18px; display:flex; gap:12px;">
              <button class="btn-primary" type="submit">Lưu Settings</button>
              <button id="cancel-settings" class="btn-secondary" type="button">Đóng</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>

  <script>
    const loginView = document.getElementById("login-view");
    const appView = document.getElementById("app-view");
    const loginForm = document.getElementById("login-form");
    const userForm = document.getElementById("user-form");
    const statusBox = document.getElementById("status");
    const logoutBtn = document.getElementById("logout-btn");
    const tableBody = document.querySelector("#users-table tbody");
    const formTitle = document.getElementById("form-title");
    const submitBtn = document.getElementById("user-submit");
    const cancelEditBtn = document.getElementById("cancel-edit");
    const usernameInput = document.getElementById("user-username");
    const passwordInput = document.getElementById("user-password");
    const displayInput = document.getElementById("user-display");
    const rolesInput = document.getElementById("user-roles");
    const activeInput = document.getElementById("user-active");
    const settingsCard = document.getElementById("settings-card");
    const settingsForm = document.getElementById("settings-form");
    const settingsUserId = document.getElementById("settings-user-id");
    const settingsUsername = document.getElementById("settings-username");
    const settingsStatus = document.getElementById("settings-status");
    const settingsMaxDevices = document.getElementById("settings-max-devices");
    const settingsTrialEnds = document.getElementById("settings-trial-ends");
    const cancelSettingsBtn = document.getElementById("cancel-settings");
    const settingsTitle = document.getElementById("settings-title");

    let accessToken = "";
    let usersCache = [];
    let editingUserId = null;

    const setStatus = (message, isError = false) => {
      if (!message) {
        statusBox.classList.add("hidden");
        statusBox.textContent = "";
        return;
      }
      statusBox.textContent = message;
      statusBox.className = isError ? "status error" : "status success";
    };

    const resetForm = () => {
      editingUserId = null;
      userForm.reset();
      usernameInput.readOnly = false;
      usernameInput.required = true;
      passwordInput.required = true;
      rolesInput.value = "";
      activeInput.checked = true;
      submitBtn.textContent = "Tạo user";
      formTitle.textContent = "Tạo tài khoản mới";
      cancelEditBtn.classList.add("hidden");
    };

    const requireLogin = () => {
      accessToken = "";
      appView.classList.add("hidden");
      loginView.classList.remove("hidden");
      setStatus("Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.", true);
    };

    const adminFetch = async (url, options = {}) => {
      const headers = options.headers ? { ...options.headers } : {};
      if (!(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
      }
      if (accessToken) {
        headers["Authorization"] = `Bearer ${accessToken}`;
      }
      const response = await fetch(url, { ...options, headers });
      if (response.status === 401) {
        requireLogin();
        throw new Error("Unauthorized");
      }
      if (!response.ok) {
        let detail = "Có lỗi xảy ra.";
        try {
          const data = await response.json();
          detail = data.detail || JSON.stringify(data);
        } catch (_) {}
        throw new Error(detail);
      }
      if (response.status === 204) {
        return null;
      }
      return response.json();
    };

    const renderUsers = (users) => {
      usersCache = users;
      tableBody.innerHTML = "";
      if (!users.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 6;
        cell.textContent = "Chưa có user nào.";
        row.appendChild(cell);
        tableBody.appendChild(row);
        return;
      }
      users.forEach((user) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${user.id}</td>
          <td>${user.username}</td>
          <td>${user.display_name || ""}</td>
          <td>${user.roles.join(", ")}</td>
          <td>${user.is_active ? "Active" : "Inactive"}</td>
        `;
        const actionsCell = document.createElement("td");
        actionsCell.className = "table-actions";
        const editBtn = document.createElement("button");
        editBtn.textContent = "Sửa";
        editBtn.className = "btn-secondary";
        editBtn.addEventListener("click", () => startEdit(user.id));
        const settingsBtn = document.createElement("button");
        settingsBtn.textContent = "Settings";
        settingsBtn.className = "btn-secondary";
        settingsBtn.style.background = "#10b981";
        settingsBtn.style.color = "#fff";
        settingsBtn.addEventListener("click", () => openSettings(user.id, user.username));
        const deleteBtn = document.createElement("button");
        deleteBtn.textContent = "Xóa";
        deleteBtn.className = "btn-danger";
        deleteBtn.addEventListener("click", () => {
          if (confirm(`Xóa user "${user.username}"?`)) {
            deleteUser(user.id);
          }
        });
        actionsCell.appendChild(editBtn);
        actionsCell.appendChild(settingsBtn);
        actionsCell.appendChild(deleteBtn);
        row.appendChild(actionsCell);
        tableBody.appendChild(row);
      });
    };

    const loadUsers = async () => {
      try {
        const data = await adminFetch("/admin/users");
        renderUsers(data);
      } catch (error) {
        setStatus(error.message, true);
      }
    };

    const startEdit = (userId) => {
      const user = usersCache.find((u) => u.id === userId);
      if (!user) return;
      editingUserId = user.id;
      usernameInput.value = user.username;
      usernameInput.readOnly = true;
      passwordInput.value = "";
      passwordInput.required = false;
      displayInput.value = user.display_name || "";
      rolesInput.value = user.roles.join(", ");
      activeInput.checked = Boolean(user.is_active);
      submitBtn.textContent = "Cập nhật user";
      formTitle.textContent = `Chỉnh sửa "${user.username}"`;
      cancelEditBtn.classList.remove("hidden");
    };

    const deleteUser = async (userId) => {
      try {
        await adminFetch(`/admin/users/${userId}`, { method: "DELETE" });
        setStatus("Đã xóa user.", false);
        await loadUsers();
      } catch (error) {
        setStatus(error.message, true);
      }
    };

    const openSettings = async (userId, username) => {
      try {
        settingsUserId.value = userId;
        settingsUsername.value = username;
        settingsTitle.textContent = `Settings: ${username}`;
        
        // Load current settings
        const settings = await adminFetch(`/admin/users/${userId}/settings`);
        settingsStatus.value = settings.status || "active";
        settingsMaxDevices.value = settings.max_devices === null ? "" : settings.max_devices;
        
        if (settings.trial_ends_at) {
          const date = new Date(settings.trial_ends_at);
          const localDateTime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
            .toISOString()
            .slice(0, 16);
          settingsTrialEnds.value = localDateTime;
        } else {
          settingsTrialEnds.value = "";
        }
        
        settingsCard.classList.remove("hidden");
        settingsCard.scrollIntoView({ behavior: "smooth" });
      } catch (error) {
        setStatus(error.message, true);
      }
    };

    const closeSettings = () => {
      settingsCard.classList.add("hidden");
      settingsForm.reset();
    };

    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      setStatus("");
      try {
        const payload = {
          username: loginForm.username.value.trim(),
          password: loginForm.password.value,
        };
        const response = await fetch("/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.detail || "Đăng nhập thất bại.");
        }
        const data = await response.json();
        if (!data.roles.includes("admin")) {
          throw new Error("Tài khoản không có quyền admin.");
        }
        accessToken = data.access_token;
        loginView.classList.add("hidden");
        appView.classList.remove("hidden");
        setStatus("Đăng nhập thành công.", false);
        await loadUsers();
        resetForm();
      } catch (error) {
        setStatus(error.message, true);
      }
    });

    userForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!accessToken) {
        return requireLogin();
      }
      const roleList = rolesInput.value
        .split(",")
        .map((role) => role.trim())
        .filter(Boolean);
      const payload = {
        display_name: displayInput.value || null,
        roles: roleList,
        is_active: activeInput.checked,
      };
      try {
        if (!editingUserId) {
          if (!usernameInput.value.trim()) {
            return setStatus("Username không được để trống.", true);
          }
          if (!passwordInput.value) {
            return setStatus("Password không được để trống.", true);
          }
          payload.username = usernameInput.value.trim();
          payload.password = passwordInput.value;
          if (!payload.roles.length) {
            payload.roles = ["viewer"];
          }
          await adminFetch("/admin/users", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          setStatus("Đã tạo user mới.", false);
        } else {
          if (passwordInput.value) {
            payload.password = passwordInput.value;
          }
          if (!payload.roles.length) {
            delete payload.roles;
          }
          await adminFetch(`/admin/users/${editingUserId}`, {
            method: "PUT",
            body: JSON.stringify(payload),
          });
          setStatus("Đã cập nhật user.", false);
        }
        await loadUsers();
        resetForm();
      } catch (error) {
        setStatus(error.message, true);
      }
    });

    cancelEditBtn.addEventListener("click", () => {
      resetForm();
    });

    logoutBtn.addEventListener("click", () => {
      requireLogin();
      setStatus("Bạn đã đăng xuất.", false);
    });

    cancelSettingsBtn.addEventListener("click", () => {
      closeSettings();
    });

    settingsForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!accessToken) {
        return requireLogin();
      }
      const userId = settingsUserId.value;
      if (!userId) return;

      const payload = {
        status: settingsStatus.value,
        max_devices: settingsMaxDevices.value ? parseInt(settingsMaxDevices.value) : null,
      };

      if (settingsTrialEnds.value) {
        payload.trial_ends_at = new Date(settingsTrialEnds.value).toISOString();
      } else {
        payload.trial_ends_at = null;
      }

      try {
        await adminFetch(`/admin/users/${userId}/settings`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        setStatus("Đã cập nhật account settings.", false);
        closeSettings();
      } catch (error) {
        setStatus(error.message, true);
      }
    });
  </script>
</body>
</html>
"""


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", response_model=schemas.LoginResponse, tags=["auth"])
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)) -> schemas.LoginResponse:
    user = crud.get_user_by_username(db, payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai username hoặc password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị vô hiệu hóa.")
    roles = [role.name for role in user.roles]
    _ensure_account_entitlement(db, user, roles)
    return _build_session_response(user, roles, db)


@app.post("/auth/refresh", response_model=schemas.LoginResponse, tags=["auth"])
def refresh(payload: schemas.RefreshRequest, db: Session = Depends(get_db)) -> schemas.LoginResponse:
    if not payload.refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token không hợp lệ.")
    record = crud.get_refresh_token(db, payload.refresh_token)
    if not record or record.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token không hợp lệ hoặc đã bị thu hồi.")
    if record.expires_at < datetime.utcnow():
        crud.revoke_refresh_token(db, record)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token đã hết hạn.")
    user = record.user
    if not user.is_active:
        crud.revoke_refresh_token(db, record)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị vô hiệu hóa.")
    crud.revoke_refresh_token(db, record)
    roles = [role.name for role in user.roles]
    _ensure_account_entitlement(db, user, roles)
    return _build_session_response(user, roles, db)


@app.post("/auth/logout", tags=["auth"])
def logout(payload: schemas.LogoutRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    """Logout by revoking the refresh token."""
    if not payload.refresh_token:
        return {"status": "ok", "message": "No token provided"}
    
    record = crud.get_refresh_token(db, payload.refresh_token)
    if record and not record.revoked:
        crud.revoke_refresh_token(db, record)
        return {"status": "ok", "message": "Đã đăng xuất thành công"}
    
    return {"status": "ok", "message": "Token đã được thu hồi trước đó"}


@admin_router.get("", response_class=HTMLResponse)
def admin_console() -> HTMLResponse:
    return HTMLResponse(content=ADMIN_APP_HTML)


@admin_router.get("/users", response_model=list[schemas.AdminUserOut])
def admin_list_users(
    _: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[schemas.AdminUserOut]:
    users = crud.list_users(db)
    return [schemas.AdminUserOut.model_validate(user) for user in users]


@admin_router.post("/users", response_model=schemas.AdminUserOut, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: schemas.AdminUserCreate,
    _: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> schemas.AdminUserOut:
    if crud.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username đã tồn tại.")
    password_hash = hash_password(payload.password)
    user = crud.create_user(
        db,
        username=payload.username,
        password_hash=password_hash,
        display_name=payload.display_name,
        is_active=payload.is_active,
        role_names=payload.roles,
    )
    return schemas.AdminUserOut.model_validate(user)


@admin_router.put("/users/{user_id}", response_model=schemas.AdminUserOut)
def admin_update_user(
    user_id: int,
    payload: schemas.AdminUserUpdate,
    current_admin: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> schemas.AdminUserOut:
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy user.")
    if user.id == current_admin.user.id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tự vô hiệu hóa tài khoản đang đăng nhập.",
        )
    password_hash = hash_password(payload.password) if payload.password else None
    user = crud.update_user(
        db,
        user,
        display_name=payload.display_name,
        is_active=payload.is_active,
        password_hash=password_hash,
        role_names=payload.roles,
    )
    return schemas.AdminUserOut.model_validate(user)


@admin_router.delete("/users/{user_id}")
def admin_delete_user(
    user_id: int,
    current_admin: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy user.")
    if user.id == current_admin.user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa tài khoản đang đăng nhập.",
        )
    crud.delete_user(db, user)
    return {"status": "deleted"}


@admin_router.get("/users/{user_id}/settings", response_model=schemas.AccountSettingOut)
def admin_get_account_settings(
    user_id: int,
    _: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> schemas.AccountSettingOut:
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại.")
    setting = crud.get_account_setting(db, user)
    if not setting:
        # Create default settings if not exists
        roles = [role.name for role in user.roles]
        _ensure_account_entitlement(db, user, roles)
        setting = crud.get_account_setting(db, user)
        if not setting:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể tạo account setting.")
    return setting


@admin_router.put("/users/{user_id}/settings", response_model=schemas.AccountSettingOut)
def admin_update_account_settings(
    user_id: int,
    payload: schemas.AccountSettingUpdate,
    _: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> schemas.AccountSettingOut:
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại.")
    setting = crud.get_account_setting(db, user)
    if not setting:
        # Create default settings if not exists
        setting = crud.create_account_setting(
            db,
            user,
            status=payload.status or "active",
            trial_ends_at=payload.trial_ends_at,
            max_devices=payload.max_devices,
        )
    else:
        setting = crud.update_account_setting(
            db,
            setting,
            status=payload.status,
            trial_ends_at=payload.trial_ends_at,
            max_devices=payload.max_devices,
        )
    return setting


app.include_router(admin_router)


def _build_session_response(user: models.User, roles: list[str], db: Session) -> schemas.LoginResponse:
    # Check max_devices policy
    setting = crud.get_account_setting(db, user)
    if setting and setting.max_devices == 1:
        # Single device mode: check if already logged in
        active_count = crud.count_active_refresh_tokens(db, user)
        if active_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tài khoản này đang được sử dụng trên thiết bị khác. Vui lòng đăng xuất thiết bị đó trước."
            )
    # TODO: Add logic for max_devices > 1 (count active tokens and revoke oldest if exceeded)
    
    access_token = create_access_token(subject=user.username, roles=roles)
    refresh_value = generate_refresh_token()
    expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    refresh_record = crud.create_refresh_token(db, user, refresh_value, expires_at)
    user_out = schemas.UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        roles=roles,
    )
    return schemas.LoginResponse(
        access_token=access_token,
        refresh_token=refresh_record.token,
        roles=roles,
        user=user_out,
    )


def _ensure_account_entitlement(db: Session, user: models.User, roles: list[str]) -> None:
    setting = crud.get_account_setting(db, user)
    if setting is None:
        if trial_days := _trial_duration_for_roles(roles):
            trial_end = datetime.utcnow() + timedelta(days=trial_days)
            setting = crud.create_account_setting(db, user, status="trial", trial_ends_at=trial_end)
        else:
            setting = crud.create_account_setting(db, user, status="active", trial_ends_at=None)

    if setting.status == "locked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa.")
    if setting.status == "expired":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã hết hạn.")
    if setting.status == "trial":
        if setting.trial_ends_at and setting.trial_ends_at < datetime.utcnow():
            crud.update_account_setting(db, setting, status="expired")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản đã hết thời gian dùng thử.",
            )


def _trial_duration_for_roles(roles: list[str]) -> Optional[int]:
    durations = [TRIAL_POLICY[role] for role in roles if role in TRIAL_POLICY]
    if not durations:
        return None
    return min(durations)

