<!-- author: jf -->
# AI 面试历史消息与选择框图标修复

## 1. 背景

AI 面试页历史会话恢复后，前面的两条对话卡片只显示角色名但没有正文；同时面试历史选择框最右侧下拉图标存在偏移，视觉观感较差。移动端继续复查时发现，历史会话下拉框展开后会被下方问答卡片遮挡。

## 2. 目标

修复历史会话消息展示空白问题，并将历史选择框右侧图标替换为项目已有第三方图标组件，保证移动端顶部控件对齐稳定，历史会话下拉框展开后不被问答区域遮挡。

## 3. 范围

- 修复 AI 面试历史消息内容归一化和展示逻辑。
- 过滤不可展示的空消息，避免只剩角色名的空白卡片。
- 替换历史选择框右侧下拉图标并调整桌面、移动端样式。
- 修复历史会话下拉框与问答卡片之间的层级遮挡问题。

## 4. 非目标

- 不修改 AI 面试接口契约、会话存储结构、评分逻辑和语音逻辑。
- 不新增依赖，优先复用项目已有 `lucide-vue-next`。
- 不新增或修改测试代码、测试脚本、fixture 或 mock 文件。

## 5. 细化任务清单

- [已完成] 任务 1：确认历史消息和选择框图标的现有实现位置。
- [已完成] 任务 2：补齐历史消息内容兼容提取和空消息过滤。
- [已完成] 任务 3：用第三方 SVG 图标替换选择框字符箭头并修正对齐。
- [已完成] 任务 4：执行允许的验证并记录结果。
- [已完成] 任务 5：调整历史下拉框、顶部区域和问答区域的层级关系，避免移动端下拉框被遮挡。

## 6. 验收细节 list

- [待验证] 历史会话恢复后不会出现只有“AI候选人 / AI面试官 / 你”角色名、正文为空的消息卡片。
- [待验证] 历史消息能兼容 `content`、`message`、`text`、`assistantReply` 等常见字段来源。
- [待验证] 历史选择框右侧图标来自 `lucide-vue-next`，不再使用文本字符箭头。
- [待验证] 移动端历史选择框右侧图标居中、不偏移，并能随展开状态旋转。
- [待验证] 目标文件 lint / 类型验证通过或记录明确原因。
- [待验证] 页面级浏览器验证通过或记录明确原因。
- [待验证] 移动端历史会话下拉框展开后位于问答卡片上方，采样命中下拉框内部元素而不是问答卡片。

## 7. 执行记录

