# Environment Setup Guide

This document provides instructions for setting up and activating the correct environment for the Jobs Manager project.

## Initial Setup

1. Ensure you have Python 3.12+ installed:
   ```bash
   python --version
   ```

2. Create a virtual environment (if not already created):
   ```bash
   python3.12 -m venv venv
   ```

3. Install dependencies:
   ```bash
   source venv/bin/activate
   pip install -e .
   ```

## Daily Development

### Option 1: Using the activation script

The simplest way to activate the environment is to use the provided script:

```bash
source activate_env.sh
```

This will:
- Activate the virtual environment
- Set up any necessary environment variables
- Display helpful commands

### Option 2: Manual activation

If you prefer to activate manually:

```bash
source venv/bin/activate
```

### Option 3: VS Code Integration

If using VS Code:

1. Open the project folder in VS Code
2. VS Code should automatically detect and use the virtual environment
3. When opening a terminal in VS Code, it should automatically activate the environment

## Environment Variables

The project uses a `.env` file for configuration. If you need to modify environment variables:

1. Edit the `.env` file in the project root
2. Restart your development server for changes to take effect

## Common Issues

### Wrong Python Version

If you see errors about Python version compatibility:

```bash
The currently activated Python version 3.10.11 is not supported by the project (^3.12)
```

Make sure you're using the correct virtual environment with Python 3.12+.

### Missing Dependencies

If you encounter missing module errors:

```bash
ModuleNotFoundError: No module named 'concurrent_log_handler'
```

Reinstall dependencies:

```bash
source venv/bin/activate
pip install -e .
```

## Database Setup

The project uses MariaDB. Make sure your database is properly configured in the `.env` file:

```
MYSQL_DATABASE=msm_workflow
MSM_DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
```