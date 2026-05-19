from pathlib import Path

from push2HAL import elementHAL as elt


def test_from_type_returns_specialized_class():
    document = elt.HALelt.from_type("article", {"title": {"en": "Example title"}})

    assert isinstance(document, elt.Article)
    assert document.dataXML is not None


def test_from_input_uses_declared_type():
    document = elt.HALelt.from_input({"type": "book", "title": {"en": "Example book"}})

    assert isinstance(document, elt.Book)


def test_load_data_updates_existing_xml_tree():
    tei_file = Path(__file__).parent / "emse-01525674v3.tei.xml"
    document = elt.HALelt.from_type("article")
    document.loadXML(str(tei_file))

    document.loadData(
        {
            "remove": ["title"],
            "title": {"en": "Updated title"},
        }
    )

    assert document.dataXML is not None


def test_from_xml_content_infers_existing_type():
    tei_file = Path(__file__).parent / "emse-01525674v3.tei.xml"

    document = elt.HALelt.fromXML(str(tei_file))

    assert isinstance(document, elt.Article)


def test_prepare_resolves_pdf_from_data(tmp_path, monkeypatch):
    pdf_path = tmp_path / "article.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr("push2HAL.misc.checkXML", lambda *args, **kwargs: True)
    document = elt.HALelt.from_type(
        "article",
        {
            "title": {"en": "Prepared title"},
            "file": pdf_path.name,
        },
    )

    sendfile, payload = document.prepare(dirPath=str(tmp_path))

    assert Path(sendfile).exists()
    assert payload["Content-Type"] == "application/zip"