from app.history import valid_session
from app.rag import _accept_translation


def test_session_id_must_be_a_uuid():
    assert valid_session("123e4567-e89b-12d3-a456-426614174000")
    assert not valid_session("session-1")


def test_translation_must_match_the_target_script():
    assert _accept_translation("Open the app", "ಅಪ್ಲಿಕೇಶನ್ ತೆರೆಯಿರಿ", "kn") == "ಅಪ್ಲಿಕೇಶನ್ ತೆರೆಯಿರಿ"
    assert _accept_translation("Open the app", "Open the app", "kn") == ""
    assert _accept_translation("Tap Settings", "ಸೆಟ್ಟಿಂಗ್ ತappable", "kn") == ""
    assert _accept_translation("ಖಾತೆ ತೆರೆಯಿರಿ", "Create an account", "en") == "Create an account"
    assert _accept_translation("ಖಾತೆ ತೆರೆಯಿರಿ", "ಖಾತೆ ತೆರೆಯಿರಿ", "en") == ""
