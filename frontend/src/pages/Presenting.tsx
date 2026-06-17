import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import Countdown from '../components/Countdown';
import { useBoothStore } from '../stores/boothStore';
import { useFaceMesh } from '../hooks/useFaceMesh';

const FRAME_INTERVAL_MS = 200; // 5fps

function Presenting() {
  const countdown = useBoothStore((state) => state.countdown);
  const step = useBoothStore((state) => state.step);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const endRef = useRef(false);
  const frameTimerRef = useRef<number>(0);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);

  const [started, setStarted] = useState(false);
  const [seconds, setSeconds] = useState(60);
  const [faceLocked, setFaceLocked] = useState(false);

  // 浏览器端实时人脸 mesh 叠加（demo 增强）
  useFaceMesh(videoRef, overlayRef, started, setFaceLocked);

  // --- 清残留帧（回到 Presenting 时重置状态） ---
  useEffect(() => {
    endRef.current = false;
    setStarted(false);
    setSeconds(60);
  }, []);

  // --- 点击 "开始" ---
  async function handleStart() {
    if (started) return;
    setStarted(true);

    // 1. 开摄像头预览
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
    } catch {
      // 摄像头不可用也可以继续
    }

    // 2. 通知后端开始录音 + 发帧准备
    await fetch('/api/step/presenting/start', { method: 'POST' });

    // 3. 开始发帧
    startFrameCapture();
  }

  // --- 发帧 ---
  function startFrameCapture() {
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    canvasRef.current = canvas;

    frameTimerRef.current = window.setInterval(() => {
      const video = videoRef.current;
      if (!video || !video.videoWidth || endRef.current) return;
      try {
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        ctx.drawImage(video, 0, 0, 640, 480);
        const jpeg = canvas.toDataURL('image/jpeg', 0.5);
        fetch('/api/step/presenting/frame', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ frame: jpeg }),
        }).catch(() => {});
      } catch {}
    }, FRAME_INTERVAL_MS);
  }

  // --- 本地倒计时（从 start 后才开始） ---
  useEffect(() => {
    if (!started || endRef.current) return;
    const timer = setInterval(() => {
      setSeconds((prev) => {
        if (prev <= 1) {
          // 倒计时结束，不在这里调 endPresentation（避免 setState 内副作用）
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [started]);

  // 倒计时归零时触发结束
  useEffect(() => {
    if (started && seconds <= 0 && !endRef.current) {
      endPresentation();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [started, seconds]);

  // --- 结束路演 ---
  function endPresentation() {
    if (endRef.current) return;
    endRef.current = true;

    // 停帧发送
    if (frameTimerRef.current) {
      clearInterval(frameTimerRef.current);
      frameTimerRef.current = 0;
    }

    // 停摄像头
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }

    // 通知后端结束
    fetch('/api/step/presenting/end', { method: 'POST' })
      .then(() => {
        // 后端返回后强制跳转到 thinking（不等 SSE，防止丢事件）
        useBoothStore.getState().updateFromSSE({
          step: 'thinking',
          countdown: 0,
          data: {},
        });
      })
      .catch(() => {
        // 即使后端报错也跳转
        useBoothStore.getState().updateFromSSE({
          step: 'thinking',
          countdown: 0,
          data: {},
        });
      });
  }

  // --- 未开始：显示 Start 按钮 ---
  if (!started) {
    return (
      <motion.div
        className="flex flex-col items-center justify-center w-full h-full px-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <motion.h2
          className="text-white font-bold text-center mb-6"
          style={{ fontSize: 'clamp(28px, 4vw, 48px)' }}
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          Ready to Present
        </motion.h2>

        <motion.p
          className="text-gray-400 text-center max-w-xl mb-12"
          style={{ fontSize: 'clamp(16px, 2vw, 24px)' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.5 }}
        >
          You have up to 60 seconds. Present your project, then we'll analyze it.
        </motion.p>

        <motion.button
          className="px-16 py-6 border-2 border-gray-400 text-gray-200 rounded-xl text-2xl md:text-3xl hover:border-white hover:text-white hover:bg-white/5 transition-colors duration-200 tracking-wider"
          onClick={handleStart}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.7, duration: 0.4 }}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
        >
          Start
        </motion.button>
      </motion.div>
    );
  }

  // --- 已开始：显示倒计时 + 摄像头 + End Early ---
  return (
    <motion.div
      className="flex flex-col items-center justify-center w-full h-full px-8"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <motion.p
        className="text-gray-500 mb-8 tracking-widest uppercase"
        style={{ fontSize: 'clamp(14px, 1.5vw, 20px)' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        Listening...
      </motion.p>

      <div className="mb-8">
        <Countdown seconds={seconds} />
      </div>

      <motion.p
        className="text-gray-600 mb-12"
        style={{ fontSize: 'clamp(14px, 1.5vw, 20px)' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
      >
        seconds remaining
      </motion.p>

      <motion.div
        className="mb-12"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.6, duration: 0.4 }}
      >
        <div className="relative aspect-[4/3] w-[44vw] max-w-[520px] bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className="absolute inset-0 w-full h-full object-cover"
          />
          {/* 关键点 mesh 叠加层 */}
          <canvas
            ref={overlayRef}
            className="absolute inset-0 w-full h-full pointer-events-none"
          />
          {/* 检测状态徽标 */}
          <div className="absolute top-2 left-2 px-2 py-1 rounded text-xs font-mono flex items-center gap-1.5 bg-black/60">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                faceLocked ? 'bg-green-400' : 'bg-red-500'
              }`}
            />
            <span className={faceLocked ? 'text-green-300' : 'text-gray-400'}>
              {faceLocked ? '已锁定面部 478 点' : '正在寻找面部…'}
            </span>
          </div>
        </div>
        <p className="text-gray-600 text-center mt-2 text-sm">
          camera preview · 实时面部识别
        </p>
      </motion.div>

      <motion.button
        className="px-10 py-4 border-2 border-gray-600 text-gray-300 rounded-lg text-xl md:text-2xl hover:border-red-500 hover:text-red-400 hover:bg-red-500/10 transition-colors duration-200"
        onClick={endPresentation}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8, duration: 0.4 }}
      >
        End Early
      </motion.button>
    </motion.div>
  );
}

export default Presenting;
