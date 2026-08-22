# author: jf

ARG FLYWAY_BASE_IMAGE=redgate/flyway:13.3.0-alpine@sha256:4c051c4081eda3a84a24e6adf4150fbda408f012c5e5167be3b0e975dc4016fc
FROM ${FLYWAY_BASE_IMAGE}

# Flyway 官方镜像不包含 MySQL Connector/J，固定版本和校验和以保证构建可复现。
ADD --checksum=sha256:69084713593a4aa8d07c383619b9639276f08bccf8faf1c562178147d389b1e1 \
    https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/26.7.0/mysql-connector-j-26.7.0.jar \
    /flyway/drivers/mysql-connector-j-26.7.0.jar
