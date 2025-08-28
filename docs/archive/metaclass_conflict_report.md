### レポート: `customtkinter` と `tkinterdnd2` の統合における `TypeError: metaclass conflict` の解決策

#### 1. 問題の再確認

現在、開発中のVTT to MD変換ツールにおいて、`customtkinter` と `tkinterdnd2` の両ライブラリを統合しようとした際に `TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases` というエラーが発生しています。このエラーは、両ライブラリが `tkinter.Tk` クラスを異なる方法で拡張しようとすることに起因するメタクラスの競合が原因です。

#### 2. 調査結果

Google Web Search および o3-search を用いて調査を行った結果、この問題は `customtkinter` と `tkinterdnd2` を併用する際の既知の課題であり、Stack Overflowなどのコミュニティで解決策が提示されていることが判明しました。

**主要な解決策の概要:**

この `TypeError: metaclass conflict` を解決するための推奨されるアプローチは、アプリケーションのメインクラスが `customtkinter.CTk` と `tkinterdnd2.TkinterDnD.DnDWrapper` の両方から継承することです。これにより、`customtkinter` のモダンなUI機能と `tkinterdnd2` のドラッグ＆ドロップ機能を単一のクラスで統合することが可能になります。

#### 3. 実装方法

以下に、この解決策を適用するためのコードスニペットと解説を示します。

```python
import customtkinter
from tkinterdnd2 import TkinterDnD, DND_FILES # DND_ALL も使用可能
from pathlib import Path
import threading
from tkinter import filedialog, messagebox # tkinterのmessageboxとfiledialogはそのまま使用

# converter.py からのインポートを想定
from vtt2md.converter import convert_vtt_to_md

class App(customtkinter.CTk, TkinterDnD.DnDWrapper): # 両方から継承
    def __init__(self):
        super().__init__() # customtkinter.CTk の初期化を呼び出す

        # TkinterDnD の初期化
        # TkinterDnD._require(self) は、customtkinter.CTk インスタンスを
        # TkinterDnD のルートウィンドウとして登録するために重要です。
        self.TkdndVersion = TkinterDnD._require(self)

        customtkinter.set_appearance_mode("light") # Modes: "System" (default), "Dark", "Light"
        customtkinter.set_default_color_theme("blue") # Themes: "blue" (default), "dark-blue", "green"

        # --- Basic Setup ---
        self.title("VTT to MD Converter")
        self.geometry("600x700")

        # --- State ---
        self.file_path = None
        self.md_content = None

        # --- Widgets ---
        self.main_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.pack(expand=True, fill=customtkinter.BOTH, padx=20, pady=20)

        self.status_label = customtkinter.CTkLabel(self.main_frame, text="ステータス: 待機中", font=("Yu Gothic UI", 12))
        self.status_label.pack(side=customtkinter.BOTTOM, fill=customtkinter.X, pady=(0, 10))

        self.create_initial_view()

    def create_initial_view(self):
        self._clear_frame()

        # --- Header ---
        customtkinter.CTkLabel(self.main_frame, text="VTT → MD Converter", font=("Yu Gothic UI", 24, "bold")).pack(pady=(0, 30))

        # --- Drop Area ---
        self.drop_frame = customtkinter.CTkFrame(self.main_frame, width=400, height=200, corner_radius=10,
                                       fg_color=("gray80", "gray20"),
                                       border_width=2, border_color=("gray60", "gray40"))
        self.drop_frame.pack(pady=20, padx=20, fill=customtkinter.BOTH, expand=True)
        
        # Bind drag and drop events
        self.drop_frame.drop_target_register(DND_FILES) # DND_ALL も使用可能
        self.drop_frame.dnd_bind('<<Drop>>', self.drop_file)

        customtkinter.CTkLabel(self.drop_frame, text="📁", font=("Yu Gothic UI", 72)).pack(pady=(20, 10))
        customtkinter.CTkLabel(self.drop_frame, text="ファイルをここにドラッグ＆ドロップ", font=("Yu Gothic UI", 16)).pack()
        customtkinter.CTkLabel(self.drop_frame, text="または", font=("Yu Gothic UI", 12)).pack(pady=(10, 0))

        # --- Button ---
        customtkinter.CTkButton(self.main_frame, text="ファイルを選択", command=self.select_file,
                      font=("Yu Gothic UI", 14, "bold"), height=40).pack(pady=(20, 0))

    def create_result_view(self):
        self._clear_frame()

        # --- Header ---
        customtkinter.CTkLabel(self.main_frame, text="✓ 変換完了", font=("Yu Gothic UI", 24, "bold"), text_color="#10B981").pack(pady=(0, 30))

        # --- Preview ---
        text_frame = customtkinter.CTkFrame(self.main_frame, corner_radius=10)
        text_frame.pack(expand=True, fill=customtkinter.BOTH, pady=10)
        
        preview_text = customtkinter.CTkTextbox(text_frame, wrap="word", font=("Yu Gothic", 12), activate_scrollbars=True)
        preview_text.insert("end", self.md_content)
        preview_text.configure(state="disabled")
        preview_text.pack(expand=True, fill=customtkinter.BOTH, padx=10, pady=10)

        # --- Buttons ---
        button_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        button_frame.pack(pady=20)
        customtkinter.CTkButton(button_frame, text="💾 ダウンロード", command=self.download_file,
                      font=("Yu Gothic UI", 14, "bold"), height=40).pack(side=customtkinter.LEFT, padx=10)
        customtkinter.CTkButton(button_frame, text="🔄 新規変換", command=self.create_initial_view,
                      font=("Yu Gothic UI", 14, "bold"), height=40).pack(side=customtkinter.LEFT, padx=10)

    def drop_file(self, event):
        filepath = event.data
        # TkinterDnD2 returns paths in curly braces if they contain spaces
        if filepath.startswith('{') and filepath.endswith('}'):
            filepath = filepath[1:-1]
        self.process_file(filepath)

    def select_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("VTT Files", "*.vtt")])
        if filepath:
            self.process_file(filepath)

    def process_file(self, filepath):
        self.file_path = Path(filepath)
        if self.file_path.suffix.lower() != '.vtt':
            messagebox.showerror("エラー", "VTTファイルを選択してください。")
            return

        self.status_label.configure(text="ステータス: 変換中...")
        # Run conversion in a separate thread to keep UI responsive
        threading.Thread(target=self._run_conversion).start()

    def _run_conversion(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                vtt_content = f.read()
            
            self.md_content = convert_vtt_to_md(vtt_content, str(self.file_path))
            self.after(0, self.create_result_view) # Schedule UI update on the main thread
        except FileNotFoundError:
            self.after(0, lambda: messagebox.showerror("エラー", "ファイルが見つかりません。"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("変換エラー", f"予期せぬエラーが発生しました: {e}"))
        finally:
            self.after(0, lambda: self.status_label.configure(text="ステータス: 待機中"))

    def download_file(self):
        if not self.md_content:
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            initialfile=f"{self.file_path.stem}.md",
            filetypes=[("Markdown Files", "*.md")]
        )
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(self.md_content)
                messagebox.showinfo("成功", "ファイルを保存しました。")
            except Exception as e:
                messagebox.showerror("保存エラー", f"ファイルの保存中にエラーが発生しました: {e}")

    def _clear_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
