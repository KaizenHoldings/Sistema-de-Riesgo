USE [master];
GO

-- 1. Crear la base de datos si no existe (el error también indica que "Cannot open database 'kfg_ecosystem'")
IF DB_ID('kfg_ecosystem') IS NULL
BEGIN
    CREATE DATABASE [kfg_ecosystem];
END
GO

-- 2. Crear el Login a nivel de servidor (usando la contraseña de tu archivo .env)
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = N'USERDEV')
BEGIN
    CREATE LOGIN [USERDEV] WITH PASSWORD = 'Developer123', CHECK_POLICY = OFF;
END
GO

-- 3. Cambiar al contexto de la base de datos
USE [kfg_ecosystem];
GO

-- 4. Crear el usuario en la base de datos vinculado al Login
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = N'USERDEV')
BEGIN
    CREATE USER [USERDEV] FOR LOGIN [USERDEV];
END
GO

-- 5. Otorgar permisos (asignando el rol db_owner para permisos totales en desarrollo)
ALTER ROLE [db_owner] ADD MEMBER [USERDEV];
GO
