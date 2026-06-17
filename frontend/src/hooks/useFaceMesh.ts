import { useEffect } from 'react';
import {
  FaceLandmarker,
  FilesetResolver,
  DrawingUtils,
} from '@mediapipe/tasks-vision';

// wasm 版本需与已安装的 @mediapipe/tasks-vision 版本一致
const WASM_URL =
  'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm';
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task';

/**
 * 浏览器端实时人脸 mesh 叠加（demo 增强）。
 *
 * 在传入的 <video> 上方，用同一套 MediaPipe FaceLandmarker（web 版）实时
 * 检测 478 关键点并画到 overlay canvas 上。注意：这是浏览器内的独立检测，
 * 用于演示/直观确认摄像头与人脸检测；后端的情绪分析另有一套同源引擎。
 */
export function useFaceMesh(
  videoRef: React.RefObject<HTMLVideoElement | null>,
  canvasRef: React.RefObject<HTMLCanvasElement | null>,
  enabled: boolean,
  onStatus?: (detected: boolean) => void,
): void {
  useEffect(() => {
    if (!enabled) return;

    let landmarker: FaceLandmarker | null = null;
    let raf = 0;
    let cancelled = false;
    let lastTs = -1;

    async function createLandmarker(): Promise<FaceLandmarker> {
      const fileset = await FilesetResolver.forVisionTasks(WASM_URL);
      try {
        return await FaceLandmarker.createFromOptions(fileset, {
          baseOptions: { modelAssetPath: MODEL_URL, delegate: 'GPU' },
          runningMode: 'VIDEO',
          numFaces: 1,
        });
      } catch {
        // GPU 不可用时回退 CPU
        return await FaceLandmarker.createFromOptions(fileset, {
          baseOptions: { modelAssetPath: MODEL_URL, delegate: 'CPU' },
          runningMode: 'VIDEO',
          numFaces: 1,
        });
      }
    }

    function loop() {
      raf = requestAnimationFrame(loop);
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || !landmarker || !video.videoWidth) return;

      const w = video.clientWidth;
      const h = video.clientHeight;
      if (w === 0 || h === 0) return;
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }

      const ts = performance.now();
      if (ts <= lastTs) return; // VIDEO 模式要求时间戳严格递增
      lastTs = ts;

      let result;
      try {
        result = landmarker.detectForVideo(video, ts);
      } catch {
        return;
      }

      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.clearRect(0, 0, w, h);

      const faces = result.faceLandmarks;
      onStatus?.(faces.length > 0);
      if (faces.length === 0) return;

      const du = new DrawingUtils(ctx);
      for (const lm of faces) {
        du.drawConnectors(lm, FaceLandmarker.FACE_LANDMARKS_TESSELATION, {
          color: 'rgba(0,255,120,0.25)',
          lineWidth: 0.5,
        });
        du.drawConnectors(lm, FaceLandmarker.FACE_LANDMARKS_FACE_OVAL, {
          color: '#00ff78',
          lineWidth: 1.5,
        });
        du.drawConnectors(lm, FaceLandmarker.FACE_LANDMARKS_LEFT_EYE, {
          color: '#00e5ff',
          lineWidth: 1,
        });
        du.drawConnectors(lm, FaceLandmarker.FACE_LANDMARKS_RIGHT_EYE, {
          color: '#00e5ff',
          lineWidth: 1,
        });
        du.drawConnectors(lm, FaceLandmarker.FACE_LANDMARKS_LIPS, {
          color: '#ff3b6b',
          lineWidth: 1.5,
        });
      }
    }

    createLandmarker()
      .then((lm) => {
        if (cancelled) {
          lm.close();
          return;
        }
        landmarker = lm;
        loop();
      })
      .catch(() => {
        // 模型/wasm 加载失败（如离线）：静默，预览仍正常，只是没有 mesh
      });

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      landmarker?.close();
      landmarker = null;
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext('2d');
      if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
    };
  }, [enabled, videoRef, canvasRef, onStatus]);
}
