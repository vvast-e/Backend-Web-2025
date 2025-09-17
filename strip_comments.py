import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent

PY_LINE = re.compile(r"^[\t ]*#.*$")
PY_INLINE = re.compile(r"(?P<code>[^'#]*)(?P<comment>#.*)$")

HTML_COMMENT = re.compile(r"<!--([\s\S]*?)-->")
CSS_COMMENT = re.compile(r"/\*([\s\S]*?)\*/")

def strip_py(text: str) -> str:
    out_lines = []
    for line in text.splitlines():
        if PY_LINE.match(line):
            out_lines.append("")
            continue
        m = PY_INLINE.match(line)
        if m:
            out_lines.append(m.group('code').rstrip())
        else:
            out_lines.append(line)
    return "\n".join(out_lines)

def strip_html(text: str) -> str:
    return HTML_COMMENT.sub("", text)

def strip_css(text: str) -> str:
    return CSS_COMMENT.sub("", text)

def main():
    patterns = ["*.py", "*.html", "*.css"]
    for pat in patterns:
        for path in ROOT.rglob(pat):
            if path.name == Path(__file__).name:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue
            if pat.endswith(".py"):
                new = strip_py(content)
            elif pat.endswith(".html"):
                new = strip_html(content)
            else:
                new = strip_css(content)
            if new != content:
                path.write_text(new, encoding="utf-8")
                print(f"Stripped comments: {path}")

if __name__ == "__main__":
    sys.exit(main())
