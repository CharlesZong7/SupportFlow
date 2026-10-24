# SupportFlow：GitHub 开源发布步骤

编写日期：2026-10-24。适用目录：`D:\multi agent`。本文件是操作教程；本轮没有替你初始化 Git、创建远程仓库、提交、选择许可证或推送代码。

## 1. 先认识几个名字

| 名称 | 通俗理解 |
| --- | --- |
| Git | 本机的版本记录工具 |
| GitHub | 存放远程仓库、展示项目和协作的网站 |
| Repository / 仓库 | 项目文件加版本历史 |
| Commit / 提交 | 在本机保存一次可以回看的改动记录 |
| Push / 推送 | 把本机提交上传到 GitHub |
| main | 本项目约定的主分支 |
| origin | 本机给远程仓库起的名称 |

第一次的完整顺序：**网页创建空仓库 → 本机初始化 → 检查待发布文件 → 本机提交 → 推送 → 补齐许可证。** 后续通常只需 add、commit、push。

## 2. 当前已经具备什么？

- 本机 Git 为 `2.49.0.windows.1`，已配置作者信息和凭据管理器；未发现 GitHub CLI `gh`，本教程不需要安装它。
- 当前项目尚未初始化 Git，没有远程地址或提交记录。
- GitHub 连接核对到的账号为 `CharlesZong7`；网页和本机认证也应使用你希望持有此项目的账号。
- README、依赖文件、测试、运行说明和模拟数据已经存在，当前里程碑为 M0。
- `.gitignore` 已忽略 `.venv/`、`.env`、Python 缓存及 `*.log`，不应上传整个 Python 环境。
- 本轮初步文本检查未发现常见 API 密钥、GitHub token 或私钥格式，也未发现 `.env`、`.pem` 等敏感文件名。模式检查不能保证覆盖所有敏感内容，提交前仍需检查实际暂存内容。
- 当前没有 `LICENSE`。公开代码和明确授予开源许可是两件事，许可证在第 7 步说明。

## 3. 在 GitHub 网页创建空仓库

登录 GitHub，打开 <https://github.com/new>，填写：

| 页面字段 | 建议填写 |
| --- | --- |
| Owner | `CharlesZong7`，或你希望使用的实际账号 |
| Repository name | `SupportFlow`；是否可用以创建页提示为准 |
| Description | `面向企业软件的技术支持与工单协作项目，逐步实现四角色 Agent、证据复核与可靠执行。当前为 M0 模拟业务基线。` |
| Visibility | 希望直接公开展示时选 `Public`；需要先自行检查时可先用 `Private`，之后再修改可见性 |
| Add README | 不添加，本地已有 README |
| Add .gitignore | 不添加，本地已有忽略规则 |
| Choose a license | 本次空仓库流程先不添加，第 7 步单独处理 |

点击 **Create repository**。网页显示 Quick setup 即可，不用把网页列出的全部命令都执行一遍。

选择空仓库是为了让远程没有另一个初始提交，便于直接推送现有项目。这与 [GitHub 官方导入说明](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)一致。

以下命令中的地址按 `CharlesZong7/SupportFlow` 编写。如果页面的账号或仓库名不同，使用页面 **Code / HTTPS** 或 Quick setup 提供的真实地址。

## 4. 在 PowerShell 初始化本地仓库

在 PowerShell 逐行运行：

```powershell
Set-Location 'D:\multi agent'
git init -b main
git status
```

`git init` 只建立本机版本库，不会上传代码。若已经执行过，先用 `git status` 和 `git remote -v` 看现状，不反复重新初始化。

首次提交前确认作者信息：

```powershell
git config user.name
git config user.email
```

