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

## 发布流程（门禁不过就不上线）

Pages 的发布方式是 **GitHub Actions**（Settings → Pages → Build and deployment → Source），
由 `.github/workflows/check-site.yml` 发布，不是「从 main 分支直接发布」：

1. 每次推送和 PR 都跑 `scripts/test-check-site.py`（门禁自测）和 `scripts/check-site.py`（发布门禁）。
2. 只有 `main` 上的推送，并且两步都通过，才会打包 `*.html` 和 `assets/` 并部署。门禁红了，线上保持上一版。
3. 自有域名在 Settings → Pages → Custom domain 里填。用 Actions 发布时 GitHub 不读 `CNAME` 文件，不用加。

门禁查什么：残留 `{{占位符}}`、草稿字样、坏链接（大小写也算）、图片缺替代文字、标题层级。
改 `check-site.py` 本身前后都跑一遍 `python3 scripts/test-check-site.py`。
