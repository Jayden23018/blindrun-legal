#!/usr/bin/env python3
"""check-site.py 的自测：每个检查分支一条用例，在临时目录里造页面，断言报出（或不报）对应的错。

用法：python3 scripts/test-check-site.py
改 check-site.py 前后都跑一遍。门禁的漏报不会自己暴露 —— 它只会安静地放行。

CHECK_SITE 环境变量可以指向另一份 check-site.py（验证这些用例在实现被改坏时会不会红）。
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKER = Path(os.environ.get("CHECK_SITE", HERE / "check-site.py"))

HEAD = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>t</title></head><body>'
TAIL = "</body></html>"
CLEAN = HEAD + '<h1 id="top">标题</h1><h2>小节</h2><a href="support.html#faq">支持</a><a href="#top">回顶部</a>' \
    '<a href="support.html?from=home">带参数</a><a href="/">根目录</a>' \
    '<img src="support.html" alt="一张图"><img src="support.html" alt="" aria-hidden="true">' \
    '<svg aria-hidden="true"></svg><svg role="img" aria-label="图"></svg>' + TAIL
SUPPORT = HEAD + '<h1 id="faq">支持</h1>' + TAIL


def run(pages, *flags):
    with tempfile.TemporaryDirectory() as d:
        for name, html in {"index.html": CLEAN, "support.html": SUPPORT, **pages}.items():
            Path(d, name).write_text(html, encoding="utf-8")
        p = subprocess.run([sys.executable, str(CHECKER), "--root", d, *flags], capture_output=True, text=True)
        return p.returncode, p.stdout


CASES = [
    # (说明, 要写入的页面, 额外参数, 期望退出码, 输出里必须出现的片段；None 表示输出里不能有 ❌)
    ("干净的页面不误报（带参数链接、根目录链接、装饰图、两种 svg 都合法）", {}, (), 0, None),
    ("成对的占位符：发布模式算错误", {"a.html": HEAD + "<h1>t</h1><p>{{公司全称}}</p>" + TAIL}, (), 1, "❌ a.html:1: 残留占位符 {{公司全称}}"),
    ("成对的占位符：预览模式只警告", {"a.html": HEAD + "<h1>t</h1><p>{{公司全称}}</p>" + TAIL}, ("--preview",), 0, "⚠️  a.html:1: 残留占位符"),
    ("没闭合的占位符也要报", {"a.html": HEAD + "<h1>t</h1><p>{{公司全称}</p>" + TAIL}, (), 1, "残留占位符 {{公司全称"),
    ("正文里的「草稿」", {"a.html": HEAD + "<h1>t</h1><p>这是草稿</p>" + TAIL}, (), 1, "出现「草稿」"),
    ("alt 里的「示例文字」", {"a.html": HEAD + '<h1>t</h1><img src="support.html" alt="示例文字">' + TAIL}, (), 1, "出现「示例文字」"),
    ("小写 todo 也要报", {"a.html": HEAD + "<h1>t</h1><p>Todo: 补电话</p>" + TAIL}, (), 1, "出现「todo」"),
    ("meta content 里的 example.com", {"a.html": HEAD + '<meta name="x" content="mail@example.com"><h1>t</h1>' + TAIL}, (), 1, "出现「example.com」"),
    ("链接到不存在的文件", {"a.html": HEAD + '<h1>t</h1><a href="missing.html">x</a>' + TAIL}, (), 1, "指向的文件不存在"),
    ("文件名大小写不一致（Pages 上会 404）", {"a.html": HEAD + '<h1>t</h1><a href="Support.html">x</a>' + TAIL}, (), 1, "\"Support.html\" 指向的文件不存在"),
    ("本页锚点不存在", {"a.html": HEAD + '<h1>t</h1><a href="#nope">x</a>' + TAIL}, (), 1, "锚点 #nope 在 a.html 里不存在"),
    ("别页锚点不存在", {"a.html": HEAD + '<h1>t</h1><a href="support.html#nope">x</a>' + TAIL}, (), 1, "锚点 #nope 在 support.html 里不存在"),
    ("img 没有 alt", {"a.html": HEAD + '<h1>t</h1><img src="support.html">' + TAIL}, (), 1, "缺 alt"),
    ("img 只写了 alt 不带值", {"a.html": HEAD + '<h1>t</h1><img src="support.html" alt>' + TAIL}, (), 1, "缺 alt"),
    ("alt 只有空格", {"a.html": HEAD + '<h1>t</h1><img src="support.html" alt=" ">' + TAIL}, (), 1, "缺 alt"),
    ("装饰图没写 aria-hidden", {"a.html": HEAD + '<h1>t</h1><img src="support.html" alt="">' + TAIL}, (), 1, "没写 aria-hidden"),
    ("svg 既不隐藏也没名字", {"a.html": HEAD + "<h1>t</h1><svg></svg>" + TAIL}, (), 1, "<svg> 要么"),
    ("没有 h1", {"a.html": HEAD + "<h2>t</h2>" + TAIL}, (), 1, "h1 应恰好 1 个，实际 0 个"),
    ("两个 h1", {"a.html": HEAD + "<h1>t</h1><h1>u</h1>" + TAIL}, (), 1, "h1 应恰好 1 个，实际 2 个"),
    ("标题跳级", {"a.html": HEAD + "<h1>t</h1><h3>u</h3>" + TAIL}, (), 1, "标题从 h1 跳到 h3"),
    ("法律页例外：恰好两个 h1 放行", {"privacy-policy.html": HEAD + "<h1>t</h1><h1>t</h1>" + TAIL}, (), 0, None),
    ("法律页例外：变成三个 h1 照样报", {"privacy-policy.html": HEAD + "<h1>t</h1><h1>t</h1><h1>t</h1>" + TAIL}, (), 1, "h1 应恰好 2 个，实际 3 个"),
    ("法律页例外：修好后提示删掉例外", {"privacy-policy.html": HEAD + "<h1>t</h1>" + TAIL}, (), 1, "删掉 H1_EXCEPTIONS"),
]


def main():
    failed = 0
    for desc, pages, flags, want_rc, want in CASES:
        rc, out = run(pages, *flags)
        ok = rc == want_rc and (("❌" not in out) if want is None else (want in out))
        print(("✅" if ok else "❌"), desc)
        if not ok:
            failed += 1
            print(f"   期望退出码 {want_rc}、输出含 {want!r}；实际退出码 {rc}，输出：\n" + "\n".join("   | " + l for l in out.splitlines()))
    print(f"{len(CASES) - failed}/{len(CASES)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
