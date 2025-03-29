-- This script drops and recreates the msm_workflow database
-- It preserves the character set and collation settings
-- Note: User accounts are preserved as they are stored in the MySQL system database

-- Drop the database
DROP DATABASE IF EXISTS msm_workflow;

-- Recreate the database with the same character set and collation
CREATE DATABASE msm_workflow DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_uca1400_ai_ci;

-- Note: If you need to create the django_user, use the following commands
-- (replace 'your_password' with the actual password from your .env file):
--
-- CREATE USER 'django_user'@'localhost' IDENTIFIED BY 'your_password';
-- CREATE USER 'django_user'@'%' IDENTIFIED BY 'your_password';

-- Grant privileges to django_user@localhost
GRANT ALL PRIVILEGES ON msm_workflow.* TO 'django_user'@'localhost';
GRANT ALL PRIVILEGES ON test_msm_workflow.* TO 'django_user'@'localhost';

-- Grant privileges to django_user@'%'
GRANT ALL PRIVILEGES ON msm_workflow.* TO 'django_user'@'%';

-- Flush privileges to ensure changes take effect
FLUSH PRIVILEGES;