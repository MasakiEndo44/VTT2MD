import sys
import types

# Stub out darkdetect to avoid slow WMI calls during theme detection.
if "darkdetect" not in sys.modules:
    _darkdetect_stub = types.ModuleType("darkdetect")
    _darkdetect_stub.theme = lambda *_, **__: "Light"
    _darkdetect_stub.listener = lambda *_, **__: None
    sys.modules["darkdetect"] = _darkdetect_stub

import customtkinter
from tkinterdnd2 import TkinterDnD, DND_FILES
from pathlib import Path
import threading
import queue
from tkinter import filedialog, messagebox
from datetime import datetime
from importlib import import_module
from typing import TYPE_CHECKING
from vtt2md.converter import convert_vtt_to_md

if TYPE_CHECKING:
    from tkcalendar import Calendar  # type: ignore

# --- カスタムダイアログ --- #
class DateTimeDialog(customtkinter.CTkToplevel):
    """Dialog that collects the meeting date and start time."""
    def __init__(self, master=None):
        super().__init__(master)

        self.geometry("420x520")
        self.minsize(420, 520)
        self.resizable(False, False)

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

        # Calendar widget (tkcalendar) used for date selection
        customtkinter.CTkLabel(main_frame, text="会議の日付", font=("Yu Gothic UI", 13)).pack(anchor="w")
        Calendar = getattr(import_module("tkcalendar"), "Calendar")
        self.calendar = Calendar(
            main_frame,
            selectmode="day",
            date_pattern="y-mm-dd",
            showweeknumbers=False,
            firstweekday="monday",
            background="white",
            foreground="#1A1A1A",
            headersbackground="#3B8ED0",
            headersforeground="white",
            selectbackground="#3B8ED0",
            selectforeground="white",
            normalbackground="white",
            normalforeground="#1A1A1A",
            weekendbackground="#F0F4FA",
            weekendforeground="#1A1A1A",
            bordercolor="#3B8ED0",
            font=("Yu Gothic UI", 14),
        )
        self.calendar.pack(pady=(5, 15), fill="both", expand=True)
        self.calendar.selection_set(datetime.now().date())

        # Time Entry
        customtkinter.CTkLabel(main_frame, text="会議の開始時刻 (HH:MM)", font=("Yu Gothic UI", 13)).pack(anchor="w")
        time_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        time_frame.pack(pady=(5, 20), fill="x")
        current_time = datetime.now()
        default_hour = f"{current_time.hour:02d}"
        default_minute = f"{(current_time.minute // 15) * 15:02d}"
        hour_options = [f"{h:02d}" for h in range(24)]
        minute_options = ["00", "15", "30", "45"]
        self.hour_var = customtkinter.StringVar(value=default_hour)
        self.minute_var = customtkinter.StringVar(value=default_minute)
        self.hour_menu = customtkinter.CTkOptionMenu(
            time_frame,
            values=hour_options,
            variable=self.hour_var,
            width=100,
            font=entry_font,
        )
        self.hour_menu.pack(side="left", padx=(0, 10))
        self.minute_menu = customtkinter.CTkOptionMenu(
            time_frame,
            values=minute_options,
            variable=self.minute_var,
            width=100,
            font=entry_font,
        )
        self.minute_menu.pack(side="left")

        # Buttons
        button_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=(10, 15))

        self.ok_button = customtkinter.CTkButton(button_frame, text="OK", command=self._on_ok, width=100)
        self.ok_button.pack(side="left", padx=10)

        self.cancel_button = customtkinter.CTkButton(button_frame, text="キャンセル", command=self._on_cancel, fg_color="gray50", hover_color="gray40", width=100)
        self.cancel_button.pack(side="left", padx=10)
        
        self.hour_menu.focus_set()

        # ウィンドウが表示される前にレイアウトを強制的に更新
        self.update_idletasks()
        # grab_set() はサイズ計算の後に呼び出す
        self.grab_set()

    def _on_ok(self, event=None):
        self._date_str = self.calendar.get_date().strip()
        self._time_str = f"{self.hour_var.get()}:{self.minute_var.get()}"
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
        self._worker_queue: queue.Queue | None = None
        self._conversion_in_progress = False
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
        if self.file_path.suffix.lower() != ".vtt":
            messagebox.showerror("エラー", "VTTファイルを選択してください。")
            return
        self.meeting_datetime = self._get_meeting_datetime()
        if not self.meeting_datetime:
            return

        remove_fillers = self.remove_fillers_var.get()
        split_output = self.split_files_var.get() == "split"

        self._worker_queue = queue.Queue()
        self._conversion_in_progress = True
        self.status_label.configure(text="ステータス: 変換中...")
        threading.Thread(
            target=self._run_conversion,
            args=(remove_fillers, split_output),
            daemon=True,
        ).start()
        self.after(50, self._poll_worker_queue)

    def _run_conversion(self, remove_fillers: bool, split_output: bool):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                vtt_content = f.read()

            md_content = convert_vtt_to_md(
                vtt_content,
                str(self.file_path),
                meeting_datetime=self.meeting_datetime,
                remove_fillers=remove_fillers,
                split_output=split_output,
            )
            if self._worker_queue:
                self._worker_queue.put(("success", md_content))
        except FileNotFoundError:
            if self._worker_queue:
                self._worker_queue.put(("error", ("エラー", "ファイルが見つかりません。")))
        except Exception as e:
            if self._worker_queue:
                self._worker_queue.put(("error", ("変換エラー", f"予期せぬエラーが発生しました: {e}")))
        finally:
            if self._worker_queue:
                self._worker_queue.put(("done", None))

    def _poll_worker_queue(self):
        if not self._worker_queue:
            return
        try:
            while True:
                kind, payload = self._worker_queue.get_nowait()
                if kind == "success":
                    self.md_content = payload
                    self.create_result_view()
                elif kind == "error":
                    title, message = payload
                    messagebox.showerror(title, message)
                elif kind == "done":
                    self._conversion_in_progress = False
                self._worker_queue.task_done()
        except queue.Empty:
            pass

        if self._conversion_in_progress:
            self.after(50, self._poll_worker_queue)
        else:
            self.status_label.configure(text="ステータス: 待機中")
            self._worker_queue = None


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
