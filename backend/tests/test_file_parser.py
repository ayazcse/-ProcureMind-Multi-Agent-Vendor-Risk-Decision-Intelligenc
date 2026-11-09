from app.services.file_parser import parse_file, parse_txt, parse_csv


def test_parse_txt_basic():
    result = parse_txt(b"Hello vendor proposal text")
    assert "Hello vendor proposal text" in result.full_text
    assert result.warnings == []


def test_parse_txt_empty():
    result = parse_txt(b"")
    assert result.full_text == ""


def test_parse_csv_basic():
    result = parse_csv(b"name,price\nAcme,1000\nGlobex,900")
    assert "Acme" in result.full_text
    assert "900" in result.full_text


def test_parse_file_unsupported_extension():
    result = parse_file("file.exe", b"binary junk")
    assert result.full_text == ""
    assert any("Unsupported" in w for w in result.warnings)


def test_parse_file_routes_by_extension():
    result = parse_file("notes.txt", b"some notes")
    assert "some notes" in result.full_text
