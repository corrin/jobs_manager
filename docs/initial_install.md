# Initial Installation Guide

This guide details the steps required to set up the Jobs Manager application for local development. The setup involves configuring several external services **before** initializing the application itself. **Xero integration is mandatory** for the application's core functionality.

**Core Dependencies:**

*   Python 3.12+
*   [Poetry](https://python-poetry.org/)
*   Node.js + npm
*   MariaDB Server & Client (Version 11.5.2+ recommended)
*   [ngrok](https://ngrok.com/) Client

## Defining Your Application Name

To maintain consistency throughout this guide, choose a name for your application based on your company or project. For example, if your company is "MSM Sheetmetal", a suitable app name might be `msm_workflow`.

This "App Name" will be used to construct:

*   Your MariaDB database name (e.g., `<your-app-name>`)
*   Your MariaDB database username (e.g., `<your-app-name>`)
*   Part of your ngrok subdomain (e.g., `<your-app-name>-dev.ngrok-free.app`). Note that ngrok's free tier may not guarantee your requested name, so you might need to tweak it slightly.
*   Part of your Xero App name (e.g., `<your-app-name> Development`).

**Decide on your App Name now and use it consistently throughout this guide.** We'll refer to it as `<your-app-name>`.

## Phase 1: Prerequisites & External Service Setup

Complete these steps first to gather all necessary credentials and configurations. **Note down the details you create in each step** (passwords, domains, IDs, secrets) as you will need them later.

### Step 1: Install Core Software

Ensure you have installed Python, Poetry, Node.js/npm, the MariaDB server/client, and the ngrok client on your development machine. Follow the official installation instructions for each tool specific to your operating system.

### Step 2: Set Up MariaDB Database

The application requires a dedicated database and user.

1.  Log into your MariaDB server as root (or another privileged user):
    ```bash
    # Example for Linux/macOS using sudo
    sudo mysql -u root -p
    # Windows might involve opening the MariaDB client/shell directly
    ```
2.  Run the following SQL commands. **Choose a strong password** for the database user and **record it securely**:
    ```sql
    -- Replace <your-app-name> with your chosen application name
    CREATE DATABASE <your-app-name>;
    -- Replace <your-app-name> with your chosen application name
    -- Replace 'your-strong-password' with your chosen password
    CREATE USER '<your-app-name>'@'localhost' IDENTIFIED BY 'your-strong-password';
    GRANT ALL PRIVILEGES ON <your-app-name>.* TO '<your-app-name>'@'localhost';
    FLUSH PRIVILEGES;
    EXIT;
    ```
3.  **Install Timezone Data:** After creating the database, install timezone data into MySQL/MariaDB. This is required for Django's timezone-aware database functions to work correctly:
    ```bash
    # Install timezone data from system zoneinfo files
    sudo mysql_tzinfo_to_sql /usr/share/zoneinfo | sudo mysql mysql
    ```
    *   **Details to Record:** Database name (`<your-app-name>`), DB username (`<your-app-name>`), DB password (`your-strong-password`).

### Step 3: Set Up ngrok

`ngrok` creates a secure tunnel to your local machine, providing a public HTTPS URL needed for Xero's callbacks.

1.  **Sign up/Log in:** Create an account at [ngrok.com](https://ngrok.com/).
2.  **Install & Authenticate:** Follow their instructions to install the ngrok client and connect it to your account using your authtoken (`ngrok config add-authtoken <your_token>`).
3.  **Choose Your Static Domain:** You need a predictable hostname.
    *   *Free Plan:* You can use a static domain provided on the free tier (e.g., `<your-app-name>-dev.ngrok-free.app`). Find this option in your ngrok dashboard.
    *   *Paid Plan:* You can configure a custom static domain.
    *   **Decide on your domain name now.** You will need it for the Xero setup in the next step.
    *   **Detail to Record:** Your chosen ngrok static domain (e.g., `<your-app-name>-dev.ngrok-free.app`).
    *   **Note your region:** Also note the ngrok region you intend to use (e.g., `au`, `us`, `eu`).

### Step 4: Set Up Xero Developer Account & App

The application syncs data with Xero. You need to register a Xero application.

1.  **Sign up/Log in:** Go to the Xero Developer Portal: [https://developer.xero.com/](https://developer.xero.com/) and create an account or log in.
2.  **Create a New App:**
    *   Click "New App".
    *   Give it a name (e.g., `<your-app-name> Development`).
    *   Select "Web app" as the integration type.
    *   Company or Practice Name: Enter your details.
    *   **OAuth 2.0 Redirect URI:** This is critical. Enter the URL formed by your ngrok domain from Step 3, followed by `/xero/callback`.
        *   Example: `https://<your-app-name>-dev.ngrok-free.app/xero/callback`
        *   *(Make sure to use HTTPS and replace the example domain with your actual ngrok domain)*.
    *   Agree to the terms and conditions and create the app.
3.  **Get Credentials:** Once the app is created, navigate to its configuration page.
    *   **Details to Record:** Copy the **Client ID** and the **Client Secret**. Keep the Client Secret confidential.

*You should now have recorded: DB credentials, your ngrok domain & region, and your Xero Client ID & Client Secret.*

## Phase 2: Application Installation & Configuration

Now that the external services are prepared, set up the application code.

### Step 5: Clone Repository & Install Dependencies

```bash
git clone https://github.com/corrin/jobs_manager.git
cd jobs_manager
poetry install
npm install
```

### Step 6: Configure Environment (`.env`) File

1.  Copy the example environment file:
    ```bash
    cp .env.example .env # Linux/macOS
    # copy .env.example .env # Windows
    ```
2.  Open the `.env` file in a text editor.
3.  **Populate with Recorded Details:** Fill in the following values using the details you recorded in Phase 1:
    *   `DATABASE_URL`: Construct using your DB user, password, and name (e.g., `mysql://<your-app-name>:your-strong-password@localhost:3306/<your-app-name>`).
    *   `APP_DOMAIN`: Enter your chosen ngrok static domain (e.g., `<your-app-name>-dev.ngrok-free.app`).
    *   `XERO_CLIENT_ID`: Paste your Xero app's Client ID.
    *   `XERO_CLIENT_SECRET`: Paste your Xero app's Client Secret.
    *   Review other settings and adjust if needed (e.g., `DJANGO_SECRET_KEY` should be changed for any non-local testing).

### Step 7: Initialize Application & Database Schema

1.  Activate the Python virtual environment:
    ```bash
    poetry shell
    ```
2.  Apply database migrations:
    ```bash
    python manage.py migrate
    ```
3.  Load essential configuration and initial data fixtures:
    ```bash
    # Load essential company configuration
    python manage.py loaddata apps/workflow/fixtures/company_defaults.json

    # EITHER
    # Load demo data for development (optional - skip if restoring production data)
    python manage.py loaddata apps/workflow/fixtures/initial_data.json
    # OR...  restore from prod
    python manage.py backport_data_restore

    ```
    **Default Admin Credentials (from initial_data.json):**
    *   **Username:** `defaultadmin@example.com`
    *   **Password:** `Default-admin-password`

4.  **(Optional) Restore production data:** If you have a production backup to work with:
    ```bash
    python manage.py backport_data_restore restore/prod_backup_YYYYMMDD_HHMMSS.json
    ```
    This loads production data (jobs, timesheets, etc.) while preserving essential configuration. The restore command automatically loads `company_defaults.json` after clearing the database, so you don't need to load it separately.

## Phase 3: Running the Application & Connecting Xero

### Step 8: Start Ngrok Tunnel

1.  Open a **new, separate terminal window**.
2.  Run the `ngrok` command using the domain and region you recorded:
    ```bash
    # Replace <your-region> with your ngrok region (e.g., au, us, eu)
    # Replace <your-ngrok-domain> with the hostname from Step 3 / your .env file
    # Replace <django-port> with the port Django runs on (default: 8000)
    ngrok http --region=<your-region> --domain=<your-ngrok-domain> <django-port>

    # Example:
    # ngrok http --region=au --domain=<your-app-name>-dev.ngrok-free.app 8000
    ```
3.  Keep this ngrok terminal open. It forwards traffic from your public ngrok URL to your local development server.

### Step 9: Start Development Server

1.  Go back to your **original terminal window** (where `poetry shell` is active).
2.  Start the Django development server, binding to `0.0.0.0` to accept connections from ngrok:
    ```bash
    python manage.py runserver 0.0.0.0:8000
    # Or specify a different port if 8000 is in use: python manage.py runserver 0.0.0.0:8001
    # (Ensure the port matches the one used in the ngrok command)
    ```

### Step 10: Connect Application to Xero

1.  **Access Application:** Open your web browser and navigate to your public ngrok URL (e.g., `https://<your-app-name>-dev.ngrok-free.app`).
2.  **Log In:** Use the default admin credentials (`defaultadmin@example.com` / `Default-admin-password`).
3.  **Initiate Xero Connection:** Find the "Connect to Xero" or similar option (likely in Settings/Admin). Click it.
4.  **Authorize in Xero:** You'll be redirected to Xero. Log in if needed. **Crucially, select and authorize the "Demo Company (Global)"**. Do *not* use your live company data for development.

### Important: Create Demo Company Shop Contact

**Before proceeding with the development setup, you must create a specific contact in Xero:**

1. **Log into Xero Demo Company:** After authorization, log into your Xero Demo Company account at [https://go.xero.com/](https://go.xero.com/).
2. **Create Shop Contact:**
   - Navigate to Contacts → Add Contact
   - Name: `Demo Company Shop` (exactly this name - case sensitive)
   - This contact represents internal shop work/maintenance jobs
   - Save the contact
3. **Verify Creation:** Ensure the contact appears in your Xero contacts list as "Demo Company Shop"

This contact is essential for proper shop hours tracking in KPI reports.
5.  **Setup Development Xero Connection:** After authorization and creating the shop contact:
    ```bash
    python manage.py setup_dev_xero
    ```
    This command will:
    * Automatically find the Demo Company tenant ID
    * Update your CompanyDefaults with the correct tenant ID
    * Sync the "Demo Company Shop" client to get its Xero contact ID
    * Skip the full sync (default behavior - use --full-sync if you want to run it)

6.  **Create shop jobs:** Create the special internal jobs for tracking shop work:
Note - only do this if you chose not to restore from production!
    ```bash
    python manage.py create_shop_jobs
    ```

7.  **Run full Xero sync:** Now sync all data from Xero:
    ```bash
    python manage.py start_xero_sync
    ```

    **Alternative Manual Setup:** If you prefer to do this manually:
    * Get available tenant IDs: `python manage.py get_xero_tenant_id`
    * Manually update CompanyDefaults in the admin interface
    * Run sync manually: `python manage.py start_xero_sync`

You now have a fully configured local development environment.

## Production-like Setup

For running in a mode closer to production:

1.  Set the environment variable `DJANGO_ENV=production_like` in your `.env` file.
2.  Ensure **Redis** is installed and running (used for caching/Celery). Configure connection details in `.env`.
3.  Start **Celery** worker(s) for handling background tasks (check project specifics).
4.  **Collect Static Files:** Before deploying, run `python manage.py collectstatic --noinput` to gather static assets into the `STATIC_ROOT` directory.
5.  Run using **Gunicorn** (or another WSGI server):
    ```bash
    gunicorn --bind 0.0.0.0:8000 jobs_manager.wsgi
    ```
    *(In actual production, this would run behind a reverse proxy like Nginx, which would serve the collected static files).*

## Resetting the Database (Wipe and Reload)

To wipe the local database and start fresh:

1.  **Create/Ensure Reset Script:** Have a script `scripts/reset_database.sql` containing:
    ```sql
    -- WARNING: This script DROPS the database!
    DROP DATABASE IF EXISTS <your-app-name>;
    CREATE DATABASE <your-app-name>;
    -- Use the SAME password as in your .env file
    GRANT ALL PRIVILEGES ON <your-app-name>.* TO '<your-app-name>'@'localhost' IDENTIFIED BY 'your-strong-password';
    FLUSH PRIVILEGES;
    ```
    *(Replace `<your-app-name>` with your application name and `your-strong-password` with your actual DB password)*.

2.  **Execute Reset Script:** (You might need MariaDB root password)
    ```bash
    mariadb -u root -p -e "source scripts/reset_database.sql"
    ```

3.  **Re-install Timezone Data:** (Required for timezone-aware database functions)
    ```bash
    sudo mysql_tzinfo_to_sql /usr/share/zoneinfo | sudo mysql mysql
    ```

4.  **Re-initialize Application:** (Activate `poetry shell` if needed)
    ```bash
    python manage.py migrate
    python manage.py loaddata apps/workflow/fixtures/company_defaults.json
    python manage.py loaddata apps/workflow/fixtures/initial_data.json
    # Optional: python manage.py backport_data_restore restore/prod_backup_YYYYMMDD_HHMMSS.json
    ```

5.  **Re-Connect Xero and Setup:** After resetting, you **must** repeat the Xero connection steps:
    * Log into the app and click "Connect to Xero"
    * Authorize the Demo Company
    * Create "Demo Company Shop" contact in Xero (if not already there)
    * Run `python manage.py setup_dev_xero`
    * Run `python manage.py create_shop_jobs` (only if you didn't restore from production)
    * Run `python manage.py start_xero_sync`

## Troubleshooting

If you encounter issues:

1.  **Dependencies:** Rerun `poetry install`, `npm install`. Check for errors.
2.  **.env File:** Verify `DATABASE_URL`, Xero keys, `NGROK_DOMAIN`.
3.  **Database:** Is MariaDB running? Do credentials in `.env` match the `CREATE USER` command?
4.  **Migrations:** Run `python manage.py migrate`. Any errors?
5.  **ngrok:** Is the ngrok terminal running without errors? Does the domain match Xero's redirect URI and `.env`? Is the port correct?
6.  **Xero Config:** Double-check Redirect URI in Xero Dev portal. Check Client ID/Secret.
7.  **Django Debug Page/Logs:** Look for detailed errors when `DEBUG=True`. Check `logs/` directory.
