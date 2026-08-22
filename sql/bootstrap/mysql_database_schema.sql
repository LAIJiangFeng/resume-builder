-- author: jf
-- 手工建库：为不使用 Docker 自动建库的 MySQL 实例创建业务数据库。

CREATE DATABASE IF NOT EXISTS `resume-builder`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_0900_ai_ci;
