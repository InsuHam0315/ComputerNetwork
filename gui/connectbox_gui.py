"""Modern Tkinter GUI for the final ConnectBox presentation version."""

from __future__ import annotations

import ctypes
import os
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from client.client_main import send_paths
from common.progress import format_bytes
from server.server_main import run_server


BG = "#F5F7FB"
CARD = "#FFFFFF"
BORDER = "#E5E7EB"
TEXT = "#111827"
MUTED = "#6B7280"
PRIMARY = "#2563EB"
PRIMARY_DARK = "#1D4ED8"
ACCENT = "#3B82F6"
SUCCESS = "#22C55E"
SUCCESS_DARK = "#16A34A"
SUCCESS_BG = "#DCFCE7"
DANGER = "#EF4444"
DANGER_DARK = "#DC2626"
DANGER_BG = "#FEF2F2"
IDLE_BG = "#EEF2FF"
ACTIVE_BG = "#DBEAFE"
ERROR_BG = "#FEE2E2"
LOG_BG = "#111827"
LOG_FG = "#E5E7EB"
LOG_MUTED = "#9CA3AF"
INPUT_BG = "#F9FAFB"
SEGMENT_BG = "#EAF0FF"


def resource_path(relative_path: str) -> Path:
    """Return a path that works both from source and PyInstaller bundles."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / relative_path
    return Path(__file__).resolve().parents[1] / relative_path


class ConnectBoxApp(tk.Tk):
    def __init__(self) -> None:
        self._set_windows_app_id()
        super().__init__()
        self.title("ConnectBox")
        self.geometry("1100x760")
        self.minsize(980, 700)
        self.configure(bg=BG)

        self.events: queue.Queue[tuple[str, str, object]] = queue.Queue()
        self.send_files: list[Path] = []
        self.send_folder: Path | None = None
        self.send_worker: threading.Thread | None = None
        self.receive_worker: threading.Thread | None = None
        self.active_tab = "receive"
        self.progress_widgets: dict[str, dict[str, tk.Widget | ttk.Progressbar]] = {}
        self.progress_trackers: dict[str, dict[str, float | int | None]] = {
            "receive": {"time": None, "bytes": 0, "start_time": None},
            "send": {"time": None, "bytes": 0, "start_time": None},
        }

        self.logo_source_image: tk.PhotoImage | None = None
        self.logo_image: tk.PhotoImage | None = None
        self.icon_image: tk.PhotoImage | None = None

        self._apply_window_icon()
        self._configure_style()
        self._build_widgets()
        self.after(100, self._poll_events)

    def _configure_style(self) -> None:
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure(
            "Connect.Horizontal.TProgressbar",
            troughcolor=BORDER,
            background=ACCENT,
            bordercolor=BORDER,
            lightcolor=ACCENT,
            darkcolor=PRIMARY,
            thickness=12,
        )
        self.style.configure("Vertical.TScrollbar", gripcount=0, background="#374151")

    def _apply_window_icon(self) -> None:
        icon_ico = resource_path("assets/connectbox_icon.ico")
        icon_png = resource_path("assets/connectbox_icon.png")

        icon_applied = False
        if icon_ico.exists():
            try:
                self.iconbitmap(default=str(icon_ico))
                icon_applied = True
            except tk.TclError:
                icon_applied = False

        if not icon_applied and icon_png.exists():
            try:
                self.icon_image = tk.PhotoImage(file=str(icon_png))
                self.iconphoto(True, self.icon_image)
            except tk.TclError:
                self.icon_image = None

    def _set_windows_app_id(self) -> None:
        if os.name != "nt":
            return
        try:
            app_id = "ConnectBox.FileTransfer.FinalPresentation"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass

    def _build_widgets(self) -> None:
        root = tk.Frame(self, bg=BG, padx=24, pady=22)
        root.pack(fill=tk.BOTH, expand=True)

        self._build_header(root)
        self._build_segment_tabs(root)

        self.content = tk.Frame(root, bg=BG)
        self.content.pack(fill=tk.BOTH, expand=True)

        self.receive_frame = tk.Frame(self.content, bg=BG)
        self.send_frame = tk.Frame(self.content, bg=BG)

        self._build_receive_tab()
        self._build_send_tab()
        self._show_tab("receive")

    def _build_header(self, parent: tk.Frame) -> None:
        header = tk.Frame(
            parent,
            bg=CARD,
            padx=22,
            pady=18,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        header.pack(fill=tk.X)

        brand = tk.Frame(header, bg=CARD)
        brand.pack(side=tk.LEFT, fill=tk.X, expand=True)

        brand_row = tk.Frame(brand, bg=CARD)
        brand_row.pack(anchor="w")

        self._load_logo_image()
        if self.logo_image is not None:
            tk.Label(brand_row, image=self.logo_image, bg=CARD, bd=0).pack(
                side=tk.LEFT, padx=(0, 12)
            )

        tk.Label(
            brand_row,
            text="ConnectBox",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 26, "bold"),
        ).pack(side=tk.LEFT)

        tk.Label(
            brand,
            text="LAN File & Folder Transfer",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(6, 0))

        right = tk.Frame(header, bg=CARD)
        right.pack(side=tk.RIGHT, anchor="ne")
        self.global_status_label = tk.Label(
            right,
            text="● Ready",
            bg=IDLE_BG,
            fg=PRIMARY,
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=7,
        )
        self.global_status_label.pack(anchor="e")
        tk.Label(
            right,
            text="Final GUI",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="e", pady=(8, 0))

    def _load_logo_image(self) -> None:
        logo_path = resource_path("assets/connectbox_logo.png")
        if not logo_path.exists():
            return
        try:
            self.logo_source_image = tk.PhotoImage(file=str(logo_path))
            target_size = 56
            factor = max(1, min(
                self.logo_source_image.width(),
                self.logo_source_image.height(),
            ) // target_size)
            self.logo_image = self.logo_source_image.subsample(factor, factor)
        except tk.TclError:
            self.logo_source_image = None
            self.logo_image = None

    def _build_segment_tabs(self, parent: tk.Frame) -> None:
        shell = tk.Frame(parent, bg=BG)
        shell.pack(fill=tk.X, pady=(16, 14))

        segmented = tk.Frame(shell, bg=SEGMENT_BG, padx=4, pady=4)
        segmented.pack(anchor="w")

        self.tab_buttons = {
            "receive": self._make_segment_button(segmented, "receive", "받기"),
            "send": self._make_segment_button(segmented, "send", "보내기"),
        }

    def _make_segment_button(self, parent: tk.Frame, key: str, text: str) -> tk.Button:
        button = tk.Button(
            parent,
            text=text,
            command=lambda: self._show_tab(key),
            bd=0,
            relief="flat",
            padx=26,
            pady=9,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        button.pack(side=tk.LEFT)
        return button

    def _show_tab(self, key: str) -> None:
        self.active_tab = key
        self.receive_frame.pack_forget()
        self.send_frame.pack_forget()

        if key == "receive":
            self.receive_frame.pack(fill=tk.BOTH, expand=True)
        else:
            self.send_frame.pack(fill=tk.BOTH, expand=True)

        for tab_key, button in self.tab_buttons.items():
            if tab_key == key:
                button.configure(
                    bg=PRIMARY,
                    fg="#FFFFFF",
                    activebackground=PRIMARY_DARK,
                    activeforeground="#FFFFFF",
                )
            else:
                button.configure(
                    bg=SEGMENT_BG,
                    fg=MUTED,
                    activebackground="#DDE7FF",
                    activeforeground=PRIMARY,
                )

    def _make_card(
        self,
        parent: tk.Frame,
        title: str,
        subtitle: str = "",
        *,
        fill: str = tk.X,
        expand: bool = False,
    ) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        card.pack(fill=fill, expand=expand, pady=(0, 14))

        body = tk.Frame(card, bg=CARD, padx=18, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            body,
            text=title,
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")
        if subtitle:
            tk.Label(
                body,
                text=subtitle,
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 10),
                wraplength=820,
                justify="left",
            ).pack(anchor="w", pady=(4, 12))
        else:
            tk.Frame(body, bg=CARD, height=10).pack(fill=tk.X)

        content = tk.Frame(body, bg=CARD)
        content.pack(fill=tk.BOTH, expand=True)
        return content

    def _build_receive_tab(self) -> None:
        self.receive_host_var = tk.StringVar(value="0.0.0.0")
        self.receive_port_var = tk.StringVar(value="5001")
        self.receive_save_dir_var = tk.StringVar(value="received")

        top = tk.Frame(self.receive_frame, bg=BG)
        top.pack(fill=tk.X)
        left = tk.Frame(top, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        right = tk.Frame(top, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        settings = self._make_card(
            left,
            "받기 모드",
            "이 PC를 수신 서버로 열고, 같은 LAN의 송신자가 접속하면 파일/폴더를 저장합니다.",
        )
        settings.columnconfigure(1, weight=1)
        settings.columnconfigure(3, weight=0)

        tk.Label(
            settings,
            text="연결을 열어두면 한 번의 전송 세션을 받은 뒤 자동으로 종료됩니다.",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        self.receive_status_label = self._make_status_badge(settings, "● Ready")
        self.receive_status_label.grid(row=0, column=3, sticky="e", pady=(0, 10))

        self._make_form_label(settings, "Host").grid(row=1, column=0, sticky="w", pady=6)
        self._make_entry(settings, self.receive_host_var).grid(
            row=1, column=1, sticky="ew", padx=(10, 14), pady=6
        )
        self._make_form_label(settings, "Port").grid(row=1, column=2, sticky="w", pady=6)
        self._make_entry(settings, self.receive_port_var, width=10).grid(
            row=1, column=3, sticky="ew", pady=6
        )

        self._make_form_label(settings, "저장 폴더").grid(row=2, column=0, sticky="w", pady=6)
        self._make_entry(settings, self.receive_save_dir_var).grid(
            row=2, column=1, sticky="ew", padx=(10, 14), pady=6
        )
        self._make_button(
            settings,
            "폴더 선택",
            self._choose_receive_dir,
            variant="secondary",
        ).grid(row=2, column=2, sticky="ew", padx=(0, 8), pady=6)
        self._make_button(
            settings,
            "폴더 열기",
            self._open_receive_dir,
            variant="secondary",
        ).grid(row=2, column=3, sticky="ew", pady=6)

        self.receive_start_button = self._make_button(
            settings,
            "수신 시작",
            self._start_receive_server,
            variant="success",
        )
        self.receive_start_button.grid(
            row=3, column=0, columnspan=4, sticky="ew", pady=(12, 0)
        )

        self.progress_widgets["receive"] = self._build_progress_card(
            right,
            "수신 진행률",
            "받는 파일의 현재 진행률과 전체 저장 진행률을 보여줍니다.",
        )
        self.receive_log = self._build_log_card(
            self.receive_frame,
            "수신 로그",
            lambda: self._clear_log("receive"),
        )

    def _build_send_tab(self) -> None:
        self.send_host_var = tk.StringVar(value="127.0.0.1")
        self.send_port_var = tk.StringVar(value="5001")

        top = tk.Frame(self.send_frame, bg=BG)
        top.pack(fill=tk.X)
        left = tk.Frame(top, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        right = tk.Frame(top, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        destination = self._make_card(
            left,
            "보내기 모드",
            "받는 PC의 IPv4 주소와 포트를 입력한 뒤 파일 여러 개 또는 폴더 하나를 전송합니다.",
        )
        destination.columnconfigure(1, weight=1)
        destination.columnconfigure(3, weight=0)

        tk.Label(
            destination,
            text="같은 PC 테스트는 127.0.0.1, LAN 시연은 받는 PC의 IPv4 주소를 사용하세요.",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        self.send_status_label = self._make_status_badge(destination, "● Ready")
        self.send_status_label.grid(row=0, column=3, sticky="e", pady=(0, 10))

        self._make_form_label(destination, "서버 IP").grid(row=1, column=0, sticky="w", pady=6)
        self._make_entry(destination, self.send_host_var).grid(
            row=1, column=1, sticky="ew", padx=(10, 14), pady=6
        )
        self._make_form_label(destination, "Port").grid(row=1, column=2, sticky="w", pady=6)
        self._make_entry(destination, self.send_port_var, width=10).grid(
            row=1, column=3, sticky="ew", pady=6
        )

        selection = self._make_card(
            left,
            "보낼 항목",
            "파일은 여러 개 선택할 수 있고, 폴더는 내부 구조를 유지한 채 전송됩니다.",
        )
        button_row = tk.Frame(selection, bg=CARD)
        button_row.pack(fill=tk.X)
        self._make_button(
            button_row,
            "파일 선택",
            self._add_send_files,
            variant="secondary",
        ).pack(side=tk.LEFT)
        self._make_button(
            button_row,
            "폴더 선택",
            self._choose_send_folder,
            variant="secondary",
        ).pack(side=tk.LEFT, padx=8)
        self._make_button(
            button_row,
            "선택 초기화",
            self._clear_send_selection,
            variant="danger",
        ).pack(side=tk.LEFT)

        self.selection_summary_label = tk.Label(
            selection,
            text="선택된 항목 없음",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 10),
        )
        self.selection_summary_label.pack(anchor="w", pady=(12, 6))

        self.send_listbox = tk.Listbox(
            selection,
            height=4,
            bg=INPUT_BG,
            fg=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            selectbackground=PRIMARY,
            selectforeground="#FFFFFF",
            activestyle="none",
            font=("Segoe UI", 10),
        )
        self.send_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        self.send_button = self._make_button(
            selection,
            "전송 시작",
            self._start_send,
            variant="primary",
        )
        self.send_button.pack(fill=tk.X)

        self.progress_widgets["send"] = self._build_progress_card(
            right,
            "전송 진행률",
            "보내는 파일의 현재 진행률과 전체 전송 진행률을 보여줍니다.",
        )
        self.send_log = self._build_log_card(
            self.send_frame,
            "전송 로그",
            lambda: self._clear_log("send"),
        )

    def _make_form_label(self, parent: tk.Frame, text: str) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        )

    def _make_entry(
        self,
        parent: tk.Frame,
        variable: tk.StringVar,
        *,
        width: int | None = None,
    ) -> tk.Entry:
        return tk.Entry(
            parent,
            textvariable=variable,
            width=width or 28,
            bg=INPUT_BG,
            fg=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            insertbackground=TEXT,
            font=("Segoe UI", 10),
        )

    def _make_button(
        self,
        parent: tk.Frame,
        text: str,
        command: Callable[[], None],
        *,
        variant: str,
    ) -> tk.Button:
        palette = {
            "primary": (PRIMARY, "#FFFFFF", PRIMARY_DARK),
            "success": (SUCCESS, "#FFFFFF", SUCCESS_DARK),
            "secondary": ("#EEF2FF", PRIMARY, "#DBEAFE"),
            "danger": (DANGER_BG, DANGER_DARK, "#FEE2E2"),
        }[variant]
        bg, fg, active_bg = palette
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            disabledforeground="#CBD5E1",
            bd=0,
            relief="flat",
            padx=14,
            pady=9,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            takefocus=True,
        )

    def _make_status_badge(self, parent: tk.Frame, text: str) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            bg=IDLE_BG,
            fg=PRIMARY,
            font=("Segoe UI", 9, "bold"),
            padx=11,
            pady=5,
        )

    def _build_progress_card(
        self,
        parent: tk.Frame,
        title: str,
        subtitle: str,
    ) -> dict[str, tk.Widget | ttk.Progressbar]:
        body = self._make_card(parent, title, subtitle)

        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        current_panel = self._make_progress_panel(body, 0, "현재 파일 진행률")
        total_panel = self._make_progress_panel(body, 1, "전체 진행률")

        metrics = tk.Frame(body, bg=CARD)
        metrics.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        metrics.columnconfigure(0, weight=1)
        metrics.columnconfigure(1, weight=1)
        metrics.columnconfigure(2, weight=1)

        file_value = self._make_metric(metrics, 0, "파일", "대기")
        speed_value = self._make_metric(metrics, 1, "전송 속도", "대기")
        state_value = self._make_metric(metrics, 2, "전송 상태", "Ready")

        return {
            "current_label": current_panel["label"],
            "current_bar": current_panel["bar"],
            "total_label": total_panel["label"],
            "total_bar": total_panel["bar"],
            "file_value": file_value,
            "speed_value": speed_value,
            "state_value": state_value,
        }

    def _make_progress_panel(
        self, parent: tk.Frame, column: int, title: str
    ) -> dict[str, tk.Widget | ttk.Progressbar]:
        panel = tk.Frame(
            parent,
            bg=INPUT_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        panel.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
        tk.Label(
            panel,
            text=title,
            bg=INPUT_BG,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        label = tk.Label(
            panel,
            text="0%",
            bg=INPUT_BG,
            fg=MUTED,
            font=("Segoe UI", 10),
            wraplength=360,
            justify="left",
        )
        label.pack(anchor="w", fill=tk.X, pady=(4, 6))
        bar = ttk.Progressbar(
            panel,
            maximum=100,
            mode="determinate",
            style="Connect.Horizontal.TProgressbar",
        )
        bar.pack(fill=tk.X)
        return {"label": label, "bar": bar}

    def _make_metric(self, parent: tk.Frame, column: int, title: str, value: str) -> tk.Label:
        box = tk.Frame(
            parent,
            bg=INPUT_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        box.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        tk.Label(
            box,
            text=title,
            bg=INPUT_BG,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w")
        value_label = tk.Label(
            box,
            text=value,
            bg=INPUT_BG,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        )
        value_label.pack(anchor="w", pady=(3, 0))
        return value_label

    def _build_log_card(
        self,
        parent: tk.Frame,
        title: str,
        clear_command: Callable[[], None],
    ) -> tk.Text:
        body = self._make_card(
            parent,
            title,
            "어두운 콘솔 스타일로 상태 로그를 확인합니다.",
            fill=tk.BOTH,
            expand=True,
        )

        header = tk.Frame(body, bg=CARD)
        header.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            header,
            text="Console",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT)
        self._make_button(header, "로그 지우기", clear_command, variant="secondary").pack(
            side=tk.RIGHT
        )

        console = tk.Frame(body, bg=LOG_BG, padx=10, pady=10)
        console.pack(fill=tk.BOTH, expand=True)

        text = tk.Text(
            console,
            height=8,
            state="disabled",
            wrap="word",
            bg=LOG_BG,
            fg=LOG_FG,
            insertbackground=LOG_FG,
            relief="flat",
            bd=0,
            padx=2,
            pady=2,
            font=("Consolas", 10),
        )
        scrollbar = ttk.Scrollbar(console, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.tag_configure("time", foreground=LOG_MUTED)
        text.tag_configure("success", foreground=SUCCESS)
        text.tag_configure("error", foreground="#FCA5A5")
        text.tag_configure("info", foreground=LOG_FG)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return text

    def _choose_receive_dir(self) -> None:
        selected = filedialog.askdirectory(title="받은 파일 저장 폴더 선택")
        if selected:
            self.receive_save_dir_var.set(selected)

    def _open_receive_dir(self) -> None:
        save_dir = Path(self.receive_save_dir_var.get().strip() or "received")
        try:
            save_dir.mkdir(parents=True, exist_ok=True)
            if hasattr(os, "startfile"):
                os.startfile(str(save_dir))  # type: ignore[attr-defined]
            else:
                messagebox.showinfo("ConnectBox", f"저장 폴더: {save_dir.resolve()}")
        except OSError as exc:
            messagebox.showerror("ConnectBox", f"저장 폴더를 열 수 없습니다: {exc}")

    def _add_send_files(self) -> None:
        selected = filedialog.askopenfilenames(title="보낼 파일 선택")
        for filename in selected:
            path = Path(filename)
            if path not in self.send_files:
                self.send_files.append(path)
        self._refresh_send_listbox()

    def _choose_send_folder(self) -> None:
        selected = filedialog.askdirectory(title="보낼 폴더 선택")
        if selected:
            self.send_folder = Path(selected)
        self._refresh_send_listbox()

    def _clear_send_selection(self) -> None:
        self.send_files.clear()
        self.send_folder = None
        self._refresh_send_listbox()

    def _refresh_send_listbox(self) -> None:
        self.send_listbox.delete(0, tk.END)
        for path in self.send_files:
            self.send_listbox.insert(tk.END, f"파일  {path}")
        if self.send_folder is not None:
            self.send_listbox.insert(tk.END, f"폴더  {self.send_folder}")

        file_count = len(self.send_files)
        folder_count = 1 if self.send_folder is not None else 0
        if file_count == 0 and folder_count == 0:
            summary = "선택된 항목 없음"
        elif folder_count:
            summary = f"파일 {file_count}개 + 폴더 1개 선택됨"
        else:
            summary = f"파일 {file_count}개 선택됨"
        self.selection_summary_label.configure(text=summary)

    def _start_receive_server(self) -> None:
        if self.receive_worker is not None and self.receive_worker.is_alive():
            messagebox.showinfo("ConnectBox", "수신 서버가 이미 실행 중입니다.")
            return

        try:
            port = self._parse_port(self.receive_port_var.get())
        except ValueError as exc:
            messagebox.showerror("ConnectBox", str(exc))
            return

        host = self.receive_host_var.get().strip() or "0.0.0.0"
        save_dir = Path(self.receive_save_dir_var.get().strip() or "received")
        self._reset_progress("receive")
        self._set_status("receive", "active", "서버 대기 중")
        self.receive_start_button.configure(state=tk.DISABLED)

        def worker() -> None:
            try:
                saved_paths = run_server(
                    host,
                    port,
                    save_dir,
                    log_callback=lambda message: self._enqueue_log("receive", message),
                    progress_callback=lambda event: self._enqueue_progress(
                        "receive", event
                    ),
                )
                self._enqueue_log("receive", f"완료: {len(saved_paths)}개 파일 수신")
                self.events.put(("status", "receive", ("success", "수신 완료")))
            except Exception as exc:
                self._enqueue_log("receive", f"오류: {exc}")
                self.events.put(("status", "receive", ("error", "수신 오류")))
            finally:
                self.events.put(("done", "receive", None))

        self.receive_worker = threading.Thread(target=worker, daemon=True)
        self.receive_worker.start()

    def _start_send(self) -> None:
        if self.send_worker is not None and self.send_worker.is_alive():
            messagebox.showinfo("ConnectBox", "전송이 이미 실행 중입니다.")
            return
        if not self.send_files and self.send_folder is None:
            messagebox.showwarning("ConnectBox", "보낼 파일 또는 폴더를 선택하세요.")
            return

        try:
            port = self._parse_port(self.send_port_var.get())
        except ValueError as exc:
            messagebox.showerror("ConnectBox", str(exc))
            return

        host = self.send_host_var.get().strip() or "127.0.0.1"
        files = list(self.send_files)
        folder = self.send_folder
        self._reset_progress("send")
        self._set_status("send", "active", "전송 중")
        self.send_button.configure(state=tk.DISABLED)

        def worker() -> None:
            try:
                send_paths(
                    host,
                    port,
                    file_paths=files,
                    folder_path=folder,
                    log_callback=lambda message: self._enqueue_log("send", message),
                    progress_callback=lambda event: self._enqueue_progress(
                        "send", event
                    ),
                )
                self._enqueue_log("send", "전송 완료")
                self.events.put(("status", "send", ("success", "전송 완료")))
            except Exception as exc:
                self._enqueue_log("send", f"오류: {exc}")
                self.events.put(("status", "send", ("error", "전송 오류")))
            finally:
                self.events.put(("done", "send", None))

        self.send_worker = threading.Thread(target=worker, daemon=True)
        self.send_worker.start()

    def _parse_port(self, value: str) -> int:
        try:
            port = int(value)
        except ValueError as exc:
            raise ValueError("Port는 숫자여야 합니다.") from exc
        if not 1 <= port <= 65535:
            raise ValueError("Port는 1~65535 범위여야 합니다.")
        return port

    def _enqueue_log(self, area: str, message: str) -> None:
        self.events.put(("log", area, message))

    def _enqueue_progress(self, area: str, event: dict[str, object]) -> None:
        self.events.put(("progress", area, event))

    def _poll_events(self) -> None:
        while True:
            try:
                event_type, area, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if event_type == "log":
                self._append_log(area, str(payload))
            elif event_type == "progress":
                self._update_progress(area, payload)  # type: ignore[arg-type]
            elif event_type == "status":
                style_name, text = payload  # type: ignore[misc]
                self._set_status(area, str(style_name), str(text))
            elif event_type == "done":
                if area == "send":
                    self.send_button.configure(state=tk.NORMAL)
                elif area == "receive":
                    self.receive_start_button.configure(state=tk.NORMAL)

        self.after(100, self._poll_events)

    def _set_status(self, area: str, status: str, text: str) -> None:
        global_text = {
            "idle": "● Ready",
            "active": "● Receiving" if area == "receive" else "● Sending",
            "success": "● Complete",
            "error": "● Error",
        }.get(status, "● Ready")
        badge_bg, badge_fg = self._status_colors(status)
        self.global_status_label.configure(text=global_text, bg=badge_bg, fg=badge_fg)

        local_label = self.receive_status_label if area == "receive" else self.send_status_label
        local_label.configure(text=global_text, bg=badge_bg, fg=badge_fg)

        widgets = self.progress_widgets.get(area)
        if widgets:
            state_value = widgets["state_value"]
            if isinstance(state_value, tk.Label):
                state_value.configure(text=text)

        if status == "success":
            self._append_log(area, f"✅ {text} — 상태 배지가 Complete로 변경되었습니다.", "success")
            self.bell()
            self.after(150, lambda message=text: messagebox.showinfo("ConnectBox", message))
        elif status == "error":
            self._append_log(area, f"⚠ {text} — 로그를 확인하세요.", "error")

    def _status_colors(self, status: str) -> tuple[str, str]:
        if status == "active":
            return ACTIVE_BG, PRIMARY_DARK
        if status == "success":
            return SUCCESS_BG, SUCCESS_DARK
        if status == "error":
            return ERROR_BG, DANGER_DARK
        return IDLE_BG, PRIMARY

    def _append_log(self, area: str, message: str, emphasis: str | None = None) -> None:
        log_widget = self.send_log if area == "send" else self.receive_log
        tag = emphasis or self._log_tag_for_message(message)
        timestamp = time.strftime("%H:%M:%S")

        log_widget.configure(state=tk.NORMAL)
        log_widget.insert(tk.END, f"[{timestamp}] ", "time")
        log_widget.insert(tk.END, message + "\n", tag)
        log_widget.see(tk.END)
        log_widget.configure(state=tk.DISABLED)

    def _log_tag_for_message(self, message: str) -> str:
        lower = message.lower()
        if "오류" in message or "error" in lower or "failed" in lower:
            return "error"
        if "완료" in message or "complete" in lower or "success" in lower:
            return "success"
        return "info"

    def _clear_log(self, area: str) -> None:
        log_widget = self.send_log if area == "send" else self.receive_log
        log_widget.configure(state=tk.NORMAL)
        log_widget.delete("1.0", tk.END)
        log_widget.configure(state=tk.DISABLED)

    def _reset_progress(self, area: str) -> None:
        widgets = self.progress_widgets[area]
        for key in ("current_bar", "total_bar"):
            bar = widgets[key]
            if isinstance(bar, ttk.Progressbar):
                bar["value"] = 0

        label_values = {
            "current_label": "현재 파일: 0%",
            "total_label": "전체 진행률: 0%",
            "file_value": "대기",
            "speed_value": "대기",
            "state_value": "준비됨",
        }
        for key, value in label_values.items():
            widget = widgets[key]
            if isinstance(widget, tk.Label):
                widget.configure(text=value)

        now = time.monotonic()
        self.progress_trackers[area] = {"time": now, "bytes": 0, "start_time": now}

    def _update_progress(self, area: str, event: dict[str, object]) -> None:
        current = int(event["current_bytes"])
        current_total = int(event["current_total"])
        total_bytes = int(event["total_bytes"])
        total_size = int(event["total_size"])
        file_index = int(event["file_index"])
        file_count = int(event["file_count"])
        relative_path = str(event["relative_path"])

        current_percent = 100 if current_total == 0 else int(current * 100 / current_total)
        total_percent = 100 if total_size == 0 else int(total_bytes * 100 / total_size)
        speed_text = self._calculate_speed(area, total_bytes)

        widgets = self.progress_widgets[area]
        current_bar = widgets["current_bar"]
        total_bar = widgets["total_bar"]
        if isinstance(current_bar, ttk.Progressbar):
            current_bar["value"] = current_percent
        if isinstance(total_bar, ttk.Progressbar):
            total_bar["value"] = total_percent

        self._configure_label(
            widgets["current_label"],
            (
                f"현재 파일 [{file_index}/{file_count}] {relative_path}: "
                f"{current_percent}% "
                f"({format_bytes(current)} / {format_bytes(current_total)})"
            ),
        )
        self._configure_label(
            widgets["total_label"],
            (
                f"전체 진행률: {total_percent}% "
                f"({format_bytes(total_bytes)} / {format_bytes(total_size)})"
            ),
        )
        self._configure_label(widgets["file_value"], f"{file_index}/{file_count}")
        self._configure_label(widgets["speed_value"], speed_text)
        self._configure_label(widgets["state_value"], "진행 중")

    def _configure_label(self, widget: tk.Widget | ttk.Progressbar, text: str) -> None:
        if isinstance(widget, tk.Label):
            widget.configure(text=text)

    def _calculate_speed(self, area: str, total_bytes: int) -> str:
        now = time.monotonic()
        tracker = self.progress_trackers[area]
        last_time = tracker.get("time")
        last_bytes = int(tracker.get("bytes") or 0)
        tracker["time"] = now
        tracker["bytes"] = total_bytes

        start_time = tracker.get("start_time")
        if not isinstance(last_time, float):
            return self._calculate_average_speed(start_time, now, total_bytes)
        elapsed = now - last_time
        delta = total_bytes - last_bytes
        if elapsed <= 0 or delta <= 0:
            return self._calculate_average_speed(start_time, now, total_bytes)
        return f"{format_bytes(int(delta / elapsed))}/s"

    def _calculate_average_speed(
        self,
        start_time: float | int | None,
        now: float,
        total_bytes: int,
    ) -> str:
        if not isinstance(start_time, float):
            return "계산 중"
        elapsed = now - start_time
        if elapsed <= 0 or total_bytes <= 0:
            return "계산 중"
        return f"{format_bytes(int(total_bytes / elapsed))}/s"


def main() -> None:
    app = ConnectBoxApp()
    app.mainloop()


if __name__ == "__main__":
    main()
