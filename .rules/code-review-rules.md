---
inclusion: always
author: jf
---

# Code Review 与修复流程规范

## 适用范围

- 适用于本仓库所有需要准备提交代码的场景
- 触发时机为执行 `git commit` 之前

## 强制执行流程

### 提交前询问

- 在准备执行 `git commit` 前，必须先明确询问用户：是否需要先执行 `code-review`
- 未经用户确认，不得直接假定跳过 `code-review`

### 执行 Code Review

- 如果用户确认需要执行 `code-review`，必须调用仓库内的 `code-review` skill
- 执行 `code-review` 后，必须将审查结论、问题分级和报告路径明确反馈给用户

### Review 后询问是否修复

- `code-review` 完成后，必须再次明确询问用户：是否需要修复本次 `code-review` 发现的问题
- 未经用户确认，不得自动开始修复 `code-review` 问题

### 执行 Code Review Fix

- 如果用户确认需要修复，必须调用仓库内的 `code-review-fix` skill
- 修复范围、修复顺序与后续复审要求以 `code-review-fix` skill 规范为准

## 执行约束

- `code-review` 与 `code-review-fix` 必须作为两个显式步骤执行，不得合并为未经确认的一次性自动流程
- 如果用户明确拒绝执行 `code-review`，可以继续后续提交流程，但必须遵守用户本次决定
- 如果用户明确拒绝修复 `code-review` 问题，不得继续自动调用 `code-review-fix`
- 如果当前上下文涉及提交、代码审查或审查问题修复，必须优先读取本规则文件

## 优先级说明

- 本规则为仓库级强制流程约束
- 与提交、审查、审查修复相关的执行动作，均必须遵守本文件
