#!/usr/bin/env python
"""
Script to check if the correct environment is activated.
Run this script to verify your environment setup.
"""

import sys
import os
import platform
import django
import concurrent_log_handler
import MySQLdb

def check_environment():
    """Check if the environment is properly set up."""
    print("\n=== Jobs Manager Environment Check ===\n")
    
    # Check Python version
    python_version = sys.version.split()[0]
    print(f"Python version: {python_version}")
    if not python_version.startswith("3.12"):
        print("⚠️  WARNING: Python 3.12+ is required")
    else:
        print("✅ Python version OK")
    
    # Check virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"✅ Virtual environment active: {sys.prefix}")
    else:
        print("⚠️  WARNING: No virtual environment detected")
    
    # Check Django version
    print(f"Django version: {django.get_version()}")
    if django.VERSION[0] >= 5 and django.VERSION[1] >= 2:
        print("✅ Django version OK")
    else:
        print("⚠️  WARNING: Django 5.2+ is required")
    
    # Check critical packages
    print("\nCritical packages:")
    print(f"✅ concurrent-log-handler: {concurrent_log_handler.__version__}")
    print(f"✅ mysqlclient: {MySQLdb.__version__}")
    
    # Check environment variables
    print("\nEnvironment variables:")
    env_vars = ['DEBUG', 'DJANGO_ENV', 'MYSQL_DATABASE', 'MSM_DB_USER']
    for var in env_vars:
        if var in os.environ:
            print(f"✅ {var}: {os.environ[var]}")
        else:
            print(f"⚠️  {var} not set")
    
    print("\n=== Environment Check Complete ===\n")

if __name__ == "__main__":
    check_environment()