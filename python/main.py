"""Gesture Exhibit - detection entry point.

Pipeline per frame:
    camera -> HandLandmarker -> active-player selection -> gesture FSM
           -> homography map -> One Euro smoothing -> WebSocket -> browser

Usage (run from this 'python/' folder):
    python download_model.py        # once, fetch the model
    python main.py                  # run the detector
    python main.py --calibrate      # 4-corner projector calibration
    python main.py --no-preview     # headless (no OpenCV window)
    python main.py --config foo.json

Hotkeys in the preview window:  ESC = quit,  C = recalibrate.
Same two actions (recalibrate, camera settings) are also reachable without a
preview window, from the browser's in-game settings tab (web/js/settings.js)
over the WebSocket command channel handled in net/ws_sender.py.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Depo kökünü sys.path'e al ki `import paths` hem `cd python && python main.py`
# ile doğrudan çalıştırınca hem de matematik.py üzerinden çalışsın. python/ bir
# paket değil (modüller birbirini düz isimle import ediyor), bu yüzden kökü
# eklemenin başka yolu yok.
_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

import cv2

import paths

from config import load_config
from camera import create_camera
from detection import HandRecognizer
from selection import ActivePlayerSelector
from gesture import GestureFSM, FIST
from smoothing import CursorSmoother
from mapping import Homography
from mapping.calibrate import run_calibration
from net import create_sender

_QUIT = "quit"
_RECALIBRATE = "recalibrate"
_CAMERA_SETTINGS = "camera_settings"

# MediaPipe Hands 21-point skeleton topology (drawn in the preview overlay).
_HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),            # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),            # index
    (5, 9), (9, 10), (10, 11), (11, 12),       # middle
    (9, 13), (13, 14), (14, 15), (15, 16),     # ring
    (13, 17), (17, 18), (18, 19), (19, 20),    # pinky
    (0, 17),                                   # palm base
)


def _draw_skeleton(bgr, landmarks_px, color):
    """Draw the 21-point hand skeleton: connection lines + joint dots."""
    n = len(landmarks_px)
    for a, b in _HAND_CONNECTIONS:
        if a < n and b < n:
            cv2.line(bgr, landmarks_px[a], landmarks_px[b], color, 2, cv2.LINE_AA)
    for p in landmarks_px:
        cv2.circle(bgr, p, 3, color, -1, cv2.LINE_AA)


class MonotonicMs:
    """Strictly increasing millisecond clock for detect_async timestamps."""
    def __init__(self):
        self._last = -1

    def now(self) -> int:
        ts = int(time.monotonic() * 1000)
        if ts <= self._last:
            ts = self._last + 1
        self._last = ts
        return ts


def _draw_overlay(bgr, cfg, observations, sel, committed, present,
                  mapped, fps, calibrated, cam_fps=0.0, inf_fps=0.0):
    h, w = bgr.shape[:2]
    ap = cfg.active_player

    # ROI rectangle (interaction zone).
    cv2.rectangle(bgr,
                  (int(ap.roi_x_min * w), int(ap.roi_y_min * h)),
                  (int(ap.roi_x_max * w), int(ap.roi_y_max * h)),
                  (80, 80, 80), 1)

    locked = sel.locked
    for obs in observations:
        xs = [p[0] for p in obs.landmarks_px]
        ys = [p[1] for p in obs.landmarks_px]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        is_locked = locked is not None and obs is locked
        color = (0, 255, 0) if is_locked else (130, 130, 130)
        # Hand skeleton: fist -> magenta, open -> the lock colour above.
        skel_color = (255, 0, 255) if obs.gesture == "Closed_Fist" else color
        _draw_skeleton(bgr, obs.landmarks_px, skel_color)
        cv2.rectangle(bgr, (x1, y1), (x2, y2), color, 2 if is_locked else 1)
        label = f"{obs.gesture} {obs.gesture_score:.2f} sz{obs.span01:.2f}"
        cv2.putText(bgr, label, (x1, max(y1 - 8, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        if is_locked:
            cx, cy = int(obs.centroid_px[0]), int(obs.centroid_px[1])
            cv2.circle(bgr, (cx, cy), 6, (0, 255, 0), -1)

    # Status bar.
    state_color = (0, 0, 255) if committed == FIST else (0, 200, 255)
    lines = [
        f"loop {fps:4.1f}  cam {cam_fps:4.1f}  infer {inf_fps:4.1f} fps   "
        f"hands {len(observations)}   "
        f"{'CALIBRATED' if calibrated else 'NOT CALIBRATED (raw coords)'}",
        f"present={int(present)}  state={committed}  "
        f"mapped=({mapped[0]:.3f},{mapped[1]:.3f})",
        "ESC quit   C recalibrate",
    ]
    for i, line in enumerate(lines):
        cv2.putText(bgr, line, (12, 24 + 22 * i),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    state_color if i == 1 else (255, 255, 255), 2)


def run_detector(cfg, preview: bool) -> str:
    cam = create_camera(cfg)
    recognizer = HandRecognizer(cfg)
    homography = Homography(cfg)
    # Saved calibration is tied to the camera resolution + mirroring it was built
    # with; if either changed, the px coords no longer line up -> warn loudly.
    homography.warn_if_environment_changed(cam.resolution, cfg.camera.flip_horizontal)
    selector = ActivePlayerSelector(cfg)
    fsm = GestureFSM(cfg)
    smoother = CursorSmoother(cfg.smoothing.min_cutoff, cfg.smoothing.beta,
                              cfg.smoothing.d_cutoff)
    sender = create_sender(cfg)   # WebSocket köprüsü (net/ws_sender.py) — tek tasiyici
    clock = MonotonicMs()

    frame_budget = 1.0 / float(cfg.net.send_rate_hz)
    win = cfg.preview.window_name
    if preview:
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    last_xy = (0.5, 0.5)
    committed = "searching"
    mapped = (0.5, 0.5)
    present = False
    observations = []
    sel = None
    last_rid = -1
    fps = 0.0
    fps_t = time.monotonic()
    # Gerçek darboğazı görmek için üç ayrı hız: döngü (60 Hz'e kilitli, yanıltıcı),
    # kamera kare hızı ve MediaPipe sonuç hızı (= merceğin gerçek güncelleme hızı).
    stat_t = time.monotonic()
    stat_cam = 0
    stat_inf = 0
    cam_fps = 0.0
    inf_fps = 0.0

    print(f"[detector] running. transport=ws  WS -> {cfg.net.ws_host}:{cfg.net.ws_port}  "
          f"calibrated={homography.is_calibrated}")
    try:
        while True:
            loop_start = time.monotonic()

            frame = cam.read()
            if frame is None:
                # Transient grab failure; keep the cursor parked, don't busy-spin.
                sender.send_absent(*last_xy)
                if preview and (cv2.waitKey(1) & 0xFF) == 27:
                    return _QUIT
                time.sleep(0.01)
                continue

            stat_cam += 1
            recognizer.submit(frame.rgb, clock.now())

            # Run the pipeline only on a NEW inference result. The loop spins at
            # ~60 Hz but MediaPipe completes only ~20-30 Hz; feeding One Euro (and
            # ticking the selector/FSM frame counters) with duplicate frames is what
            # defeated the smoothing and made the lens step. We still emit a
            # packet every loop (~60 Hz heartbeat) below so the browser never starves.
            rid = recognizer.result_id
            if rid != last_rid:
                last_rid = rid
                stat_inf += 1
                observations = recognizer.get_observations()
                sel = selector.update(observations)

                if sel.just_acquired:
                    smoother.reset()
                    fsm.reset()
                if sel.just_released:
                    fsm.reset()
                    smoother.reset()

                if sel.locked is not None:
                    committed = fsm.update(sel.locked.gesture)
                    raw = homography.map_point(
                        sel.locked.centroid_px[0], sel.locked.centroid_px[1],
                        sel.locked.centroid01)
                    t = time.monotonic()
                    mapped = smoother(t, raw[0], raw[1])
                    last_xy = mapped
                    present = True
                else:
                    committed = "searching"
                    present = False

            # ~60 Hz heartbeat; position only advances on a fresh inference.
            if present:
                sender.send_hand(mapped[0], mapped[1], True, committed)
            else:
                sender.send_absent(*last_xy)

            # FPS (EMA).
            now = time.monotonic()
            inst = 1.0 / max(now - fps_t, 1e-6)
            fps = 0.9 * fps + 0.1 * inst if fps else inst
            fps_t = now
            if now - stat_t >= 2.0:
                cam_fps = stat_cam / (now - stat_t)
                inf_fps = stat_inf / (now - stat_t)
                stat_cam = stat_inf = 0
                stat_t = now
                if not preview:
                    print(f"[stat] cam {cam_fps:4.1f} fps  infer {inf_fps:4.1f} fps  "
                          f"hands {len(observations)}", flush=True)

            if preview:
                bgr = cv2.cvtColor(frame.rgb, cv2.COLOR_RGB2BGR)
                _draw_overlay(bgr, cfg, observations, sel, committed, present,
                              mapped, fps, homography.is_calibrated,
                              cam_fps, inf_fps)
                cv2.imshow(win, bgr)
                key = cv2.waitKey(1) & 0xFF
                if key == 27:               # ESC
                    return _QUIT
                if key in (ord('c'), ord('C')):
                    return _RECALIBRATE

            # Tarayıcıdaki ayarlar sekmesinden gelen komutlar (2026-09-16):
            # önizleme penceresi olmasa bile (sergi = --no-preview) çalışmalı,
            # bu yüzden preview bloğunun DIŞINDA, her karede yoklanır.
            poll = getattr(sender, "poll_commands", None)
            if poll is not None:
                for cmd in poll():
                    if cmd == "kalibrasyon":
                        return _RECALIBRATE
                    if cmd == "kamera_ayarlari":
                        return _CAMERA_SETTINGS

            # Rate cap: never flood the browser faster than its render rate.
            sleep = frame_budget - (time.monotonic() - loop_start)
            if sleep > 0:
                time.sleep(sleep)
    finally:
        cam.close()
        recognizer.close()
        _close = getattr(sender, "close", None)
        if callable(_close):
            _close()   # WS sunucusunu kapat / portu serbest bırak (recalibrate yeniden-başlatması için)
        if preview:
            cv2.destroyAllWindows()


def _kamera_ayarlarini_ac() -> None:
    """Oyun içi 'Kamera Ayarları' komutuyla tetiklenir.

    run_detector()'ın finally bloğu kamerayı zaten serbest bırakmış olur
    (bu fonksiyon ancak run_detector dönünce çağrılır) — camera_settings'in
    kendi cv2.VideoCapture'ı ile çakışma yok. Pencere kapanınca config.json
    güncellenmiş olabilir; çağıran taraf cfg'yi yeniden yüklemeli.
    """
    try:
        import camera_settings
        camera_settings.run_gui()
    except Exception as exc:  # noqa: BLE001 — sergi çökmesin, sadece logla
        print(f"[main] kamera ayarlari penceresi acilamadi: {exc!r}")


def _yollari_coz(cfg) -> None:
    """config.json'daki göreli yolları mutlaklaştır.

    Bu dosyadaki yollar eskiden çalışma dizinine göre çözülüyordu, yani dedektör
    ancak `cd python` yapıldıktan sonra çalışıyordu. matematik.py depo kökünden,
    EXE ise Program Files'tan başlatılıyor; ikisinde de CWD farklı. Yolların
    sahibi artık paths.py.
    """
    mp = cfg.detection.model_path
    if not os.path.isabs(mp):
        cfg.detection.model_path = paths.model_path(os.path.basename(mp))
    cfg.calibration.file = paths.calib_path(cfg.calibration.file)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Gesture Exhibit detector")
    parser.add_argument("--config", default=None,
                        help="varsayilan: paths.config_path()")
    parser.add_argument("--calibrate", action="store_true",
                        help="run 4-corner projector calibration and exit")
    parser.add_argument("--no-preview", action="store_true",
                        help="run without the OpenCV preview window")
    parser.add_argument("--ws-port", type=int, default=None,
                        help="config.json'daki net.ws_port'u ez (matematik.py "
                             "bos port secip hem buraya hem tarayiciya bildirir)")
    args = parser.parse_args(argv)

    cfg = load_config(args.config or paths.config_path())
    _yollari_coz(cfg)

    # Port çakışırsa matematik.py boş bir tane seçer; dedektör ile tarayıcı aynı
    # porta bakmazsa köprü sessizce ölür (G0'da tam olarak bu görüldü).
    if args.ws_port is not None:
        net = cfg.get("net", None)
        if net is not None:
            net.ws_port = args.ws_port

    if args.calibrate:
        run_calibration(cfg)
        return 0

    preview = not args.no_preview
    while True:
        action = run_detector(cfg, preview)
        if action == _RECALIBRATE:
            run_calibration(cfg)
            continue   # restart detector; Homography reloads the new calib.json
        if action == _CAMERA_SETTINGS:
            _kamera_ayarlarini_ac()
            # camera_settings config.json'a yazdı; bellekteki cfg'yi tazele
            # (create_camera yalnızca cfg nesnesine bakar, dosyayı değil).
            cfg = load_config(args.config or paths.config_path())
            _yollari_coz(cfg)
            continue
        break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
