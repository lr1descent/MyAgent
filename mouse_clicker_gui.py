import ctypes
import random
import tkinter as tk
from tkinter import messagebox
from ctypes.util import find_library


class MacMouseClicker:
    """Use macOS CoreGraphics to send a left mouse click."""

    KCG_EVENT_LEFT_MOUSE_DOWN = 1
    KCG_EVENT_LEFT_MOUSE_UP = 2
    KCG_MOUSE_BUTTON_LEFT = 0

    def __init__(self) -> None:
        framework_path = find_library("ApplicationServices")
        if not framework_path:
            raise RuntimeError("无法加载 ApplicationServices，当前系统可能不是 macOS。")

        self.core_graphics = ctypes.cdll.LoadLibrary(framework_path)
        self.core_graphics.CGEventCreateMouseEvent.restype = ctypes.c_void_p
        self.core_graphics.CGEventCreateMouseEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            CGPoint,
            ctypes.c_uint32,
        ]
        self.core_graphics.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
        self.core_graphics.CFRelease.argtypes = [ctypes.c_void_p]

    def left_click(self, x: int, y: int) -> None:
        point = CGPoint(float(x), float(y))
        mouse_down = self.core_graphics.CGEventCreateMouseEvent(
            None,
            self.KCG_EVENT_LEFT_MOUSE_DOWN,
            point,
            self.KCG_MOUSE_BUTTON_LEFT,
        )
        mouse_up = self.core_graphics.CGEventCreateMouseEvent(
            None,
            self.KCG_EVENT_LEFT_MOUSE_UP,
            point,
            self.KCG_MOUSE_BUTTON_LEFT,
        )

        try:
            self.core_graphics.CGEventPost(0, mouse_down)
            self.core_graphics.CGEventPost(0, mouse_up)
        finally:
            self.core_graphics.CFRelease(mouse_down)
            self.core_graphics.CFRelease(mouse_up)


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class MouseClickerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("随机点击器")
        self.root.geometry("420x260")
        self.root.resizable(False, False)

        self.clicker = MacMouseClicker()
        self.running = False
        self.job_id: str | None = None
        self.anchor_point: tuple[int, int] | None = None

        self.select_overlay: tk.Toplevel | None = None

        self.status_var = tk.StringVar(value="状态：未启动")
        self.point_var = tk.StringVar(value="点击点位：未设置")
        self.interval_var = tk.StringVar(value="下一次点击间隔：未调度")

        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, padx=18, pady=18)
        container.pack(fill="both", expand=True)

        title = tk.Label(container, text="鼠标随机点击器", font=("PingFang SC", 18, "bold"))
        title.pack(anchor="w")

        desc = tk.Label(
            container,
            text="先点击准星按钮锚定一个点，再启动任务。点击间隔 = 10 秒 + 1~10 秒随机数。",
            justify="left",
            fg="#444444",
        )
        desc.pack(anchor="w", pady=(8, 18))

        action_row = tk.Frame(container)
        action_row.pack(fill="x")

        anchor_btn = tk.Button(
            action_row,
            text="◎ 锚定点位",
            width=12,
            command=self.enter_point_selection,
        )
        anchor_btn.pack(side="left")

        start_btn = tk.Button(
            action_row,
            text="启动",
            width=10,
            bg="#1f9d55",
            fg="white",
            command=self.start_clicking,
        )
        start_btn.pack(side="left", padx=12)

        stop_btn = tk.Button(
            action_row,
            text="停止",
            width=10,
            bg="#d64545",
            fg="white",
            command=self.stop_clicking,
        )
        stop_btn.pack(side="left")

        info_frame = tk.LabelFrame(container, text="运行信息", padx=12, pady=12)
        info_frame.pack(fill="both", expand=True, pady=(18, 0))

        tk.Label(info_frame, textvariable=self.status_var, anchor="w", justify="left").pack(fill="x")
        tk.Label(info_frame, textvariable=self.point_var, anchor="w", justify="left").pack(fill="x", pady=(8, 0))
        tk.Label(info_frame, textvariable=self.interval_var, anchor="w", justify="left").pack(fill="x", pady=(8, 0))

        tips = tk.Label(
            container,
            text="提示：首次运行如无法点击，请在 macOS“系统设置 -> 隐私与安全性 -> 辅助功能”中给 Python/终端授权。",
            justify="left",
            fg="#666666",
            wraplength=380,
        )
        tips.pack(anchor="w", pady=(12, 0))

    def enter_point_selection(self) -> None:
        if self.running:
            self.stop_clicking()

        self.status_var.set("状态：等待锚定点击点位")
        self.root.withdraw()

        overlay = tk.Toplevel(self.root)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-alpha", 0.25)
        overlay.attributes("-topmost", True)
        overlay.configure(bg="black", cursor="crosshair")
        overlay.focus_force()

        canvas = tk.Canvas(overlay, bg="black", highlightthickness=0, cursor="crosshair")
        canvas.pack(fill="both", expand=True)

        hint = canvas.create_text(
            overlay.winfo_screenwidth() // 2,
            60,
            text="在目标位置单击鼠标左键完成锚定；按 ESC 取消",
            fill="white",
            font=("PingFang SC", 20, "bold"),
        )
        _ = hint

        canvas.bind("<Button-1>", self._on_point_selected)
        overlay.bind("<Escape>", self._cancel_point_selection)

        self.select_overlay = overlay

    def _on_point_selected(self, event: tk.Event) -> None:
        x, y = event.x, event.y
        self.anchor_point = (x, y)
        self.point_var.set(f"点击点位：({x}, {y})")
        self.status_var.set("状态：点位已设置，可启动")
        self._close_overlay()

    def _cancel_point_selection(self, _event: tk.Event | None = None) -> None:
        self.status_var.set("状态：已取消点位选择")
        self._close_overlay()

    def _close_overlay(self) -> None:
        if self.select_overlay is not None:
            self.select_overlay.destroy()
            self.select_overlay = None

        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(200, lambda: self.root.attributes("-topmost", False))

    def start_clicking(self) -> None:
        if not self.anchor_point:
            messagebox.showwarning("未设置点位", "请先点击“◎ 锚定点位”并在屏幕上单击一个目标点。")
            return

        if self.running:
            return

        self.running = True
        self.status_var.set("状态：运行中")
        self._schedule_next_click()

    def stop_clicking(self) -> None:
        self.running = False
        if self.job_id is not None:
            self.root.after_cancel(self.job_id)
            self.job_id = None
        self.status_var.set("状态：已停止")
        self.interval_var.set("下一次点击间隔：未调度")

    def _schedule_next_click(self) -> None:
        if not self.running:
            return

        interval_seconds = 10 + random.randint(1, 10)
        self.interval_var.set(f"下一次点击间隔：{interval_seconds} 秒")
        self.job_id = self.root.after(interval_seconds * 1000, self._perform_click)

    def _perform_click(self) -> None:
        if not self.running or not self.anchor_point:
            return

        x, y = self.anchor_point

        try:
            self.clicker.left_click(x, y)
            self.status_var.set(f"状态：已点击坐标 ({x}, {y})")
        except Exception as exc:
            self.stop_clicking()
            messagebox.showerror("点击失败", f"模拟点击失败：{exc}")
            return

        self._schedule_next_click()


def main() -> None:
    root = tk.Tk()
    app = MouseClickerApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop_clicking(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
