"""Tkinter GUI for the final ConnectBox presentation version."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from client.client_main import send_paths
from common.progress import format_bytes
from server.server_main import run_server


class ConnectBoxApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ConnectBox")
        self.geometry("780x620")

        self.events: queue.Queue[tuple[str, str, object]] = queue.Queue()
        self.send_files: list[Path] = []
        self.send_folder: Path | None = None
        self.send_worker: threading.Thread | None = None
        self.receive_worker: threading.Thread | None = None

        self._build_widgets()
        self.after(100, self._poll_events)

    def _build_widgets(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.receive_frame = ttk.Frame(notebook, padding=10)
        self.send_frame = ttk.Frame(notebook, padding=10)
        notebook.add(self.receive_frame, text="받기 모드")
        notebook.add(self.send_frame, text="보내기 모드")

        self._build_receive_tab()
        self._build_send_tab()

    def _build_receive_tab(self) -> None:
        self.receive_host_var = tk.StringVar(value="0.0.0.0")
        self.receive_port_var = tk.StringVar(value="5001")
        self.receive_save_dir_var = tk.StringVar(value="received")

        form = ttk.LabelFrame(self.receive_frame, text="수신 설정", padding=10)
        form.pack(fill=tk.X)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Host").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.receive_host_var).grid(
            row=0, column=1, sticky="ew", padx=8, pady=4
        )
        ttk.Label(form, text="Port").grid(row=0, column=2, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.receive_port_var, width=10).grid(
            row=0, column=3, sticky="w", padx=8, pady=4
        )

        ttk.Label(form, text="저장 폴더").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.receive_save_dir_var).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=8, pady=4
        )
        ttk.Button(form, text="찾기", command=self._choose_receive_dir).grid(
            row=1, column=3, sticky="ew", padx=8, pady=4
        )

        self.receive_start_button = ttk.Button(
            self.receive_frame,
            text="받기 서버 시작",
            command=self._start_receive_server,
        )
        self.receive_start_button.pack(anchor="e", pady=10)

        self.receive_current_label = ttk.Label(self.receive_frame, text="현재 파일: 0%")
        self.receive_current_label.pack(anchor="w")
        self.receive_current_bar = ttk.Progressbar(
            self.receive_frame, maximum=100, mode="determinate"
        )
        self.receive_current_bar.pack(fill=tk.X, pady=(2, 8))

        self.receive_total_label = ttk.Label(self.receive_frame, text="전체: 0%")
        self.receive_total_label.pack(anchor="w")
        self.receive_total_bar = ttk.Progressbar(
            self.receive_frame, maximum=100, mode="determinate"
        )
        self.receive_total_bar.pack(fill=tk.X, pady=(2, 8))

        self.receive_log = self._build_log(self.receive_frame)

    def _build_send_tab(self) -> None:
        self.send_host_var = tk.StringVar(value="127.0.0.1")
        self.send_port_var = tk.StringVar(value="5001")

        form = ttk.LabelFrame(self.send_frame, text="송신 설정", padding=10)
        form.pack(fill=tk.X)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="서버 IP").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.send_host_var).grid(
            row=0, column=1, sticky="ew", padx=8, pady=4
        )
        ttk.Label(form, text="Port").grid(row=0, column=2, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.send_port_var, width=10).grid(
            row=0, column=3, sticky="w", padx=8, pady=4
        )

        buttons = ttk.Frame(self.send_frame)
        buttons.pack(fill=tk.X, pady=10)
        ttk.Button(buttons, text="파일 추가", command=self._add_send_files).pack(
            side=tk.LEFT
        )
        ttk.Button(buttons, text="폴더 선택", command=self._choose_send_folder).pack(
            side=tk.LEFT, padx=8
        )
        ttk.Button(buttons, text="선택 초기화", command=self._clear_send_selection).pack(
            side=tk.LEFT
        )

        selection_frame = ttk.LabelFrame(self.send_frame, text="보낼 항목", padding=8)
        selection_frame.pack(fill=tk.BOTH, expand=False)
        self.send_listbox = tk.Listbox(selection_frame, height=7)
        self.send_listbox.pack(fill=tk.BOTH, expand=True)

        self.send_button = ttk.Button(
            self.send_frame,
            text="전송 시작",
            command=self._start_send,
        )
        self.send_button.pack(anchor="e", pady=10)

        self.send_current_label = ttk.Label(self.send_frame, text="현재 파일: 0%")
        self.send_current_label.pack(anchor="w")
        self.send_current_bar = ttk.Progressbar(
            self.send_frame, maximum=100, mode="determinate"
        )
        self.send_current_bar.pack(fill=tk.X, pady=(2, 8))

        self.send_total_label = ttk.Label(self.send_frame, text="전체: 0%")
        self.send_total_label.pack(anchor="w")
        self.send_total_bar = ttk.Progressbar(
            self.send_frame, maximum=100, mode="determinate"
        )
        self.send_total_bar.pack(fill=tk.X, pady=(2, 8))

        self.send_log = self._build_log(self.send_frame)

    def _build_log(self, parent: ttk.Frame) -> tk.Text:
        frame = ttk.LabelFrame(parent, text="상태 로그", padding=6)
        frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        text = tk.Text(frame, height=10, state="disabled", wrap="word")
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return text

    def _choose_receive_dir(self) -> None:
        selected = filedialog.askdirectory(title="받은 파일 저장 폴더 선택")
        if selected:
            self.receive_save_dir_var.set(selected)

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
            self.send_listbox.insert(tk.END, f"파일: {path}")
        if self.send_folder is not None:
            self.send_listbox.insert(tk.END, f"폴더: {self.send_folder}")

    def _start_receive_server(self) -> None:
        if self.receive_worker is not None and self.receive_worker.is_alive():
            messagebox.showinfo("ConnectBox", "받기 서버가 이미 실행 중입니다.")
            return

        try:
            port = self._parse_port(self.receive_port_var.get())
        except ValueError as exc:
            messagebox.showerror("ConnectBox", str(exc))
            return

        host = self.receive_host_var.get().strip() or "0.0.0.0"
        save_dir = Path(self.receive_save_dir_var.get().strip() or "received")
        self._reset_progress("receive")
        self.receive_start_button.configure(state="disabled")

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
            except Exception as exc:
                self._enqueue_log("receive", f"오류: {exc}")
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
        self.send_button.configure(state="disabled")

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
            except Exception as exc:
                self._enqueue_log("send", f"오류: {exc}")
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
            elif event_type == "done":
                if area == "send":
                    self.send_button.configure(state="normal")
                elif area == "receive":
                    self.receive_start_button.configure(state="normal")

        self.after(100, self._poll_events)

    def _append_log(self, area: str, message: str) -> None:
        log_widget = self.send_log if area == "send" else self.receive_log
        log_widget.configure(state="normal")
        log_widget.insert(tk.END, message + "\n")
        log_widget.see(tk.END)
        log_widget.configure(state="disabled")

    def _reset_progress(self, area: str) -> None:
        bars = (
            (self.send_current_bar, self.send_total_bar)
            if area == "send"
            else (self.receive_current_bar, self.receive_total_bar)
        )
        labels = (
            (self.send_current_label, self.send_total_label)
            if area == "send"
            else (self.receive_current_label, self.receive_total_label)
        )
        for bar in bars:
            bar["value"] = 0
        labels[0].configure(text="현재 파일: 0%")
        labels[1].configure(text="전체: 0%")

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

        if area == "send":
            current_bar = self.send_current_bar
            total_bar = self.send_total_bar
            current_label = self.send_current_label
            total_label = self.send_total_label
        else:
            current_bar = self.receive_current_bar
            total_bar = self.receive_total_bar
            current_label = self.receive_current_label
            total_label = self.receive_total_label

        current_bar["value"] = current_percent
        total_bar["value"] = total_percent
        current_label.configure(
            text=(
                f"현재 파일 [{file_index}/{file_count}] {relative_path}: "
                f"{current_percent}% "
                f"({format_bytes(current)} / {format_bytes(current_total)})"
            )
        )
        total_label.configure(
            text=(
                f"전체: {total_percent}% "
                f"({format_bytes(total_bytes)} / {format_bytes(total_size)})"
            )
        )


def main() -> None:
    app = ConnectBoxApp()
    app.mainloop()


if __name__ == "__main__":
    main()
