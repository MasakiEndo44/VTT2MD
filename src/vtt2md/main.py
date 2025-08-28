import customtkinter
from tkinterdnd2 import TkinterDnD, DND_FILES
from pathlib import Path
import threading
import logging
from tkinter import filedialog, messagebox
from vtt2md.converter import convert_vtt_to_md

# --- Logger Setup ---
log_file = Path.home() / "Desktop" / "VTT2MD_debug.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w', encoding='utf-8'),
        logging.StreamHandler() # Also print to console
    ]
)
logging.info("Application starting...")

class App(customtkinter.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        # Initialize TkinterDnD
        self.TkdndVersion = TkinterDnD._require(self)

        customtkinter.set_appearance_mode("light")
        customtkinter.set_default_color_theme("blue")

        # --- Basic Setup ---
        self.title("VTT to MD Converter")
        self.geometry("600x700")

        # --- State ---
        self.file_path = None
        self.md_content = None

        # --- Widgets ---
        # Main content frame (this will be cleared and redrawn)
        self.main_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.pack(expand=True, fill=customtkinter.BOTH, padx=20, pady=(20, 0))

        # Status label (outside the main_frame, so it won't be cleared)
        self.status_label = customtkinter.CTkLabel(self, text="ステータス: 待機中", font=("Yu Gothic UI", 12))
        self.status_label.pack(side=customtkinter.BOTTOM, fill=customtkinter.X, padx=20, pady=(0, 10))

        self.create_initial_view()

    def create_initial_view(self):
        self._clear_frame()
        customtkinter.CTkLabel(self.main_frame, text="VTT → MD Converter", font=("Yu Gothic UI", 24, "bold")).pack(pady=(0, 30))
        self.drop_frame = customtkinter.CTkFrame(self.main_frame, width=400, height=200, corner_radius=10,
                                       fg_color=("gray80", "gray20"),
                                       border_width=2, border_color=("gray60", "gray40"))
        self.drop_frame.pack(pady=20, padx=20, fill=customtkinter.BOTH, expand=True)

        # Bind events for interactive UI
        self.drop_frame.dnd_bind('<<DropEnter>>', self.on_drag_enter)
        self.drop_frame.dnd_bind('<<DropLeave>>', self.on_drag_leave)
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.drop_file)
        customtkinter.CTkLabel(self.drop_frame, text="📁", font=("Yu Gothic UI", 72)).pack(pady=(20, 10))
        customtkinter.CTkLabel(self.drop_frame, text="ファイルをここにドラッグ＆ドロップ", font=("Yu Gothic UI", 16)).pack()
        customtkinter.CTkLabel(self.drop_frame, text="または", font=("Yu Gothic UI", 12)).pack(pady=(10, 0))
        customtkinter.CTkButton(self.main_frame, text="ファイルを選択", command=self.select_file,
                      font=("Yu Gothic UI", 14, "bold"), height=40).pack(pady=(20, 0))

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
        preview_text.insert("end", self.md_content)
        preview_text.configure(state="disabled")
        preview_text.pack(expand=True, fill=customtkinter.BOTH, padx=10, pady=10)
        button_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        button_frame.pack(pady=20)
        customtkinter.CTkButton(button_frame, text="💾 ダウンロード", command=self.download_file,
                      font=("Yu Gothic UI", 14, "bold"), height=40).pack(side=customtkinter.LEFT, padx=10)
        customtkinter.CTkButton(button_frame, text="🔄 新規変換", command=self.create_initial_view,
                      font=("Yu Gothic UI", 14, "bold"), height=40).pack(side=customtkinter.LEFT, padx=10)

    def drop_file(self, event):
        self.on_drag_leave(event) # Reset color after drop
        filepath = event.data
        logging.info(f"File dropped: {filepath}")
        if filepath.startswith('{') and filepath.endswith('}'):
            filepath = filepath[1:-1]
            logging.info(f"Sanitized path: {filepath}")
        self.process_file(filepath)

    def select_file(self):
        logging.info("'select_file' button clicked.")
        filepath = filedialog.askopenfilename(filetypes=[("VTT Files", "*.vtt")])
        if filepath:
            logging.info(f"File selected via dialog: {filepath}")
            self.process_file(filepath)

    def process_file(self, filepath):
        logging.info(f"--- Entered process_file ---")
        try:
            logging.info(f"1. Received path: {filepath}")
            
            self.file_path = Path(filepath)
            logging.info(f"2. Created Path object: {self.file_path}")

            if self.file_path.suffix.lower() != '.vtt':
                logging.warning(f"3. Invalid file type: {self.file_path.suffix}")
                messagebox.showerror("エラー", "VTTファイルを選択してください。")
                return
            logging.info(f"3. File type is valid (.vtt)")

            self.status_label.configure(text="ステータス: 変換中...")
            logging.info(f"4. Status label updated.")

            t = threading.Thread(target=self._run_conversion, daemon=True)
            logging.info(f"5. Thread object created.")
            
            t.start()
            logging.info(f"6. Thread started. Exiting process_file.")

        except Exception as e:
            logging.exception(f"CRITICAL ERROR inside process_file: {e}")
            messagebox.showerror("致命的なエラー", f"process_fileで予期せぬエラーが発生しました: {e}")

    def _run_conversion(self):
        try:
            logging.info(f"Reading content from {self.file_path}")
            with open(self.file_path, 'r', encoding='utf-8') as f:
                vtt_content = f.read()
            
            logging.info("Calling convert_vtt_to_md function.")
            self.md_content = convert_vtt_to_md(vtt_content, str(self.file_path))
            logging.info("Conversion successful. Scheduling UI update.")
            self.after(0, self.create_result_view)
        except FileNotFoundError:
            logging.error(f"File not found: {self.file_path}")
            self.after(0, lambda: messagebox.showerror("エラー", "ファイルが見つかりません。"))
        except Exception as e:
            logging.exception(f"An unexpected error occurred during conversion: {e}")
            self.after(0, lambda: messagebox.showerror("変換エラー", f"予期せぬエラーが発生しました: {e}"))
        finally:
            logging.info("Conversion thread finished.")
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
