# Development Session Startup

Steps to start a development session. For first-time setup, see [initial_install.md](initial_install.md).

This document uses my real development URLs (msm-workflow.ngrok-free.app and msm-workflow-front.ngrok-free.app). Replace with your own domains from initial setup.

## Quick Start Checklist

Each development session requires starting these services:

1. **Backend ngrok tunnel** (terminal 1)
2. **Frontend ngrok tunnel** (terminal 2)
3. **Django server** (VS Code debugger or terminal 3)
4. **Frontend dev server** (terminal 4, in frontend repo)
5. **Connect to Xero** (in browser, if token expired)
6. **Background scheduler** (terminal 5) - keeps Xero token alive

## Detailed Steps

### 1. Start Backend Ngrok Tunnel

```bash
ngrok http 8000 --domain=msm-workflow.ngrok-free.app
```

### 2. Start Frontend Ngrok Tunnel

```bash
ngrok http 5173 --domain=msm-workflow-front.ngrok-free.app
```

### 3. Start Django Server

VS Code: Run menu > Start Debugging (F5)

### 4. Start Frontend Dev Server

In the frontend repository:

```bash
npm run dev
```

### 5. Connect to Xero

Visit https://msm-workflow-front.ngrok-free.app/xero and click "Login with Xero" if token has expired.

### 6. Start Background Scheduler

```bash
python manage.py run_scheduler
```

## Verifying Everything is Running

- **Backend**: Visit https://msm-workflow.ngrok-free.app - should show the Django app
- **Frontend**: Visit https://msm-workflow-front.ngrok-free.app - should show the Vue app
- **ngrok tunnels**: Both ngrok terminals should show active connections

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ngrok domain already in use | Check for other ngrok processes: `pkill ngrok` |
| Port 8000 already in use | Find process: `lsof -i :8000` and kill it |
| Port 5173 already in use | Find process: `lsof -i :5173` and kill it |
| Database connection errors | Ensure MariaDB is running: `sudo systemctl start mariadb` |
| Virtual environment not active | Run `poetry shell` in the project directory |
