
import pytest
import sys
import os
from pathlib import Path

# Add the src directory to the Python path for sibling-module imports
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from vtt2md.converter import VttConverter

# --- Fixtures for test data ---

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
    # Check if the merged text for Speaker 2 is correct
    assert "This is another speaker. And a second line from them." in md
    assert "**参加者:**" in md
    assert "- Speaker 1" in md
    assert "- Speaker 2" in md

def test_merged_captions(merged_vtt, tmp_path):
    """Tests if captions from the same speaker are correctly merged within the time threshold."""
    file_path = tmp_path / "test.vtt"
    file_path.write_text(merged_vtt, encoding="utf-8")

    converter = VttConverter(merged_vtt, str(file_path))
    md = converter.to_markdown()

    # The first two parts should be merged
    assert "This is the first part. This is the second part, merged." in md
    # The third part should be separate
    assert "This is a third part, but too far away to merge." in md
    # Ensure there are two separate entries for Speaker 1
    assert md.count("**Speaker 1**") == 2

def test_empty_vtt(empty_vtt, tmp_path):
    """Tests handling of an empty VTT file."""
    file_path = tmp_path / "test.vtt"
    file_path.write_text(empty_vtt, encoding="utf-8")

    converter = VttConverter(empty_vtt, str(file_path))
    md = converter.to_markdown()
    
    assert "Could not find any captions" in md

def test_no_speaker_vtt(no_speaker_vtt, tmp_path):
    """Tests a VTT file with no speaker tags."""
    file_path = tmp_path / "test.vtt"
    file_path.write_text(no_speaker_vtt, encoding="utf-8")

    converter = VttConverter(no_speaker_vtt, str(file_path))
    md = converter.to_markdown()

    assert "## 発言記録" in md
    # The text without a speaker should not be included in the main transcript
    assert "Just some text without a speaker." not in md
    assert "**参加者:**" in md
    # No participants should be listed
    assert "- " not in md

def test_teams_uuid_stripping(teams_uuid_vtt, tmp_path):
    """Tests if the parser correctly handles and strips MS Teams UUID lines."""
    file_path = tmp_path / "test.vtt"
    file_path.write_text(teams_uuid_vtt, encoding="utf-8")

    # This should not raise an error
    converter = VttConverter(teams_uuid_vtt, str(file_path))
    md = converter.to_markdown()

    assert "**User 1**" in md
    assert "Hello from Teams." in md
    assert "e4b71968-46d8-4199-a56a-f5d6f4584268/1-1" not in md

def test_metadata_generation(simple_vtt, tmp_path):
    """Tests the generation of metadata like title, participants, and date."""
    file_path = tmp_path / "test.vtt"
    file_path.write_text(simple_vtt, encoding="utf-8")

    converter = VttConverter(simple_vtt, str(file_path))
    md = converter.to_markdown()

    assert "# test" in md # Title from filename
    assert "**参加者:**" in md
    assert "- Speaker 1" in md
    assert "- Speaker 2" in md
    assert "所要時間:" in md
    assert "日時:" in md # Check for date
