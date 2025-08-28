import webvtt
from datetime import datetime, timedelta
from pathlib import Path
import io
import re
import os

class VttConverter:
    def __init__(self, vtt_content: str, file_path: str):
        self.vtt_content = vtt_content
        self.file_path = Path(file_path)
        self.captions = self._parse_vtt()

    def _parse_vtt(self):
        # Clean up potential UUID lines from MS Teams that can break the parser
        cleaned_content = re.sub(r'^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}/\d+-\d+\s*$', '', self.vtt_content, flags=re.MULTILINE)
        return list(webvtt.from_buffer(io.StringIO(cleaned_content)))

    def _get_speaker(self, raw_text: str):
        match = re.match(r'<v\s+([^>]+)>', raw_text)
        if match:
            return match.group(1).strip()
        return None

    def _clean_text(self, raw_text: str):
        # Remove speaker tag and other VTT tags
        text = re.sub(r'<v\s+[^>]+>', '', raw_text)
        text = re.sub(r'</?v>', '', text)
        return text.strip()

    def _merge_captions(self, merge_threshold_seconds=60):
        if not self.captions:
            return []

        merged = []
        for caption in self.captions:
            speaker = self._get_speaker(caption.raw_text)
            text = self._clean_text(caption.raw_text)

            if not speaker or not text:
                continue
            
            current_start_time = datetime.strptime(caption.start.split('.')[0], '%H:%M:%S')

            # If the last speaker is the same and within the time threshold, combine the text
            if merged and merged[-1]['speaker'] == speaker:
                last_end_time_str = merged[-1]['end'].split('.')[0]
                last_end_time = datetime.strptime(last_end_time_str, '%H:%M:%S')
                
                if (current_start_time - last_end_time).total_seconds() <= merge_threshold_seconds:
                    merged[-1]['text'] += ' ' + text
                    merged[-1]['end'] = caption.end
                    continue

            merged.append({
                'speaker': speaker,
                'text': text,
                'start': caption.start,
                'end': caption.end
            })
        return merged

    def to_markdown(self) -> str:
        if not self.captions:
            return "# Conversion Error\n\nCould not find any captions in the VTT file."

        merged_captions = self._merge_captions()
        
        # --- Metadata ---
        title = self.file_path.stem
        participants = sorted(list(set(c['speaker'] for c in merged_captions)))
        
        if not self.captions:
            duration_minutes = 0
        else:
            start_time_str = self.captions[0].start
            end_time_str = self.captions[-1].end
            start_time = datetime.strptime(start_time_str.split('.')[0], '%H:%M:%S')
            end_time = datetime.strptime(end_time_str.split('.')[0], '%H:%M:%S')
            duration_seconds = (end_time - start_time).total_seconds()
            duration_minutes = round(duration_seconds / 60) if duration_seconds > 0 else 0

        # Get file modification date
        file_mod_timestamp = os.path.getmtime(self.file_path)
        file_mod_date = datetime.fromtimestamp(file_mod_timestamp).strftime('%Y年%m月%d日')

        # --- Build Markdown ---
        md_parts = [
            f"# {title}\n",
            f"**日時:** {file_mod_date}",
            "**参加者:**",
        ]
        md_parts.extend([f"- {p}" for p in participants])
        md_parts.append(f"\n**所要時間:** {duration_minutes}分\n")
        md_parts.append("## 発言記録\n")

        for entry in merged_captions:
            timestamp_str = entry['start'].split('.')[0]
            md_parts.append(f"**{entry['speaker']}** [{timestamp_str}]  ")
            md_parts.append(f"{entry['text']}\n")
            
        return "\n".join(md_parts)

def convert_vtt_to_md(vtt_content: str, file_path: str) -> str:
    """
    High-level function to convert VTT content to a formatted Markdown string.
    """
    try:
        converter = VttConverter(vtt_content, file_path)
        return converter.to_markdown()
    except Exception as e:
        return f"# Conversion Error\n\nAn unexpected error occurred: {e}"