import webvtt
from datetime import datetime
from pathlib import Path
import io
import re

# --- 軽量フィラー除去 ---

# 起動時のファイルI/Oを避けるため、フィラーリストは初回変換時に読み込む（遅延読み込み）
_CACHED_FILLERS: tuple[list[str], list[str]] | None = None

def get_or_load_fillers() -> tuple[list[str], list[str]]:
    """
    キャッシュされたフィラーリストを返す。キャッシュがない場合はファイルから読み込む。
    """
    global _CACHED_FILLERS
    if _CACHED_FILLERS is not None:
        return _CACHED_FILLERS

    try:
        file_path = "docs/filler_deletion_list.md"
        p = Path(file_path)
        if not p.is_file():
            print(f"Warning: Filler list file not found at {file_path}")
            raise FileNotFoundError()

        content = p.read_text(encoding="utf-8")
        
        general_filler_section = re.search(r"### 代表的なフィラー\n((?:- .+\n)+)", content)
        general_fillers = []
        if general_filler_section:
            lines = general_filler_section.group(1).strip().split('\n')
            for line in lines:
                cleaned_line = line.strip().lstrip('- ').strip()
                general_fillers.extend([f.strip() for f in cleaned_line.split('、')])

        aizuchi_section = re.search(r"### 純粋な相槌（削除対象）\n((?:- .+\n)+)", content)
        aizuchi_fillers = []
        if aizuchi_section:
            lines = aizuchi_section.group(1).strip().split('\n')
            for line in lines:
                cleaned_line = line.strip().lstrip('- ').strip()
                aizuchi_fillers.extend([f.strip() for f in cleaned_line.split('、')])
        
        _CACHED_FILLERS = (sorted(list(set(general_fillers))), sorted(list(set(aizuchi_fillers))))
        return _CACHED_FILLERS
    except Exception as e:
        print(f"Error loading filler list: {e}. Using fallback list.")
        # ファイル読み込みに失敗した場合は、基本的なフォールバックリストを使用
        general = ["えーと", "えっと", "えー", "あー", "あのー", "あの", "そのー", "その", "なんか", "何か", "まあ", "まぁ", "うーん", "ふーん"]
        aizuchi = ["はい", "ええ", "うん", "そうですね", "なるほど", "はいはい"]
        _CACHED_FILLERS = (general, aizuchi)
        return _CACHED_FILLERS

def remove_fillers_simple(text: str) -> str:
    """
    フィラー除去と、それに伴う不自然な句読点の整形をまとめて行う。
    """
    if not text:
        return ""

    # 初回実行時にフィラーリストを読み込む
    general_fillers, aizuchi_fillers = get_or_load_fillers()

    # 1. 連続する相槌を除去 (例: 「はいはいはい」「うんうん」)
    for aizuchi in aizuchi_fillers:
        pattern = r'(' + re.escape(aizuchi) + r'){2,}'
        text = re.sub(pattern, "", text)

    # 2. 一般的なフィラーと単体の相槌を単語境界で除去
    all_fillers = general_fillers + aizuchi_fillers
    for filler in all_fillers:
        pattern = r'\b' + re.escape(filler) + r'\b'
        text = re.sub(pattern, "", text)

    # 3. 句読点のクリーンアップ処理
    previous_text = ""
    while previous_text != text:
        previous_text = text
        text = re.sub(r'([、。,.?？])([\s　]*[、。,.?？])+', r'\1', text)

    text = re.sub(r'^[\s　]*[、。.,?？]', '', text.strip()).strip()

    if re.fullmatch(r'[\s　、。,.?？ー-]*', text):
        return ""

    text = re.sub(r'\s+([、。,.?？])', r'\1', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()
    
    return text

# --- VTTコンバータークラス (以下は変更なし) ---
class VttConverter:
    """VTTファイルを解析し、Markdown文字列に変換する。"""
    def __init__(self, vtt_content: str, file_path: str):
        self.vtt_content = vtt_content
        self.file_path = Path(file_path)
        self.captions = self._parse_vtt()

    def _parse_vtt(self):
        cleaned_content = re.sub(r'^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}/\d+-\d+\s*$', '', self.vtt_content, flags=re.MULTILINE)
        return list(webvtt.from_buffer(io.StringIO(cleaned_content)))

    def _get_speaker(self, raw_text: str):
        match = re.match(r'<v\s+([^>]+)>', raw_text)
        return match.group(1).strip() if match else None

    def _clean_text(self, raw_text: str):
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
            if merged and merged[-1]['speaker'] == speaker:
                last_end_time = datetime.strptime(merged[-1]['end'].split('.')[0], '%H:%M:%S')
                if (current_start_time - last_end_time).total_seconds() <= merge_threshold_seconds:
                    merged[-1]['text'] += ' ' + text
                    merged[-1]['end'] = caption.end
                    continue
            merged.append({'speaker': speaker, 'text': text, 'start': caption.start, 'end': caption.end})
        return merged

    def to_markdown(self, meeting_datetime: str, remove_fillers: bool = False, split_output: bool = False) -> list[str]:
        if not self.captions:
            return ["# 変換エラー\n\nVTTファイルからキャプションが見つかりませんでした。"]

        merged_captions = self._merge_captions()
        if not merged_captions:
            return ["# 変換エラー\n\nVTTファイルから有効な発言を抽出できませんでした。"]

        title = self.file_path.stem
        participants = sorted(list(set(c['speaker'] for c in merged_captions)))
        start_time = datetime.strptime(self.captions[0].start.split('.')[0], '%H:%M:%S')
        end_time = datetime.strptime(self.captions[-1].end.split('.')[0], '%H:%M:%S')
        duration_minutes = round((end_time - start_time).total_seconds() / 60)

        header_parts = [
            f"# {title}\n",
            f"**日時:** {meeting_datetime}",
            "**参加者:**",
        ]
        header_parts.extend([f"- {p}" for p in participants])
        header_parts.append(f"\n**所要時間:** {duration_minutes}分\n")
        header_parts.append("## 発言記録\n")
        header = "\n".join(header_parts)

        body_entries = []
        for entry in merged_captions:
            text_to_process = entry['text']
            if remove_fillers:
                cleaned_text = remove_fillers_simple(text_to_process)
                if not cleaned_text.strip():
                    continue
                text_to_process = cleaned_text
            timestamp_str = entry['start'].split('.')[0]
            body_entries.append(f"**{entry['speaker']}** [{timestamp_str}]  \n{text_to_process}\n")

        if not split_output:
            return [header + "\n".join(body_entries)]

        chunks = []
        current_chunk_body = ""
        char_limit = 10000
        for entry_md in body_entries:
            if len(header) + len(current_chunk_body) + len(entry_md) > char_limit and current_chunk_body:
                chunks.append(header + current_chunk_body)
                current_chunk_body = entry_md
            else:
                current_chunk_body += entry_md
        
        if current_chunk_body:
            chunks.append(header + current_chunk_body)

        return chunks if chunks else [header]

def convert_vtt_to_md(vtt_content: str, file_path: str, meeting_datetime: str, remove_fillers: bool = False, split_output: bool = False) -> list[str]:
    """
    VTTコンテンツを整形されたMarkdown文字列に変換する高レベル関数。
    """
    try:
        converter = VttConverter(vtt_content, file_path)
        return converter.to_markdown(meeting_datetime=meeting_datetime, remove_fillers=remove_fillers, split_output=split_output)
    except Exception as e:
        error_message = f"# 変換エラー\n\n予期せぬエラーが発生しました: {e}"
        print(error_message)
        return [error_message]
