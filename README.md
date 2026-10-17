# Matematik Avı (Math Hunt)

> A hands-free math game for museum wall projections: a glowing lens follows your hand, and a closed fist catches the right answer.

> 🇹🇷 **Türkçe özet:** Matematik Avı, bir web kamerası ile oynanan, duvara yansıtılan sergi oyunudur; oyuncu elini hareket ettirerek mercekle karanlıkta saklı sayıları bulur ve yumruk yaparak doğru cevabı yakalar. Oyun tarayıcıda (HTML/CSS/JS) çalışır, el takibi Python + MediaPipe ile yapılır ve WebSocket ile tarayıcıya aktarılır. Türkçe kurulum, kalibrasyon ve lisans ayrıntıları [`docs/INSTALL.md`](docs/INSTALL.md) ve [`docs/KIOSK.md`](docs/KIOSK.md) içindedir.

## Overview

Matematik Avı is an interactive exhibit designed for a wall projection. A math question appears at the top of a dark screen, and answer tokens are hidden in the dark. A circular **lens** controlled by the player's hand reveals the tokens it passes over; closing the hand into a **fist** selects the answer under the lens. There are three difficulty levels (kolay, orta, zor) and one two-minute round, with new questions arriving until time runs out.

The whole game (question generation, decoy placement, round flow, scoring, leaderboard) is a static web app in `web/`. A separate Python process does only the computer vision and streams hand state to the browser. On a machine with no camera, `Ctrl` switches input between hand tracking and the mouse, so the game can be tried on any desktop.

It is built for unattended exhibit use: kiosk launchers, a camera-and-projector calibration flow, offline fonts (no CDN), and a licensed Windows installer.

## Features

- **Gesture control.** MediaPipe hand landmarks, open-hand versus fist, debounced so a flickering gesture does not fire a selection.
- **Procedural questions.** Easy, medium and hard generators (multiplication, addition, squares and roots, fractions, and more) with numeric near-miss decoys and fraction glyphs; 36 tokens per round, 3 of them correct.
- **Friendly scoring.** Base score by difficulty with a growing combo multiplier; a wrong answer only resets the combo, it never subtracts points.
- **Active-player selection.** Tracks the nearest hand and holds the lock with hysteresis, so a bystander does not steal the cursor.
- **Projector calibration.** Nine-target (3x3) homography calibration with an on-screen verification step.
- **Mouse fallback.** `Ctrl` toggles hand and mouse input at runtime, with a visible "FARE MODU" (mouse mode) badge.
- **Self-contained front end.** Sci-fi HUD design, fonts bundled locally, WebSocket client that reconnects with exponential back-off.

## Architecture

```text
  Webcam -> [PYTHON: detector]                       [BROWSER: the game]
            MediaPipe HandLandmarker                  web/js/game.js
            -> active-player selection (lock-on)       + lens.js (lens)
            -> gesture FSM (open / fist)   WebSocket    + tokens.js (tokens, decoys)
            -> homography (camera -> wall) --/hand-->   + questions.js (questions)
            -> One Euro smoothing                       + leaderboard.js
```

- **Two processes, one message:** Python sends one JSON frame per camera frame, `{x, y, present, gesture}` (`python/net/ws_sender.py`).
- **The browser is the game, not just a renderer.** Game rules live in JavaScript, so they can change without touching the vision process.
- **`matematik.py` is the single entry point:** licence gate (frozen builds only), static server, kiosk browser window, then the detector on the main thread.
- The earlier Unity/OSC version has been removed entirely; only the WebSocket transport exists.

## Tech stack

| Layer | Technology |
|---|---|
| Game / UI | HTML, CSS, vanilla JavaScript (no build step), self-hosted fonts |
| Vision | Python, MediaPipe HandLandmarker, OpenCV, NumPy |
| Signal processing | Homography mapping, One Euro filter, gesture debounce FSM |
| Transport | `websockets` (JSON over WebSocket) |
| Packaging | Nuitka standalone build, Inno Setup installer |
| Licensing | Ed25519 signed licences, AES-256-GCM encrypted web pack, pywebview licence window |
| Tests | pytest, no hardware required |

## Engineering highlights

- **Frozen-build pitfalls found and locked down.** A build spike (see [`docs/plans/2026-09-12-G0-build-spike.md`](docs/plans/2026-09-12-G0-build-spike.md)) found two failures where the Nuitka build succeeds but the EXE is broken. In mediapipe 0.10.35 the tasks engine is a C library loaded through `ctypes` (`libmediapipe.dll`), invisible to static analysis and not picked up by package-data flags; the failure only appears on the first `HandLandmarker` call. In websockets 14+, sub-packages are resolved through `lazy_import`, so the server silently never started: no traceback, exit code 0, camera running at 30 fps, but no port open. Both flags are now explicit in `build.py`, and `tests/test_build.py` asserts them.
- **Verified end to end on the frozen EXE.** The spike measured 30 fps camera and 30 fps inference, and 180 frames received over the WebSocket in 6 seconds.
- **Licence gate before hardware.** A frozen build requires an offline licence before the camera is probed, a port is bound or the server starts. Activation is bound to a machine fingerprint, and only the public key ships; an unpacked EXE cannot be used to mint keys.
- **Encrypted content pack.** `web/` is obfuscated and packed into a single AES-256-GCM `web.pak`, decrypted in memory and served from there.
- **Honest limits.** [`docs/INSTALL.md`](docs/INSTALL.md) documents what the protection does not stop, for example that a licensed user can unpack `web.pak`, and that a licence file cannot be prevented from being reactivated on another machine (expiry bounds it).
- **Failure visibility.** If Ctrl is pressed by accident, hand tracking would silently die; a persistent on-screen badge makes the current input mode obvious. Hand frames keep being ignored (not dropped from the socket) while in mouse mode.
- **Tests.** 11 pytest modules (about 175 test functions) covering the licence flow, fingerprinting, the web pack, the installer guard, build flags, path handling, the static server and the entry point.

## Project status

The migration from Unity to a web client is complete, and the licence, encrypted-pack and installer pipeline is implemented (`python build.py`, `python build.py --kurucu`). The depth camera source (`python/camera/depth.py`) is a stub for a possible hardware upgrade; the default source is a webcam.

## Repository layout

| Path | Purpose |
|---|---|
| `matematik.py` | Single entry point: licence, server, browser, detector |
| `web/` | The game: `index.html`, `styles.css`, `js/` (game, lens, tokens, questions, input, leaderboard, calibration) |
| `python/` | Vision process: camera, detection, active-player selection, gesture FSM, mapping, smoothing, WebSocket sender |
| `build.py`, `web_paket.py`, `installer/` | Nuitka build, encrypted web pack, Inno Setup script |
| `lisans*.py`, `parmak_izi.py`, `lisans_web/` | Licence verification, fingerprint, licence window |
| `tests/` | pytest suite |
| `docs/` | Install guide, kiosk setup, delivery checklist, plans (build spike, licensing, web migration) |
| `Matematik oyunu _web tasarım/` | Design handoff for the web UI (reference prototype, not production code) |
| `unity/` | Legacy Unity project, removed from this branch; kept only in git history |

## Running locally

```bash
cd python
pip install -r requirements.txt
python download_model.py        # fetches the MediaPipe model
cd ..
python matematik.py --pencere   # windowed; no camera: press Ctrl for mouse mode
```

Calibration (once, after placing projector and camera): `python matematik.py --kalibrasyon`. Full setup (Turkish): [`docs/INSTALL.md`](docs/INSTALL.md); exhibit installation: [`docs/KIOSK.md`](docs/KIOSK.md).
