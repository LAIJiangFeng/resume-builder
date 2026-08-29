<!-- author: jf -->
# Python 认证对齐与 PDF 分页修复归档

## 产物

- PRD：`docs/requirements/2026-08-29-python-auth-feature-parity.md`
- UI 设计：不适用，本次沿用现有界面和参考项目的已验收分页实现。
- 工作分支：`feat/python-auth-and-pdf-pagination`

## 最终范围

1. Python 后端补齐邮箱验证码注册、密码重置、加密登录、访问令牌和角色权限契约。
2. 新增认证应用服务、SMTP 邮件适配器、安全适配器和 SQLAlchemy 认证仓储。
3. 补齐本地、Docker 与启动脚本配置，并修复 `.venv` 不存在时未创建的问题。
4. 对齐简历预览分页线与 PDF 固定 A4 分页，增加渲染回退和画布原点校准。
5. 将 `PreviewPanel.vue` 的 scoped 样式原样拆分到 `PreviewPanel.css`，满足前端文件行数限制。
6. 更新 Python 后端说明、仓库 Spec 与认证功能 PRD。

## Quality Gate

- `通过`：前端 `npm run lint`、`npm run build`、依赖解析与生产构建。
- `通过`：本次变更 Python 文件的 Ruff 检查、`compileall`、OpenAPI 认证路由、运行时健康检查和登录公钥 HTTP 冒烟。
- `通过`：Docker Compose Python 与迁移 Profile 配置解析。
- `通过`：作者标记、文件行数、敏感信息、私有 `.env` / `.venv` 和 `git diff --check` 检查。
- `未执行`：真实验证码邮件发送和会修改现有账号密码的重置验证，保留页面人工验收。
- `未执行`：浏览器 PDF 导出人工测试，遵循用户明确要求；静态检查、类型检查与生产构建已通过。
- 残余风险：全量 Ruff 仍会命中未改动的 `python-ai-backend/app/main.py` 既有 E402；前端构建保留现有主 chunk 超过 500 kB 的非阻断警告。

## Break Loop

- Python 无法使用当前登录注册流程：根因是认证接口、加密协议、验证码和令牌契约未与 Spring 对齐；通过共享契约、分层认证实现与双后端兼容验证闭环。
- PDF 分页线与导出分页不一致：根因是预览坐标与导出副本坐标没有统一映射；通过导出副本元素映射和固定 A4 切片闭环。
- Python 启动脚本缺少依赖：根因是批处理嵌套条件在 `.venv` 不存在时跳过创建；改为显式重建状态判断并完成临时端口健康检查。

## Review 与远程状态

- Review：用户选择跳过。
- 实现提交：`a153e76`（`feat: 完善 Python 认证并修复 PDF 分页`）。
- 推送：已推送至 `origin/feat/python-auth-and-pdf-pagination`。
- PR：[#29](https://github.com/LAIJiangFeng/resume-builder/pull/29)，目标分支为 `main`，当前已创建、未合并。
- 本归档随 PR 的后续提交推送。

## Spec 回写

- `.workflow/specs/backend.md`
- `.workflow/specs/python-ai-backend.md`
- `.workflow/specs/learnings.md`
