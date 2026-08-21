# 云服务器免域名测试部署

## 前提

- Ubuntu 24.04 云服务器
- Docker、Docker Compose、Git 和 OpenSSL 已安装
- 项目位于 `~/nine`
- 服务器防火墙无需开放 3000、8000 或 5432

Cloudflare Quick Tunnel 只用于测试。它提供随机 HTTPS 地址，但没有可用性保证，隧道容器重建后地址可能改变。

## 初始化秘密配置

在项目根目录执行：

```bash
chmod +x scripts/init-prod-env.sh
./scripts/init-prod-env.sh
```

共享密码和 API Key 只在服务器终端输入，不发送给他人，不截图。脚本会生成数据库密码，以权限 `600` 写入被 Git 忽略的 `deploy/.env.production`。

## 构建并启动

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml ps
```

## 获取访问地址

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml logs tunnel | grep -o 'https://[^ ]*trycloudflare.com' | tail -n 1
```

把输出的 HTTPS 地址和共享用户名、密码分别发送给测试者。

## 检查状态

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml ps
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml logs --tail 100 api worker web gateway tunnel
```

## 更新应用

```bash
git pull --ff-only
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml up -d --build
```

更新后再次读取 tunnel 日志；如果地址变化，重新通知测试者。

## 停止应用

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml down
```

不要添加 `-v`，否则会删除 PostgreSQL 数据卷。
