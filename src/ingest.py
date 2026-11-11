"""PDF -> pages -> clause-aware chunks. Flags scanned pages."""
import re, fitz
from dataclasses import dataclass

TOP = re.compile(r"^\s*((?:Article|ARTICLE|Section|SECTION|Clause|Chapter)\s+\d+[A-Za-z]?|§\s*\d+[\w.]*)\s*$")
DOT = re.compile(r"^\s*(\d+(?:\.\d+)+)\.?\s+[A-Z]")   # contract style: 7.2 Liability
PARA = re.compile(r"^\s*(\d+)\.(?:\s+\S.*)?$")               # statute paragraph: 4. Infringements...
REC = re.compile(r"^\s*\((\d+)\)(?:\s+\S.*)?$")              # recital / numbered point: (147) ...
MAX = 1200

@dataclass
class Chunk:
    doc: str; page: int; clause: str; text: str

def read_pages(path):
    """Returns [(page_no, text, is_scanned)] with reading order + header/footer removal."""
    out = []
    with fitz.open(path) as d:
        for i, p in enumerate(d, 1):
            w, h = p.rect.width, p.rect.height
            bl = [b for b in p.get_text("blocks") if b[6] == 0 and h*.06 < b[1] and b[3] < h*.97]
            nl = sum(b[2] < w*.5 for b in bl); nr = sum(b[0] > w*.5 for b in bl)
            col = (lambda b: int(b[0] > w*.5)) if min(nl, nr) >= 3 else (lambda b: 0)  # 2 columns only if both halves are populated
            bl.sort(key=lambda b: (col(b), b[1], b[0]))
            text = "\n".join(b[4].strip() for b in bl)
            out.append((i, text, len(text) < 30 and bool(p.get_images())))
    return out

def chunk_doc(path, name):
    pages = read_pages(path)
    chunks, cur, cl, parent = [], [], None, None

    def flush():  # split oversize clauses at line boundaries; each piece keeps its OWN page
        buf, pg, n = [], None, 0
        for p, l in cur + [(None, None)]:
            if l is None or (buf and n + len(l) > MAX):
                if buf: chunks.append(Chunk(name, pg, cl or f"p.{pg}", "\n".join(buf)))
                buf, pg, n = [], None, 0
            if l is None: break
            if pg is None: pg = p
            buf.append(l); n += len(l) + 1

    for no, text, _ in pages:
        for line in text.split("\n"):
            new = None
            if m := TOP.match(line): parent = new = m.group(1)
            elif m := DOT.match(line): new = m.group(1)
            elif m := PARA.match(line): new = f"{parent} ({m.group(1)})" if parent else m.group(1)
            elif m := REC.match(line): new = f"{parent} ({m.group(1)})" if parent else f"Recital {m.group(1)}"
            elif len(line) <= 70 and sum(ch.isalpha() for ch in line) >= 8 and line.isupper(): new = line.strip()  # ALL-CAPS heading
            if new:
                if cur: flush(); cur = []
                cl = new
            cur.append((no, line))
    if cur: flush()
    structure = {"pages": len(pages), "scanned_pages": [n for n, _, s in pages if s], "chunks": len(chunks)}
    return chunks, structure