这些输出只在你本机查看。提交中的作者邮箱会随历史公开；可在 [GitHub 邮箱设置](https://github.com/settings/emails)启用邮箱隐私并复制系统提供的 noreply 邮箱。若要仅为本项目覆盖作者信息，先替换下面的 `YOUR_GITHUB_NOREPLY_EMAIL`，再运行：

```powershell
git config --local user.name 'CharlesZong7'
git config --local user.email 'YOUR_GITHUB_NOREPLY_EMAIL'
```

这是提交作者署名设置，不是登录 GitHub 的命令。若已有信息符合你的公开署名意愿，可保持原配置。

## 5. 检查文件，建立第一次本地提交

把确定要公开的项目文件放入暂存区：

```powershell
git add .gitignore README.md requirements.txt support_app tests scripts docs tutorial.md practice.md
git status --short
git diff --cached --stat
git diff --cached --check
git diff --cached
```

最后一条查看实际将被提交的内容；若进入分页界面，按 `q` 退出。确认 `.venv`、真实密钥、私人信息和不希望公开的笔记没有进入暂存区。`docs` 包含学习记录，是否公开应在此一起检查。

`dev-alice` / `dev-bob` 是代码里明确标记的公开本地演示身份，不是生产凭据。保留其演示说明。

检查完成后运行：

```powershell
git commit -m 'chore: initialize SupportFlow M0 baseline'
git log -1 --oneline
```

这一步只保存本地历史，还没有上传。可以先运行 README 中的测试命令再提交；本轮没有重新执行测试，已有记录是 M0 的 22 项自动化测试和 7 个本地 HTTP 案例。

## 6. 连接远程仓库并上传

确认第 3 步的空仓库已创建，再运行：

```powershell
git remote add origin https://github.com/CharlesZong7/SupportFlow.git
git remote -v
git push -u origin main
```

确认 `remote -v` 显示的是你刚创建的仓库，再执行 push。首次推送时，Git Credential Manager 可能打开浏览器要求登录和授权，使用仓库所属账号完成即可；它也可能复用已缓存的登录。网页登录状态与本机 Git 凭据并非同一份状态。

不要在 URL 中加入 token，也不要把 token 发到聊天或提交到仓库。HTTPS 可以使用 GCM 管理认证，通常不需要手动把凭据写进命令。[GitHub 认证说明](https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-git)

推送成功后，刷新你创建的仓库页面，应该能看到 README、`support_app`、`tests`、`docs` 等文件。本机检查：

```powershell
git status
git branch -vv
```

通常会看到工作区干净，且 main 跟踪 origin/main。以命令结果和 GitHub 页面为准，不能仅凭本机 commit 成功就判断已经上传。

## 7. 明确选择许可证

GitHub 官方说明，真正的开源发布需要明确许可他人使用、修改和分发。[许可证说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)

如果希望采用简单的宽松许可证，可以了解 [MIT License](https://choosealicense.com/licenses/mit/)：允许使用、修改和分发，包括商业用途，要求保留版权及许可证声明。是否采用由你决定；本轮没有替你创建 LICENSE。

确定选择后，可以在首次推送完成的仓库网页中操作：

1. 点击 **Add file → Create new file**，文件名填写 `LICENSE`。
2. 从你选定许可证的官方页面复制完整正文。若选择 MIT，使用上面的 MIT 页面，填写实际年份和希望公开的权利人署名，不把占位符原样留下。
3. 检查内容，提交到 main。此时 GitHub 会新增一个提交。
4. 回到本机，在工作区干净的情况下同步：

```powershell
git pull --ff-only
```

选择许可证后，同步 README 和项目记录中的许可状态。后续若复制或修改上游代码，需要保留相应声明并按实际许可证处理；“参考过 Yuxi”不意味着其全部实现都变成了我们的成果。

## 8. 把仓库整理成容易理解的作品

仓库右侧 **About** 可以填写简介和 Topics，例如 `python`、`fastapi`、`technical-support`、`workflow`。当前未实现的能力应在 README 路线中说明，功能清单保留当前实际状态。

README 应能回答：做什么、谁使用、如何运行、现在做到哪里、怎么验证、资料来自哪里。当前文档已经明确模拟数据、AI 辅助开发及 M0 边界，后续按真实进度更新即可。

不必等 M4 完成再公开：开发中的仓库也可以持续记录每一轮变化。CI、贡献指南和发布版本可以随后按实际需求逐项补齐。

## 9. 后续每天怎么更新？

先看改动，再明确选择文件提交：

```powershell
git status
git diff
```

例如，只修改 README 和开发计划时：

```powershell
git add README.md 'docs/项目定位与开发计划.md'
git diff --cached --check
git diff --cached --stat
git commit -m 'docs: clarify SupportFlow development plan'
git push
```

新增功能时，把实际修改的源码和对应验证一起提交，并用能解释改动的提交说明。一个本地提交代表一个能说明的改动，不为制造贡献数量拆空提交。

## 10. 常见提示怎么处理？

| 提示 | 先做什么 |
| --- | --- |
| `Author identity unknown` | 配置第 4 步的本仓库 user.name 和 user.email |
| `remote origin already exists` | 先 `git remote -v` 检查。如果确认原地址错误，才用 `git remote set-url origin 正确地址` |
| `Repository not found` / 403 | 核对仓库是否创建、地址与登录账号是否正确；不代表代码丢失 |
| `src refspec main does not match any` | 检查 `git branch --show-current` 和 `git log -1`，确认已创建本地提交且分支名为 main |
| `non-fast-forward` | 远程有本机没有的提交；先检查双方历史。常见原因是创建仓库时额外生成了文件，先停下来核对，不直接强制覆盖 |
| `nothing to commit` | 当前没有待提交改动；如果仍未上传，查看远程与执行 push 的结果 |
| 换行符 LF/CRLF 提示 | 核对是否只是行尾转换提示；与上传是否成功分别判断 |

首次发布的目标是：你自己的账号下有可访问的 SupportFlow 仓库，代码和 README 已上传，许可证明确，进度描述准确。本文不把“步骤已写好”记成“仓库已发布”。
