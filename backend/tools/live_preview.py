"""
摄像头实时预览 + 人脸检测调试工具。

用本机摄像头跑**后端真正用的** FaceLandmarkerEngine + estimate_head_pose，
实时叠加 478 关键点，并显示 yaw/pitch/roll。用来验证情绪/头姿逻辑：
对着它点头/摇头/歪头，看三个角度数字动不动、对不对。
（这跑的是产出 emotion_report 的同一套代码，比前端 MediaPipe-JS 更能反映真实逻辑。）

用法（在 backend/ 目录下）：
    python tools/live_preview.py
    python tools/live_preview.py --index 1     # 换摄像头
    python tools/live_preview.py --no-landmarks # 不画 478 点

窗口按键：q/ESC 退出；s 存当前帧到 backend/data/
"""

import argparse
import os
import sys
import time

import cv2

# 让 `from pipelines...` 可导入（本文件在 backend/tools/ 下）
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from pipelines.video.mediapipe_engine import FaceLandmarkerEngine, MODEL_PATH

GREEN = (0, 255, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--index", type=int, default=0, help="摄像头 index")
    p.add_argument("--no-landmarks", action="store_true", help="不绘制 478 关键点")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if not os.path.isfile(MODEL_PATH):
        print(f"[!] 模型文件不存在: {MODEL_PATH}")
        return 1

    engine = FaceLandmarkerEngine(model_path=MODEL_PATH)
    if not engine.is_ready:
        print("[!] FaceLandmarker 初始化失败（看上方日志）。")
        return 1
    print("[*] FaceLandmarker 就绪")

    cap = cv2.VideoCapture(args.index)
    if not cap.isOpened():
        print(f"[!] 无法打开摄像头 index={args.index}，试试 --index 1")
        return 1
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    print("[*] 摄像头已打开，按 q / ESC 退出，按 s 存帧")

    save_dir = os.path.join(BACKEND_DIR, "data")
    os.makedirs(save_dir, exist_ok=True)

    start = time.time()
    frame_count = 0
    fps = 0.0
    last_t = start

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[!] 读帧失败")
                break

            frame_count += 1
            ts_ms = int((time.time() - start) * 1000)
            h, w = frame.shape[:2]

            result = engine.process_frame(frame, timestamp_ms=ts_ms)

            now = time.time()
            if now - last_t >= 0.5:
                fps = frame_count / (now - start)
                last_t = now
            brightness = float(frame.mean())

            detected = result["face_detected"]
            color = GREEN if detected else RED
            status = "FACE DETECTED" if detected else "NO FACE"

            if detected and not args.no_landmarks and result["landmarks"]:
                for lm in result["landmarks"]:
                    cv2.circle(frame, (int(lm[0] * w), int(lm[1] * h)), 1, GREEN, -1)

            cv2.rectangle(frame, (0, 0), (w, 90), (0, 0, 0), -1)
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
            cv2.putText(frame, f"FPS:{fps:4.1f}  brightness:{brightness:5.1f}",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 1)

            if detected:
                pose = result["head_pose"] or {}
                cv2.putText(
                    frame,
                    f"yaw:{pose.get('yaw', 0):6.1f}  pitch:{pose.get('pitch', 0):6.1f}  roll:{pose.get('roll', 0):6.1f}",
                    (10, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.6, YELLOW, 1)
            else:
                hint = "镜头盖住/太暗?" if brightness < 20 else "对准镜头, 50-100cm, 正面光源"
                cv2.putText(frame, hint, (10, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.55, YELLOW, 1)

            cv2.imshow("Live Preview - FaceLandmarker (q/ESC quit, s save)", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("s"):
                path = os.path.join(save_dir, f"preview_{int(time.time())}.jpg")
                ok, buf = cv2.imencode(".jpg", frame)
                if ok:
                    with open(path, "wb") as f:
                        f.write(buf.tobytes())
                    print(f"[*] 已保存: {path}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    sys.exit(main())
