"""Reads the webcam, applies freeze/stutter effects, and outputs to a virtual camera."""

import random
import threading
import time
from enum import Enum

import cv2
import numpy as np
import pyvirtualcam


class Mode(Enum):
    LIVE = "live"
    FROZEN = "frozen"
    STUTTER = "stutter"


def preauthorize_camera(device_index: int = 0) -> bool:
    cap = cv2.VideoCapture(device_index, cv2.CAP_AVFOUNDATION)
    ok = cap.isOpened()
    cap.release()
    return ok


class CameraEngine:
    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self._mode = Mode.LIVE
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

        self._preview: np.ndarray | None = None
        self.error: str | None = None
        self.virtual_cam_name: str | None = None

        self._frozen_frame: np.ndarray | None = None
        self._held_frame: np.ndarray | None = None
        self._hold_until = 0.0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.error = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None

    @property
    def mode(self) -> Mode:
        return self._mode

    def set_mode(self, mode: Mode) -> None:
        with self._lock:
            if mode == self._mode:
                return
            self._mode = mode
            self._frozen_frame = None
            self._held_frame = None
            self._hold_until = 0.0

    def get_preview(self) -> np.ndarray | None:
        with self._lock:
            return None if self._preview is None else self._preview.copy()

    def _run(self) -> None:
        cap = cv2.VideoCapture(self.device_index, cv2.CAP_AVFOUNDATION)
        if not cap.isOpened():
            self.error = (
                "Could not open the webcam. Close other apps using the camera "
                "and check System Settings > Privacy & Security > Camera."
            )
            self._running = False
            return

        ok, frame = cap.read()
        if not ok or frame is None:
            self.error = "Webcam opened but returned no frames."
            cap.release()
            self._running = False
            return

        height, width = frame.shape[:2]
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        if not 5 <= fps <= 60:
            fps = 30

        try:
            with pyvirtualcam.Camera(
                width=width,
                height=height,
                fps=int(fps),
                fmt=pyvirtualcam.PixelFormat.BGR,
            ) as cam:
                self.virtual_cam_name = cam.device
                while self._running:
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        time.sleep(0.05)
                        continue

                    output = self._apply_effect(frame)
                    cam.send(output)

                    with self._lock:
                        self._preview = output
                    cam.sleep_until_next_frame()
        except RuntimeError as exc:
            self.error = (
                f"Virtual camera unavailable: {exc}\n\n"
                "Install OBS Studio (v30+), open it once, click "
                "'Start Virtual Camera', approve the system extension, then "
                "stop it, quit OBS and relaunch this app."
            )
        finally:
            cap.release()
            self._running = False

    def _apply_effect(self, frame: np.ndarray) -> np.ndarray:
        with self._lock:
            mode = self._mode

        if mode == Mode.LIVE:
            return frame

        if mode == Mode.FROZEN:
            if self._frozen_frame is None:
                self._frozen_frame = frame.copy()
            return self._frozen_frame

        now = time.monotonic()
        if now >= self._hold_until:
            if self._held_frame is None:
                self._held_frame = frame.copy()
            else:
                self._held_frame = None
            self._hold_until = now + random.uniform(0.1, 0.6)

        if self._held_frame is not None:
            return self._held_frame
        return frame
