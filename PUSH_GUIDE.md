# 推送到 GitHub · 一步步来

## 第 0 步：确认 Git 已安装

```bash
git --version
```

没有的话去 https://git-scm.com/downloads 装。

---

## 第 1 步：在 GitHub 上建空仓库

1. 打开 https://github.com/new
2. **Repository name** 填：`astrbot_plugin_dongsen_voice`
3. 选 **Public**（市场要能访问）
4. **不要**勾选 "Add a README file"、"Add .gitignore"、"Choose a license"
   —— 本地已经有这些文件了，勾了会冲突
5. 点 **Create repository**

建好后页面会显示仓库地址，形如：
```
https://github.com/你的用户名/astrbot_plugin_dongsen_voice.git
```

---

## 第 2 步：改 metadata.yaml 的 repo 字段

打开 `astrbot_plugin_dongsen_voice/metadata.yaml`，找到第 53 行：

```yaml
repo: https://github.com/YOUR_NAME/astrbot_plugin_dongsen_voice
```

把 `YOUR_NAME` 换成你的 GitHub 用户名。例如用户名是 `zhangsan`：

```yaml
repo: https://github.com/zhangsan/astrbot_plugin_dongsen_voice
```

保存后提交这个改动：

```bash
cd astrbot_plugin_dongsen_voice
git add metadata.yaml
git commit -m "chore: 填入仓库地址"
```

---

## 第 3 步：配置远程并推送

```bash
cd astrbot_plugin_dongsen_voice

# 改分支名为 main（GitHub 默认用 main）
git branch -M main

# 加远程（把 你的用户名 换掉）
git remote add origin https://github.com/你的用户名/astrbot_plugin_dongsen_voice.git

# 推送
git push -u origin main
```

### 推送时会要认证

GitHub 从 2021 年起不再接受密码，要用 **Personal Access Token**。

**怎么拿 token：**

1. 打开 https://github.com/settings/tokens
2. 点 **Generate new token** → **Generate new token (classic)**
3. Note 填 `astrbot-plugin`
4. Expiration 选 90 天（或自定义）
5. **勾选 `repo` 权限**（这一项必勾，其他不用）
6. 拉到底点 **Generate token**
7. **立刻复制**那串 `ghp_xxxxx`（页面关掉就看不到了）

推送时：
- Username 填你的 GitHub 用户名
- Password 填**刚才复制的 token**（不是账号密码）

---

## 第 4 步：验证

推送成功后打开：
```
https://github.com/你的用户名/astrbot_plugin_dongsen_voice
```

应该能看到 README 渲染出来的页面。

再确认这几项：
- [ ] 文件列表有 `metadata.yaml`、`main.py`、`dongsen/`
- [ ] `dongsen/data/zh.wav` 存在（约 3MB）
- [ ] 没有 `__pycache__` 目录
- [ ] LICENSE 显示 AGPL-3.0

---

## 第 5 步：提交到插件市场

1. 打开 https://cloud.astrbot.app/publish
2. 注册 / 登录 AstrBot Cloud
3. 填仓库地址：`https://github.com/你的用户名/astrbot_plugin_dongsen_voice`
4. 提交审核

---

## 常见问题

### push 报 `remote: Support for password authentication was removed`

你填的是账号密码，要换成 token。见第 3 步。

### push 报 `error: remote origin already exists`

```bash
git remote set-url origin https://github.com/你的用户名/astrbot_plugin_dongsen_voice.git
```

### push 报 `failed to push some refs` / `non-fast-forward`

远程仓库不是空的（建仓库时勾了 README）。两个办法：

```bash
# 办法一：强制覆盖远程（远程内容不要了）
git push -u origin main --force

# 办法二：先拉下来合并
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### 大文件推不上去（zh.wav 3MB）

3MB 远低于 GitHub 的 100MB 单文件限制，正常不会出问题。
如果真报错，检查是不是用了 HTTP 而不是 HTTPS。

### 中文文件名乱码

`.gitattributes` 里已经设了 `text eol=lf`，一般不会有问题。
如果出现，执行：

```bash
git config core.quotepath false
```

---

## 推完之后

市场审核期间可以自己先装一遍验证：

```bash
cd AstrBot/data/plugins
git clone https://github.com/你的用户名/astrbot_plugin_dongsen_voice.git
```

然后 WebUI 重载插件，试试 `/动森 你好呀`。