- 2026-06-08：已读取仓库全局、Harness、前端、测试和代码规范规则。
- 2026-06-08：已使用 `UI-Ux-Pro-Max` 检索面试页修复方向，采用专业蓝灰、真实 SVG 图标、稳定 hover/focus 的最小修复策略。
- 2026-06-08：已定位历史消息归一化在 `src/services/interviewService.ts`，页面展示在 `src/components/ai/interview/InterviewSimulationPanel.vue`。
- 2026-06-08：已定位历史选择框在 `src/components/ai/interview/AiInterviewerPanel.vue`，当前右侧图标为文本字符 `⌄`。
- 2026-06-08：已在前端服务归一化层兼容 `content`、`messageContent`、`message`、`text`、`assistantReply`、`reply`、`answer` 等历史消息字段。
- 2026-06-08：已在聊天渲染层过滤展示文本为空的历史消息，避免只显示角色名的空白卡片。
- 2026-06-08：已将历史选择框右侧字符箭头替换为 `lucide-vue-next` 的 `ChevronDown`，并补齐展开旋转、桌面和移动端尺寸样式。
- 2026-06-08：已修复消息卡片在纵向 flex 列表中被压缩的问题，将卡片设为不收缩并取消正文裁切，避免长消息挤压前置消息。
- 2026-06-08：已执行目标文件 `npx eslint ... --cache`，通过。
- 2026-06-08：已执行目标文件 `npx oxlint ...`，通过。
- 2026-06-08：已执行 `npx vue-tsc --noEmit`，通过。
- 2026-06-08：已执行 `git diff --check` 目标文件检查，通过。
- 2026-06-08：Browser 插件 `iab` 实例不可用，Playwright MCP profile 被占用；已使用临时 Chromium headless + CDP 进行页面级兜底验证。
- 2026-06-08：页面兜底验证结果：AI 面试页渲染成功，4 个消息卡片空正文数为 0、裁切数为 0，前两条消息高度分别为 147px 和 61px；历史箭头为 SVG，展开态旋转，历史选项 6 条。
- 2026-06-08：已截图验证 `output/ai-interview-history-ui-verify-top.png`，前两条对话正文可见，历史选择框右侧图标居中。
- 2026-06-08：已为本需求文档补充 `.gitignore` 例外，保证 Harness 文档可进入 Git 状态。
- 2026-06-08：按用户移动端截图复查，发现 `.interview-layout` 宽 586px 但子级 `.workspace/.simulation-panel/.qa-card` 扩到 602px，导致问答区域视觉超出移动端主体。
- 2026-06-08：已为 `.interview-layout`、`.workspace`、`.workspace > :first-child`、`.simulation-panel`、`.qa-card` 补齐 `width: 100%`、`max-width: 100%`、`min-width: 0` 和必要的 `overflow: hidden`，让移动端宽度按父容器收缩。
- 2026-06-08：已将 `.chat-list` 改为隐藏横向溢出，`.chat-item` 保持不压缩但不再允许视觉外溢，长代码块改为在 `pre` 内部横向滚动。
- 2026-06-08：已重新执行目标文件 `npx eslint ... --cache`，通过。
- 2026-06-08：已重新执行目标文件 `npx oxlint ...`，通过。
- 2026-06-08：已重新执行 `npx vue-tsc --noEmit`，通过。
- 2026-06-08：已重新执行 `git diff --check` 目标文件检查，通过。
- 2026-06-08：Browser 插件 `iab` 仍不可用，Playwright MCP profile 仍被占用；继续使用临时 Chromium headless + CDP 进行移动端页面级兜底验证。
- 2026-06-08：移动端兜底验证结果：606px 宽度下 `.interview-layout/.workspace/.qa-card` 均为 586px，右侧溢出为 0；`chat-list` 无横向溢出；代码块仅在 `pre` 内部横向滚动；截图为 `output/ai-interview-mobile-chat-width-fix.png`。
- 2026-06-09：按用户移动端截图复查，历史会话下拉框展开后被下方 `.qa-card` 内部元素覆盖，根因是 `.interview-hero` 未建立高于 `.interview-layout` 的 stacking context。
- 2026-06-09：已使用 `UI-Ux-Pro-Max` 检索浮层层级规则，采用 `10 / 30 / 50` 层级尺度，避免使用任意超大 `z-index`。
- 2026-06-09：已为 `.interview-hero`、`.history-field`、`.history-options` 和 `.interview-layout` 补齐明确层级关系，并保持下拉框横向溢出隐藏。
- 2026-06-09：已执行目标文件 `npx eslint ... --cache`，通过；未运行全量 `npm run lint`，因为当前脚本包含 `--fix` 且工作区存在大量非本次脏改，为避免改动无关文件，本轮采用目标文件级无破坏验证。
- 2026-06-09：已执行目标文件 `npx oxlint ...`，通过。
- 2026-06-09：已执行 `npx vue-tsc --noEmit`，通过。
- 2026-06-09：已执行 `git diff --check` 目标文件检查，通过。
- 2026-06-09：Playwright MCP 仍因本机 profile 占用不可用；已使用临时 Chromium headless + CDP 进行移动端页面级兜底验证。
- 2026-06-09：移动端下拉遮挡兜底验证结果：606px 宽度下 `.history-options` 为 `z-index: 50`，`.interview-hero` 为 `z-index: 30`，`.interview-layout` 为 `z-index: 10`；采样点命中 `.history-options`，不再命中 `.qa-card` 或 `.speech-pill`；截图为 `output/ai-interview-history-dropdown-after.png`。

## 8. 验收结果

- [通过] 历史会话恢复后不会出现只有“AI候选人 / AI面试官 / 你”角色名、正文为空的消息卡片。
- [通过] 历史消息能兼容 `content`、`message`、`text`、`assistantReply` 等常见字段来源。
- [通过] 历史选择框右侧图标来自 `lucide-vue-next`，不再使用文本字符箭头。
- [通过] 移动端历史选择框右侧图标居中、不偏移，并能随展开状态旋转。
- [通过] 目标文件 lint、Oxlint、类型验证和 diff 检查通过。
- [通过] 页面级浏览器验证已通过；因 Browser / Playwright MCP 当前不可用，使用临时 Chromium headless + CDP 兜底完成。
- [通过] 移动端问答区域宽度不超过 `.interview-layout`，聊天卡片不再超出屏幕。
- [通过] 长代码块不会撑宽页面，只在代码块内部横向滚动。
- [通过] 移动端历史会话下拉框展开后位于问答卡片上方，采样命中下拉框内部元素而不是问答卡片。
