"""Tkinter GUI for CamFreeze: preview, mode buttons, and keyboard shortcuts."""

import tkinter as tk

import cv2
from PIL import Image, ImageTk

from camera_engine import CameraEngine, Mode, preauthorize_camera

BG = "#16181d"
PANEL = "#1f2229"
FG = "#e6e8ee"
MUTED = "#8a8f9c"
ACCENT_LIVE = "#2ecc71"
ACCENT_FREEZE = "#4aa3ff"
ACCENT_STUTTER = "#ff9f43"

PREVIEW_W, PREVIEW_H = 560, 315


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.engine = CameraEngine()

        root.title("CamFreeze")
        root.configure(bg=BG)
        root.resizable(False, False)

        tk.Label(
            root, text="CamFreeze", font=("Helvetica", 22, "bold"), bg=BG, fg=FG
        ).pack(pady=(16, 2))
        tk.Label(
            root,
            text="Select \u201cOBS Virtual Camera\u201d as your camera in Zoom / Meet / Teams",
            font=("Helvetica", 11),
            bg=BG,
            fg=MUTED,
        ).pack(pady=(0, 12))

        self.preview = tk.Label(root, bg="black", width=PREVIEW_W, height=PREVIEW_H)
        self.preview.pack(padx=16)

        controls = tk.Frame(root, bg=BG)
        controls.pack(pady=16)

        self.btn_live = self._button(controls, "Live", ACCENT_LIVE, Mode.LIVE)
        self.btn_freeze = self._button(controls, "Freeze", ACCENT_FREEZE, Mode.FROZEN)
        self.btn_stutter = self._button(controls, "Stutter", ACCENT_STUTTER, Mode.STUTTER)
        self.btn_live.grid(row=0, column=0, padx=6)
        self.btn_freeze.grid(row=0, column=1, padx=6)
        self.btn_stutter.grid(row=0, column=2, padx=6)

        self.status = tk.Label(
            root, text="Starting camera\u2026", font=("Helvetica", 12), bg=BG, fg=MUTED,
            wraplength=PREVIEW_W, justify="center",
        )
        self.status.pack(pady=(0, 6))

        tk.Label(
            root,
            text="Shortcuts:  F = freeze    S = stutter    Space = back to live",
            font=("Helvetica", 10),
            bg=BG,
            fg=MUTED,
        ).pack(pady=(0, 14))

        root.bind("<KeyPress-f>", lambda _: self.set_mode(Mode.FROZEN))
        root.bind("<KeyPress-s>", lambda _: self.set_mode(Mode.STUTTER))
        root.bind("<space>", lambda _: self.set_mode(Mode.LIVE))
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._photo = None
        self.engine.start()
        self.refresh_buttons()
        self.tick()

    def _button(self, parent: tk.Frame, text: str, color: str, mode: Mode) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            font=("Helvetica", 14, "bold"),
            width=10,
            pady=8,
            bd=0,
            cursor="hand2",
            highlightthickness=2,
            highlightbackground=color,
            fg=color,
            bg=PANEL,
            activeforeground=FG,
            command=lambda: self.set_mode(mode),
        )

    def set_mode(self, mode: Mode) -> None:
        if mode != Mode.LIVE and self.engine.mode == mode:
            mode = Mode.LIVE
        self.engine.set_mode(mode)
        self.refresh_buttons()

    def refresh_buttons(self) -> None:
        mode = self.engine.mode
        for btn, m, color in (
            (self.btn_live, Mode.LIVE, ACCENT_LIVE),
            (self.btn_freeze, Mode.FROZEN, ACCENT_FREEZE),
            (self.btn_stutter, Mode.STUTTER, ACCENT_STUTTER),
        ):
            active = mode == m
            btn.configure(bg=color if active else PANEL, fg=BG if active else color)

    def tick(self) -> None:
        if self.engine.error:
            self.status.configure(text=self.engine.error, fg="#ff6b6b")
        else:
            frame = self.engine.get_preview()
            if frame is not None:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.flip(frame, 1)
                image = Image.fromarray(frame).resize((PREVIEW_W, PREVIEW_H))
                self._photo = ImageTk.PhotoImage(image)
                self.preview.configure(image=self._photo, width=PREVIEW_W, height=PREVIEW_H)

                labels = {
                    Mode.LIVE: ("LIVE \u2014 feed is passing through normally", ACCENT_LIVE),
                    Mode.FROZEN: ("FROZEN \u2014 viewers see a stuck frame", ACCENT_FREEZE),
                    Mode.STUTTER: ("STUTTERING \u2014 viewers see a laggy, broken feed", ACCENT_STUTTER),
                }
                text, color = labels[self.engine.mode]
                cam = self.engine.virtual_cam_name or "virtual camera"
                self.status.configure(text=f"{text}\nOutput: {cam}", fg=color)

        self.root.after(50, self.tick)

    def on_close(self) -> None:
        self.engine.stop()
        self.root.destroy()


def main() -> None:
    preauthorize_camera()
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
