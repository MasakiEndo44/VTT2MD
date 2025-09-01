import customtkinter
from tkinterdnd2 import TkinterDnD, DND_FILES
from pathlib import Path
import threading
from tkinter import filedialog, messagebox
from vtt2md.converter import convert_vtt_to_md
from datetime import datetime
from tkcalendar import DateEntry

# --- カスタムダイアログ --- #
class DateTimeDialog(customtkinter.CTkToplevel):
    """日付と時刻を同時に入力するためのカスタムダイアログ。"""
    def __init__(self, master=None):
        super().__init__(master)

        self.title("会議の日時を入力")
        self.lift()
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._date_str = None
        self._time_str = None

        # Define a larger, consistent font
        entry_font = ("Yu Gothic UI", 16)

        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Date Entry (tkcalendarを使用)
        customtkinter.CTkLabel(main_frame, text="会議の日付", font=("Yu Gothic UI", 13)).pack(anchor="w")
        self.date_entry = DateEntry(main_frame, date_pattern='y-mm-dd', width=18,
                                    background='#3B8ED0', foreground='white', borderwidth=2, 
                                    font=entry_font) # Apply font
        self.date_entry.pack(pady=(5, 15), fill="x", ipady=4) # Add internal padding

        # Time Entry
        customtkinter.CTkLabel(main_frame, text="会議の開始時刻 (HH:MM)", font=("Yu Gothic UI", 13)).pack(anchor="w")
        self.time_entry = customtkinter.CTkEntry(main_frame, placeholder_text="14:30", width=250, font=entry_font) # Apply font
        self.time_entry.pack(pady=(5, 20), fill="x", ipady=4) # Add internal padding
        self.time_entry.insert(0, datetime.now().strftime("%H:%M"))

        # Buttons
        button_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=(10, 15))

        self.ok_button = customtkinter.CTkButton(button_frame, text="OK", command=self._on_ok, width=100)
        self.ok_button.pack(side="left", padx=10)

        self.cancel_button = customtkinter.CTkButton(button_frame, text="キャンセル", command=self._on_cancel, fg_color="gray50", hover_color="gray40", width=100)
        self.cancel_button.pack(side="left", padx=10)
        
        self.time_entry.focus_set()

        # ウィンドウが表示される前にレイアウトを強制的に更新
        self.update_idletasks()
        # grab_set() はサイズ計算の後に呼び出す
        self.grab_set()

    def _on_ok(self, event=None):
        self._date_str = self.date_entry.get().strip()
        self._time_str = self.time_entry.get().strip()
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        self._date_str = None
        self._time_str = None
        self.grab_release()
        self.destroy()

    def get_input(self) -> tuple[str | None, str | None]:
        """ダイアログをモーダルで表示し、入力値を返す。"""
        self.master.wait_window(self)
        return self._date_str, self._time_str

