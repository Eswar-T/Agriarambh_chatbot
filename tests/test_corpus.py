from app.corpus import load_chunks


def test_user_docs_are_indexed_without_secrets():
    chunks = load_chunks()
    assert chunks
    blob = "\n".join(chunk.text.lower() for chunk in chunks)
    assert "password" not in blob
    assert "greenplot-" not in blob
    assert "phonetopassword" not in blob
    assert any("sign" in chunk.text.lower() or "onboard" in chunk.section.lower() or "user flow" in chunk.section.lower() for chunk in chunks)
    assert all(not chunk.source.startswith("0") for chunk in chunks)
