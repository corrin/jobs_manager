-- This script drops and recreates the jobs_manager database
-- It preserves the character set and collation settings
-- Note: User accounts are preserved as they are stored in the MySQL system database

-- Show current databases before drop
SELECT 'Databases before drop:' as status;
SHOW DATABASES LIKE 'jobs_manager';

-- Drop the database
SELECT 'Dropping database...' as status;
DROP DATABASE IF EXISTS jobs_manager;

-- Confirm database was dropped
SELECT 'Databases after drop:' as status;
SHOW DATABASES LIKE 'jobs_manager';

-- Recreate the database with the same character set and collation
SELECT 'Creating database...' as status;
CREATE DATABASE jobs_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Confirm database was created
SELECT 'Databases after creation:' as status;
SHOW DATABASES LIKE 'jobs_manager';

-- Create the django_user (drop first if exists)
SELECT 'Creating database user...' as status;
DROP USER IF EXISTS 'django_user'@'localhost';
DROP USER IF EXISTS 'django_user'@'%';
CREATE USER 'django_user'@'localhost' IDENTIFIED BY 'FAKE_DB_PASSWORD';
CREATE USER 'django_user'@'%' IDENTIFIED BY 'FAKE_DB_PASSWORD';

-- Grant privileges to django_user@localhost
SELECT 'Granting privileges...' as status;
GRANT ALL PRIVILEGES ON jobs_manager.* TO 'django_user'@'localhost';
GRANT ALL PRIVILEGES ON test_jobs_manager.* TO 'django_user'@'localhost';

-- Grant privileges to django_user@'%'
GRANT ALL PRIVILEGES ON jobs_manager.* TO 'django_user'@'%';

-- Flush privileges to ensure changes take effect
FLUSH PRIVILEGES;
SELECT 'Reset complete!' as status;