# --- メインアプリケーション (以下は変更なし) --- #
class App(customtkinter.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        customtkinter.set_appearance_mode("light")
        customtkinter.set_default_color_theme("blue")
        self.title("VTT to MD Converter")
        self.geometry("600x750")
        self.file_path = None
        self.md_content = []
        self.meeting_datetime = None
        self.remove_fillers_var = customtkinter.BooleanVar(value=True)
        self.split_files_var = customtkinter.StringVar(value="single")
        self.main_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.pack(expand=True, fill=customtkinter.BOTH, padx=20, pady=(20, 0))
        self.status_label = customtkinter.CTkLabel(self, text="ステータス: 待機中", font=("Yu Gothic UI", 12))
        self.status_label.pack(side=customtkinter.BOTTOM, fill=customtkinter.X, padx=20, pady=(0, 10))
        self.create_initial_view()

    def create_initial_view(self):
        self._clear_frame()
        customtkinter.CTkLabel(self.main_frame, text="VTT → MD Converter", font=("Yu Gothic UI", 24, "bold")).pack(pady=(0, 20))
        self.drop_frame = customtkinter.CTkFrame(self.main_frame, width=400, height=200, corner_radius=10, fg_color=("gray80", "gray20"), border_width=2, border_color=("gray60", "gray40"))
        self.drop_frame.pack(pady=10, padx=20, fill=customtkinter.BOTH, expand=True)
        self.drop_frame.dnd_bind('<<DropEnter>>', self.on_drag_enter)
        self.drop_frame.dnd_bind('<<DropLeave>>', self.on_drag_leave)
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.drop_file)
        customtkinter.CTkLabel(self.drop_frame, text="📁", font=("Yu Gothic UI", 72)).pack(pady=(20, 10))
        customtkinter.CTkLabel(self.drop_frame, text="ファイルをここにドラッグ＆ドロップ", font=("Yu Gothic UI", 16)).pack()
        customtkinter.CTkLabel(self.drop_frame, text="または", font=("Yu Gothic UI", 12)).pack(pady=(10, 0))
        options_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        options_frame.pack(pady=(20, 10), fill="x")
        options_frame.columnconfigure(0, weight=1)
        options_frame.columnconfigure(1, weight=1)
        customtkinter.CTkSwitch(options_frame, text="フィラー・相槌を除去する", variable=self.remove_fillers_var, font=("Yu Gothic UI", 13)).grid(row=0, column=0, sticky="w", padx=10)
        output_format_frame = customtkinter.CTkFrame(options_frame)
        output_format_frame.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(10,0))
        customtkinter.CTkLabel(output_format_frame, text="出力形式:", font=("Yu Gothic UI", 13)).pack(side="left", padx=(0, 10))
        customtkinter.CTkRadioButton(output_format_frame, text="単一ファイル", variable=self.split_files_var, value="single", font=("Yu Gothic UI", 13)).pack(side="left", padx=5)
        customtkinter.CTkRadioButton(output_format_frame, text="複数ファイルに分割 (10000字以下)", variable=self.split_files_var, value="split", font=("Yu Gothic UI", 13)).pack(side="left", padx=5)
        customtkinter.CTkButton(self.main_frame, text="ファイルを選択して変換開始", command=self.select_file, font=("Yu Gothic UI", 14, "bold"), height=40).pack(pady=(10, 0), fill="x", padx=20)

    def on_drag_enter(self, event):
        self.drop_frame.configure(fg_color=("gray70", "gray10"))

    def on_drag_leave(self, event):
        self.drop_frame.configure(fg_color=("gray80", "gray20"))

    def create_result_view(self):
        self._clear_frame()
        customtkinter.CTkLabel(self.main_frame, text="✓ 変換完了", font=("Yu Gothic UI", 24, "bold"), text_color="#10B981").pack(pady=(0, 30))
        text_frame = customtkinter.CTkFrame(self.main_frame, corner_radius=10)
        text_frame.pack(expand=True, fill=customtkinter.BOTH, pady=10)
        preview_text = customtkinter.CTkTextbox(text_frame, wrap="word", font=("Yu Gothic", 12), activate_scrollbars=True)
        if self.md_content:
            preview_text.insert("end", self.md_content[0])
        preview_text.configure(state="disabled")
        preview_text.pack(expand=True, fill=customtkinter.BOTH, padx=10, pady=10)
        button_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        button_frame.pack(pady=20)
        customtkinter.CTkButton(button_frame, text="💾 ダウンロード", command=self.download_file, font=("Yu Gothic UI", 14, "bold"), height=40).pack(side=customtkinter.LEFT, padx=10)
        customtkinter.CTkButton(button_frame, text="🔄 新規変換", command=self.create_initial_view, font=("Yu Gothic UI", 14, "bold"), height=40).pack(side=customtkinter.LEFT, padx=10)

    def drop_file(self, event):
        self.on_drag_leave(event)
        filepath = event.data
        if filepath.startswith('{') and filepath.endswith('}'):
            filepath = filepath[1:-1]
        self.process_file(filepath)

    def select_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("VTT Files", "*.vtt")])
        if filepath:
            self.process_file(filepath)

    def _get_meeting_datetime(self) -> str | None:
        dialog = DateTimeDialog(self)
        date_str, time_str = dialog.get_input()
        if not date_str or not time_str:
            return None
        try:
            # tkcalendar returns a datetime.date object, so convert to string
            datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            messagebox.showerror("エラー", "日付の形式が不正です。YYYY-MM-DD形式で入力してください。")
            return None
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            messagebox.showerror("エラー", "時刻の形式が不正です。HH:MM形式で入力してください。")
            return None
        return f"{date_str} {time_str}"

    def process_file(self, filepath):
        self.file_path = Path(filepath)
        if self.file_path.suffix.lower() != '.vtt':
            messagebox.showerror("エラー", "VTTファイルを選択してください。")
            return
        self.meeting_datetime = self._get_meeting_datetime()
        if not self.meeting_datetime:
            return
        self.status_label.configure(text="ステータス: 変換中...")
        threading.Thread(target=self._run_conversion, daemon=True).start()

    def _run_conversion(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                vtt_content = f.read()
            self.md_content = convert_vtt_to_md(
                vtt_content,
                str(self.file_path),
                meeting_datetime=self.meeting_datetime,
                remove_fillers=self.remove_fillers_var.get(),
                split_output=(self.split_files_var.get() == "split")
            )
            self.after(0, self.create_result_view)
        except FileNotFoundError:
            self.after(0, lambda: messagebox.showerror("エラー", "ファイルが見つかりません。"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("変換エラー", f"予期せぬエラーが発生しました: {e}"))
        finally:
            self.after(0, lambda: self.status_label.configure(text="ステータス: 待機中"))

    def download_file(self):
        if not self.md_content:
            return

        # 分割しない場合、または分割結果が1つのファイルのみだった場合
        if self.split_files_var.get() == "single" or len(self.md_content) == 1:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".md",
                initialfile=f"{self.file_path.stem}.md",
                filetypes=[("Markdown Files", "*.md")]
            )
            if save_path:
                try:
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(self.md_content[0])
                    messagebox.showinfo("成功", "ファイルを保存しました。")
                except Exception as e:
                    messagebox.showerror("保存エラー", f"ファイルの保存中にエラーが発生しました: {e}")
        else:
            # 複数ファイルを新しいフォルダにまとめて保存
            save_path_base = filedialog.asksaveasfilename(
                initialfile=self.file_path.stem,
                title="保存フォルダ名と場所を指定してください"
            )
            if save_path_base:
                try:
                    new_folder_path = Path(save_path_base)
                    # 新しいディレクトリを作成 (既に存在していてもエラーにしない)
                    new_folder_path.mkdir(parents=True, exist_ok=True)
                    
                    file_basename = new_folder_path.name

                    for i, part_content in enumerate(self.md_content):
                        part_path = new_folder_path / f"{file_basename}_part{i+1}.md"
                        with open(part_path, 'w', encoding='utf-8') as f:
                            f.write(part_content)
                    messagebox.showinfo("成功", f"{len(self.md_content)}個のファイルを格納したフォルダ「{file_basename}」を作成しました。")
                except Exception as e:
                    messagebox.showerror("保存エラー", f"フォルダの作成またはファイルの保存中にエラーが発生しました: {e}")

    def _clear_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()