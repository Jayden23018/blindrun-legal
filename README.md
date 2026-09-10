# 助盲跑 · 法律文本

这里只放**构建产物**（两个单文件 HTML），通过 GitHub Pages 对外提供：

- 隐私政策：https://jayden23018.github.io/blindrun-legal/privacy-policy.html
- 用户协议：https://jayden23018.github.io/blindrun-legal/user-agreement.html

## 🚨 不要直接改这里的 HTML

唯一源是后端仓库的 `docs/legal/privacy-policy-draft.md` / `user-agreement-draft.md`。
改那两份 Markdown → 跑 `python3 docs/legal/build-html.py` → 把 `docs/legal/dist/` 的产物复制过来。

法律文本有两个副本就一定会漂移，而**隐私政策与实际不符比没有隐私政策更糟**
（Apple 5.1.1(i) 要求政策内容真实完整）。

## 生产是怎么用它的

后端 `GET /api/misc/legal-links` 返回这两个 URL，客户端据此打开页面。
URL 由生产的 JVM 参数注入：

    -Dapp.legal.privacy-policy-url=https://jayden23018.github.io/blindrun-legal/privacy-policy.html
    -Dapp.legal.user-agreement-url=https://jayden23018.github.io/blindrun-legal/user-agreement.html

备案落地、换成自有域名时，只改这两个参数，不用发新版 App。
