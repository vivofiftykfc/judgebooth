# 补丁交互方案

## 一、三种协作模式

### 模式 A：我在现场（最常用，最方便）

你直接在 Claude 里说需求 → **我直接改代码** → 你重启测试。

改完后我自动更新 `CHANGELOG.md`，必要时打包 rar。

### 模式 B：你收到 rar 包

```
收到 JudgeBooth.rar
  1. 解压覆盖到 D:\hks\
  2. 重启后端: uvicorn main:app --host 0.0.0.0 --port 8000
  3. 重启前端: npm run dev
```

### 模式 C：队友间传补丁（他们只会 Claude Code）

```
队友 A 改完代码
  → Claude Code 生成 .patch 文件到 patches/ 目录
  → 把 patches/ 文件夹发给队友 B
  
队友 B 收到后
  → 解压到 D:\hks\patches\
  → 打开 Claude Code 说："帮我应用 patches/ 下的补丁"
  → Claude Code 自动读取并修改代码
```

## 二、补丁管理

```bash
# 查看有哪些补丁
bash patch.sh status

# 应用所有补丁
bash patch.sh apply

# 回滚最后一个
bash patch.sh rollback
```

## 三、协约规则

1. 每次改代码 → 更新 `CHANGELOG.md`
2. 需要分享时 → 生成 `.patch` 文件到 `patches/`
3. 补丁命名格式：`001-功能描述.patch`
4. 你当场验收通过 → 不需要额外打补丁
