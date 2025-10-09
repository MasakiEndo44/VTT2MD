import pytest
import sys
import os
from pathlib import Path

# Add the src directory to the Python path for sibling-module imports
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from vtt2md.converter import VttConverter, get_nlp

# --- Fixtures for test data ---

@pytest.fixture(scope="session")
def ensure_nlp_model():
    """Ensure the spaCy model is loaded once for the test session."""
    # This fixture will trigger the model download/load before tests run.
    # It will only run once per session, improving test speed.
    try:
        get_nlp()
    except Exception as e:
        pytest.fail(f"Failed to load spaCy model, please run 'python -m spacy download ja_ginza'. Error: {e}")

@pytest.fixture
def simple_vtt():
    return """WEBVTT

1
00:00:01.000 --> 00:00:03.000
<v Speaker 1>Hello, this is a test.

2
00:00:04.000 --> 00:00:06.000
<v Speaker 2>This is another speaker.

3
00:00:06.500 --> 00:00:08.000
<v Speaker 2>And a second line from them.
"""

@pytest.fixture
def merged_vtt():
    return """WEBVTT

1
00:00:10.000 --> 00:00:12.000
<v Speaker 1>This is the first part.

2
00:00:12.800 --> 00:00:14.000
<v Speaker 1>This is the second part, merged.

3
00:01:20.000 --> 00:01:22.000
<v Speaker 1>This is a third part, but too far away to merge.
"""

@pytest.fixture
def vtt_with_fillers():
    return """WEBVTT

1
00:00:01.000 --> 00:00:03.000
<v Speaker 1>えーと、これはテストです。

2
00:00:04.000 --> 00:00:06.000
<v Speaker 2>はい。

3
00:00:07.000 --> 00:00:09.000
<v Speaker 1>あの、テスト、テストです。

4
00:00:10.000 --> 00:00:12.000
<v Speaker 2>はい、承知しました。

5
00:00:13.000 --> 00:00:15.000
<v Speaker 1>いや、そうじゃなくて、本番です。
"""

# (Other fixtures remain the same...)
@pytest.fixture
def empty_vtt():
    return "WEBVTT"

@pytest.fixture
def no_speaker_vtt():
    return """WEBVTT

1
00:00:01.000 --> 00:00:03.000
Just some text without a speaker.
"""

@pytest.fixture
def teams_uuid_vtt():
    return """WEBVTT
e4b71968-46d8-4199-a56a-f5d6f4584268/1-1

1
00:00:05.000 --> 00:00:07.000
<v User 1>Hello from Teams.
"""

# --- Test Cases ---

def test_simple_conversion(simple_vtt, tmp_path):
    """Tests basic conversion of a VTT with multiple speakers."""
    file_path = tmp_path / "test.vtt"
    file_path.write_text(simple_vtt, encoding="utf-8")
    
    converter = VttConverter(simple_vtt, str(file_path))
    md = converter.to_markdown()

    assert "**Speaker 1**" in md
    assert "Hello, this is a test." in md
    assert "**Speaker 2**" in md
    assert "This is another speaker. And a second line from them." in md

# (Other existing tests remain the same...)

# --- New Tests for Filler Removal ---

def test_filler_removal_disabled(vtt_with_fillers, tmp_path):
    """Tests that fillers are NOT removed when the feature is disabled."""
    file_path = tmp_path / "test.vtt"
    file_path.write_text(vtt_with_fillers, encoding="utf-8")
    
    converter = VttConverter(vtt_with_fillers, str(file_path))
    md = converter.to_markdown(remove_fillers=False) # Explicitly disabled

    assert "えーと、これはテストです。" in md
    assert "はい。" in md
    assert "あの、テスト、テストです。" in md
    assert "はい、承知しました。" in md
    assert "いや、そうじゃなくて、本番です。" in md

def test_filler_removal_enabled(vtt_with_fillers, tmp_path, ensure_nlp_model):
    """Tests that fillers ARE removed correctly when the feature is enabled."""
    file_path = tmp_path / "test.vtt"
    file_path.write_text(vtt_with_fillers, encoding="utf-8")
    
    converter = VttConverter(vtt_with_fillers, str(file_path))
    md = converter.to_markdown(remove_fillers=True) # Enabled

    # --- Assertions ---
    # Level 1 & 4
    assert "えーと" not in md
    assert "あの" not in md
    assert "いや、そうじゃなくて" not in md
    assert "本番です。" in md

    # Level 2
    assert "**Speaker 2** [00:00:04]" not in md # The line with only "はい。" should be completely removed
    assert "はい、承知しました。" in md # This one should be kept

    # Level 3
    assert "テスト、テストです" not in md
    assert "テストです" in md