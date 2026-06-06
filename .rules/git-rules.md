---
inclusion: always
author: jf
---

# Git 分支与提交文档规范

## 1. 适用范围

本文档用于约束本仓库的 Git 分支命名、分支创建、提交信息和提交说明 Markdown 文档。

适用于以下场景：

1. 创建新分支。
2. 准备提交代码。
3. 编写提交说明、变更说明、交付说明或提交相关 Markdown 文档。
4. 处理 PR、Review、CI 或发布前的版本控制协作。

## 2. 分支创建规则

1. 新分支名称必须使用英文，不得包含中文。
2. 新分支名称必须以明确的类型前缀开头。
3. 分支类型前缀必须使用小写英文。
4. 分支名称主体必须使用英文单词、数字和连字符，不得使用空格、中文标点或特殊符号。
5. 推荐使用 kebab-case，例如 `resume-preview-page-line`。
6. 禁止使用含义不清的名称，例如 `test`、`temp`、`new`、`update`、`fixbug`。

允许的分支前缀：

1. `feat/`：新增功能。
2. `fix/`：修复缺陷。
3. `hotfix/`：紧急修复。
4. `docs/`：文档变更。
5. `chore/`：工程、依赖、配置或杂项维护。
6. `refactor/`：不改变外部行为的重构。
7. `style/`：样式、格式或纯视觉调整。
8. `perf/`：性能优化。
9. `build/`：构建配置变更。
10. `ci/`：持续集成配置变更。

正确示例：

```text
feat/resume-preview-page-line
fix/pdf-export-pagination-offset
docs/git-branch-rules
chore/update-eslint-config
refactor/resume-template-export-flow
```

错误示例：

```text
feature/简历分页线
fix/分页偏移
feat/新增模板
test
temp
update
fixbug
feat/resume preview
feat/resume_preview
```

## 3. 分支创建前检查

创建新分支前必须确认：

1. 当前是否已经在正确的基准分支上。
2. 当前工作区是否存在未提交改动。
3. 新分支名称是否符合本文档的英文命名规则。
4. 新分支是否以允许的类型前缀开头。

如果工作区已有未提交改动，必须先确认这些改动是否属于当前任务，避免把无关改动带入新分支。

## 4. 提交信息规范

1. Git 提交信息必须使用中文描述实际完成内容。
2. Git 提交信息必须符合 Conventional Commits 格式。
3. 提交类型必须与本次变更性质一致。
4. 提交信息不得包含 AI 生成标识。
5. 提交信息不得使用空泛描述，例如“修改代码”“更新一下”“fix bug”。

推荐格式：

```text
feat: 新增简历预览分页线校准
fix: 修复 PDF 导出分页线偏移
docs: 补充 Git 分支命名规范
chore: 调整前端 lint 配置
```

## 5. 提交说明 Markdown 文档规范

如本次任务需要编写提交说明、变更说明、交付说明或提交相关 Markdown 文档，该文档必须包含以下内容：

1. 本次修改内容。
2. 关联文件。
3. 验证方式与测试结果。
4. 未完成事项或风险说明；如无风险，明确写“无”。

提交说明内容来源要求：

1. 优先从 `docs/requirements/` 中对应本次任务的需求记录提取修改内容、关联文件、验收细节、验证方式和验证结果。
2. 如果 `docs/requirements/` 中已有本次修改的完整记录，提交说明不得重新编造范围、测试结果或验收结论，应以该记录为准并补充当前实际状态。
3. `docs/requirements/` 可能被 `.gitignore` 忽略，准备提交说明时不得只依赖普通 `git status` 判断记录是否存在，必须直接检查对应文件。
4. “测试结果”仅指 `.rules/testing-rules.md` 允许的现有命令、本地手工验证或一次性不落盘命令行检查结果，不得为了补全提交说明新增或修改测试代码。

提交说明 Markdown 文档必须满足：

1. 文件必须标记作者为 `jf`。
2. 内容必须使用中文。
3. 不得包含作者为 `ai` 的标识。
4. 不得编造未执行的验证结果。
5. 不得把未验证事项写成已通过。

正确示例：

```md
<!-- author: jf -->
# 提交说明

## 本次修改内容

- 修复简历预览分页线与 PDF 实际导出分页位置不一致的问题。
- 将预览分页线校准值固定为 `16px`。

## 关联文件

- `src/components/resume/PreviewPanel.vue`
- `.rules/frontend-mandatory-rules.md`

## 验证方式与测试结果

- `npm run lint`：通过。
- Playwright 浏览器验证：在 `1280`、`900`、`1600` 三个视口宽度下，分页线未缩放坐标均稳定。

## 未完成事项或风险说明

- 无。
```

错误示例：

```md
# 修改说明

已优化代码。
```

```md
<!-- author: wrong -->
# 提交说明

测试都通过了。
```

```md
<!-- author: jf -->
# 提交说明

## 本次修改内容

- 修复问题。

## 验证方式与测试结果

- 已测试。
```

## 6. 提交前约束

准备提交前必须：

1. 检查分支名称是否符合本文档规则。
2. 检查提交信息是否符合 Conventional Commits 格式。
3. 检查 `docs/requirements/` 中是否存在本次任务记录，并优先从该记录提取提交内容、关联文件、验收细节和验证结果。
4. 按 `.rules/code-review-rules.md` 询问用户是否需要先执行 `code-review`。
5. 按 `.rules/testing-rules.md` 使用允许的方式完成验证。
6. 如果存在未验证项，必须在交付说明或提交说明文档中明确写出原因。

## 7. 优先级说明

本文档为仓库级强制规则。

涉及 Git 分支、提交信息、提交说明 Markdown 文档时，必须优先遵守本文档；如其他规则中仍存在旧的分支示例或宽松表述，以本文档为准。
