import sys, types; sys.path.insert(0, "src")
import ingest

def test_patterns():
    assert ingest.TOP.match("Article 83") and not ingest.TOP.match("Article 263 TFEU.")
    assert ingest.DOT.match("7.2 Liability cap") and not ingest.DOT.match("the cap is 2.0M")

def test_chunking_labels_and_pages(monkeypatch):
    pages = [(1, "(147) Recital text here", False),
             (2, "Article 83\nGeneral conditions\n4. Infringements shall be subject to fines\nup to 10 000 000 EUR", False),
             (3, "5. Other infringements up to 20 000 000 EUR", False)]
    monkeypatch.setattr(ingest, "read_pages", lambda p: pages)
    chunks, s = ingest.chunk_doc("x.pdf", "x.pdf")
    labels = {(c.clause, c.page) for c in chunks}
    assert ("Recital 147", 1) in labels and ("Article 83 (4)", 2) in labels and ("Article 83 (5)", 3) in labels

def test_number_on_own_line(monkeypatch):
    pages = [(82, "Article 83\n5.\nInfringements up to 20 000 000 EUR\n7.\nWithout prejudice", False)]
    monkeypatch.setattr(ingest, "read_pages", lambda p: pages)
    chunks, _ = ingest.chunk_doc("x.pdf", "x.pdf")
    assert [c.clause for c in chunks] == ["Article 83", "Article 83 (5)", "Article 83 (7)"]


def test_bottom_of_page_text_is_kept(tmp_path):
    import fitz   # regression: Art. 8(1) 2nd subparagraph ended at 94.5% of page height and was dropped as a footer
    d = fitz.open(); p = d.new_page()
    p.insert_textbox(fitz.Rect(60, 400, 500, 430), "Body paragraph in the middle of the page.", fontsize=10)
    p.insert_textbox(fitz.Rect(60, 783, 500, 812), "Member States may provide by law for a lower age.", fontsize=10)
    d.save(tmp_path / "t.pdf")
    text = ingest.read_pages(str(tmp_path / "t.pdf"))[0][1]
    assert "lower age" in text and "Body paragraph" in text
