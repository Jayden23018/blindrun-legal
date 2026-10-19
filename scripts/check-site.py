#!/usr/bin/env python3
"""官网发布门禁：发现问题直接退出码 1，不只是警告。

用法：
    python3 scripts/check-site.py            # 发布前：任何问题都失败
    python3 scripts/check-site.py --preview  # 本地预览：占位符只列出不失败，其余照常失败
    python3 scripts/check-site.py --root DIR # 检查别的目录（给 scripts/test-check-site.py 用）

为什么要有它：
    苹果审核组织账号时会看官网，「示例文字」「内容太少」都会被拒；
    官网的读者里有视障者，图片漏写替代文字、标题层级乱跳，读屏软件就读不明白。
    这两类问题肉眼都很难发现，所以交给脚本。

检查项（与 SPEC §8 一一对应）：
    1. 残留 {{ 占位符；正文或 alt / aria-label / title / meta content 里出现
       「草稿」「初稿」「示例文字」、TODO、lorem、example.com（英文不分大小写）
    2. 站内链接（href / src）指向的文件或锚点不存在。文件名大小写按 GitHub Pages（Linux）算
    3. <img> 缺 alt；alt="" 的装饰图没写 aria-hidden="true"；
       <svg> 既没标 aria-hidden="true"，也没有 role="img" + aria-label
    4. 每页 h1 不是恰好一个；标题层级往下跳级（h2 直接到 h4）
"""
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER = re.compile(r"\{\{[^{}\n]{0,40}(?:\}\})?")   # 只要出现 {{ 就算：成对的报整段，没闭合的也报
DRAFT_WORDS = ("草稿", "初稿", "示例文字", "todo", "lorem", "example.com")
TEXT_ATTRS = ("alt", "aria-label", "title", "content", "placeholder")
EXTERNAL = ("http://", "https://", "mailto:", "tel:", "data:", "//")

# 已知例外：页面 → (允许的 h1 个数, 理由)。只放过这个确切的个数，变多变少都会报。
# 法律页由后端 docs/legal/build-html.py 生成，pandoc 标题块和正文各出一个 h1，
# 修法在后端仓库（Jayden23018/blind-run-backend#809），修好后这里会报「例外已过期」。
H1_EXCEPTIONS = {
    "privacy-policy.html": (2, "blind-run-backend#809"),
    "user-agreement.html": (2, "blind-run-backend#809"),
}


class PageScan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.links = []      # (属性名, 值, 行号)
        self.images = []     # (属性字典, 行号)
        self.svgs = []
        self.headings = []   # (级别, 行号)
        self.text = []
        self._skip = 0       # 处在 <script>/<style> 里时不收正文

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        if "id" in a:
            self.ids.add(a["id"])
        for key in TEXT_ATTRS:
            if a.get(key):
                self.text.append((a[key], line))
        for key in ("href", "src"):
            if a.get(key):
                self.links.append((key, a[key], line))
        if tag == "img":
            self.images.append((a, line))
        if tag == "svg":
            self.svgs.append((a, line))
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append((int(tag[1]), line))
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.text.append((data, self.getpos()[0]))


def scan(path):
    p = PageScan()
    p.feed(path.read_text(encoding="utf-8"))
    return p


def exists_exact_case(path, root):
    """macOS 默认不区分大小写，Pages 区分。逐级比对目录列表里的真实文件名。"""
    try:
        parts = path.relative_to(root.resolve()).parts
    except ValueError:
        return False
    cur = root.resolve()
    for part in parts:
        if not cur.is_dir() or part not in os.listdir(cur):
            return False
        cur = cur / part
    return True


def check_page(path, pages, preview, root):
    errors, warnings = [], []
    rel = path.relative_to(root)
    raw = path.read_text(encoding="utf-8")
    p = pages[path]

    # 1. 占位符与草稿字样（扫原文，属性值里的也要抓）
    for i, line in enumerate(raw.split("\n"), 1):
        for m in PLACEHOLDER.findall(line):
            (warnings if preview else errors).append(f"{rel}:{i}: 残留占位符 {m}")
    for data, line in p.text:
        for w in DRAFT_WORDS:
            if w in data.lower():
                errors.append(f"{rel}:{line}: 正文或属性里出现「{w}」")

    # 2. 站内链接
    for key, value, line in p.links:
        if value.startswith(EXTERNAL):
            continue
        target, _, anchor = value.partition("#")
        target = target.split("?", 1)[0]
        if not target:
            dest = path
        elif target.startswith("/"):
            dest = (root / target.lstrip("/")).resolve()
        else:
            dest = (path.parent / target).resolve()
        if dest.is_dir():
            dest = dest / "index.html"
        if target and not exists_exact_case(dest, root):
            errors.append(f"{rel}:{line}: {key}=\"{value}\" 指向的文件不存在（大小写也要一致）")
            continue
        if anchor and dest.suffix == ".html":
            dest_ids = pages[dest].ids if dest in pages else scan(dest).ids
            if anchor not in dest_ids:
                errors.append(f"{rel}:{line}: 锚点 #{anchor} 在 {dest.name} 里不存在")

    # 3. 替代文字
    for a, line in p.images:
        if a.get("alt") is None or (a["alt"] != "" and not a["alt"].strip()):
            errors.append(f"{rel}:{line}: <img src=\"{a.get('src', '')}\"> 缺 alt")
        elif a["alt"] == "" and a.get("aria-hidden") != "true":
            errors.append(f"{rel}:{line}: 装饰图 alt=\"\" 但没写 aria-hidden=\"true\"")
    for a, line in p.svgs:
        decorative = a.get("aria-hidden") == "true"
        labelled = a.get("role") == "img" and a.get("aria-label")
        if not (decorative or labelled):
            errors.append(f"{rel}:{line}: <svg> 要么 aria-hidden=\"true\"，要么 role=\"img\" + aria-label")

    # 4. 标题层级
    h1 = [ln for lv, ln in p.headings if lv == 1]
    allowed, reason = H1_EXCEPTIONS.get(path.name, (1, None))
    if reason and len(h1) == 1:
        errors.append(f"{rel}: h1 已恢复为 1 个，删掉 H1_EXCEPTIONS 里这一条（{reason}）")
    elif len(h1) != allowed:
        errors.append(f"{rel}: h1 应恰好 {allowed} 个，实际 {len(h1)} 个")
    prev = 0
    for level, line in p.headings:
        if prev and level > prev + 1:
            errors.append(f"{rel}:{line}: 标题从 h{prev} 跳到 h{level}")
        prev = level
    return errors, warnings


def main():
    args = sys.argv[1:]
    preview = "--preview" in args
    root = Path(args[args.index("--root") + 1]).resolve() if "--root" in args else ROOT
    files = sorted(root.glob("*.html"))
    pages = {f.resolve(): scan(f) for f in files}
    errors, warnings = [], []
    for f in files:
        e, w = check_page(f.resolve(), pages, preview, root)
        errors += e
        warnings += w
    for w in warnings:
        print(f"⚠️  {w}")
    for e in errors:
        print(f"❌ {e}")
    print(f"检查了 {len(files)} 个页面：{len(errors)} 个错误，{len(warnings)} 个预览期占位符。")
    if warnings:
        print("占位符要在发布前全部替换；不带 --preview 运行时它们算错误。")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
