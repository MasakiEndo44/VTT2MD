# AGENTS.md

## 目的
このドキュメントは、VTT2MD プロジェクトに関わるエージェント同士が最小限のコンテキスト共有で作業できるようにするための概要資料です。コードリーディングや設計判断の出発点として活用してください。

## プロジェクト概要
- Microsoft Teams の会議トランスクリプト（`.vtt`）を Copilot 等で再利用しやすい Markdown に変換する Windows デスクトップアプリケーション。
- GUI は `customtkinter` と `TkinterDnD2` を用いたドラッグ&ドロップ主体の操作を想定。
- 会議日時の手入力、参加者リストの自動抽出、軽量なフィラー除去、10,000 文字上限に合わせた分割保存をサポート。
- オフライン動作を前提としており、Python 3.9 以上での実行を想定。

## リポジトリ構成（主要ファイル）
- `src/vtt2md/main.py`: GUI エントリーポイント。ファイル選択、プレビュー、出力保存などの UI ロジックを担当。
- `src/vtt2md/converter.py`: VTT 解析と Markdown 生成の中核ロジック。発言マージやフィラー除去を実装。
- `docs/requirements.md`: 要件定義。機能・非機能要件や画面設計の指針を記載。
- `docs/filler_deletion_list.md`: フィラー除去辞書。`converter.py` から遅延読み込みされる。
- `docs/user_manual.md`: エンドユーザー向け操作手順。
- `tests/test_converter.py`: 主要ロジックのユニットテスト。
- `run_sample_test.py`: サンプル VTT を使った動作確認スクリプト。
- ビルド関連: `build.bat`, `main.spec`, `dist/`, `build/`.

## セットアップと依存関係
1. `pip install -r requirements.txt`
2. 開発・テスト用途では `pip install -r requirements-dev.txt`
3. 主要依存:
   - `webvtt-py`（VTT パース）
   - `customtkinter`, `TkinterDnD2`, `tkcalendar`（GUI）
   - `pyinstaller`（配布用バイナリ作成）

## 典型的なワークフロー
- **開発実行**: `python src/vtt2md/main.py`
- **テスト**: `pytest` または `python run_sample_test.py`
- **ビルド**: `python -m pyinstaller src/vtt2md/main.py --onefile --windowed --name VTT2MD`（`build.bat` 参照）
- **成果物確認**: `dist/VTT2MD.exe`

## 注意事項
- 文字化けが発生する場合はエディタのエンコーディング設定を UTF-8 に揃えること。
- フィラー除去辞書を更新する際は `converter.py` のパースロジック（正規表現）との整合性に注意。
- 大きな議事録では分割出力の 10,000 文字上限を超えないよう、`converter.py` の `char_limit` を調整する必要がある。
- Windows 固有の依存（`TkinterDnD2`）があるため、他 OS での動作は保証されていない。
- リポジトリには既に未コミット変更が存在する場合があるため、作業前に `git status` を確認し、他タスクとのコンフリクトを避けること。

## 推奨タスク分担の例
- **UI/UX 担当**: `src/vtt2md/main.py` と `assets/` の更新、`docs/user_manual.md` の整備。
- **変換ロジック担当**: `src/vtt2md/converter.py` とテスト (`tests/`) の拡充、フィラー辞書の管理。
- **配布・CI 担当**: `build.bat`, `main.spec`, パッケージング、サンプルテストの自動化。
