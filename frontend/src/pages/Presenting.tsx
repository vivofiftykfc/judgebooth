import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useBoothStore } from '../stores/boothStore';
import { useFaceMesh } from '../hooks/useFaceMesh';
import { useSoniox } from '../hooks/useSoniox';
import MuskPresence from '../components/MuskPresence';
import muskNeutral from '../assets/musk_neutral.png';
import muskSkeptical from '../assets/musk_skeptical.png';

const FRAME_INTERVAL_MS = 200; // 5fps

function Presenting() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const endRef = useRef(false);
  const frameTimerRef = useRef<number>(0);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const sessionRef = useRef(Math.random().toString(36).slice(2, 8).toUpperCase());

  const [started, setStarted] = useState(false);
  const [seconds, setSeconds] = useState(60);
  const [total, setTotal] = useState(60);
  const [faceLocked, setFaceLocked] = useState(false);

  // 浏览器端实时人脸 mesh 叠加
  useFaceMesh(videoRef, overlayRef, started, setFaceLocked);

  // Soniox 实时语音转写（实时字幕）
  const soniox = useSoniox();

  // --- 重置 ---
  useEffect(() => {
    endRef.current = false;
    setStarted(false);
    setSeconds(60);
    setTotal(60);
  }, []);

  // --- 点击 "开始" ---
  async function handleStart() {
    if (started) return;
    setStarted(true);
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
    await fetch('/api/step/presenting/start', { method: 'POST' });
    startFrameCapture();
    soniox.start(); // 开始实时语音转写
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

  // --- 本地倒计时 ---
  useEffect(() => {
    if (!started || endRef.current) return;
    const timer = setInterval(() => {
      setSeconds((prev) => (prev <= 1 ? 0 : prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [started]);

  useEffect(() => {
    if (started && seconds <= 0 && !endRef.current) endPresentation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [started, seconds]);

  // --- 结束路演 ---
  async function endPresentation() {
    if (endRef.current) return;
    endRef.current = true;
    if (frameTimerRef.current) {
      clearInterval(frameTimerRef.current);
      frameTimerRef.current = 0;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    // 停止 Soniox，拿到最终转写 + 词级 token，先发给后端（end 触发分析前必须就位）
    const { text, tokens } = soniox.stop();
    try {
      await fetch('/api/step/presenting/transcript', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, tokens }),
      });
    } catch {
      /* 转写发送失败也继续 */
    }

    try {
      await fetch('/api/step/presenting/end', { method: 'POST' });
    } catch {
      /* ignore */
    }
    useBoothStore.getState().updateFromSSE({ step: 'thinking', countdown: 0, data: {} });
  }

  const low = seconds <= 6;
  const progress = total > 0 ? (seconds / total) * 100 : 0;
  const captionFinal =
    soniox.finalText.length > 64 ? '…' + soniox.finalText.slice(-64) : soniox.finalText;

  // =====================================================================
  // 未开始：评审席待命
  // =====================================================================
  if (!started) {
    return (
      <div className="chamber w-full h-full relative flex items-center justify-center px-[6vw]">
        <div className="grain" />
        <Header session={sessionRef.current} live={false} />

        <motion.div
          className="grid grid-cols-1 md:grid-cols-[0.82fr_1fr] gap-[4vw] items-center w-full max-w-[1180px] z-20"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6 }}
        >
          <motion.div
            className="h-[58vh] max-h-[560px]"
            initial={{ opacity: 0, x: -24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15, duration: 0.6 }}
          >
            <MuskPresence active={false} neutralSrc={muskNeutral} skepticalSrc={muskSkeptical} />
          </motion.div>

          <div>
            <motion.div
              className="hud-label mb-5"
              style={{ color: 'var(--signal)' }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              ▍评审席已就位
            </motion.div>
            <motion.h1
              className="font-display text-[var(--ink)] leading-[0.92]"
              style={{ fontSize: 'clamp(44px, 7vw, 104px)' }}
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.6 }}
            >
              ELON 正在
              <br />
              <span className="glow-red" style={{ color: 'var(--signal)' }}>等你开口</span>
            </motion.h1>
            <motion.p
              className="text-[var(--muted)] mt-6 max-w-md leading-relaxed"
              style={{ fontSize: 'clamp(14px, 1.5vw, 19px)' }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
            >
              限时路演。站到镜头前，用最少的话讲清你做了什么——
              证明它值得他抬一下眼皮。
            </motion.p>
            <motion.button
              onClick={handleStart}
              className="group mt-10 inline-flex items-center gap-3 px-9 py-4 border border-[var(--signal)] text-[var(--signal)] font-hud tracking-[0.25em] uppercase text-sm hover:bg-[var(--signal)] hover:text-black transition-colors duration-200"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.9 }}
              whileTap={{ scale: 0.97 }}
            >
              <span className="w-2 h-2 bg-[var(--signal)] group-hover:bg-black" />
              开始路演
            </motion.button>
          </div>
        </motion.div>
      </div>
    );
  }

  // =====================================================================
  // 进行中：审视台
  // =====================================================================
  return (
    <motion.div
      className="chamber w-full h-full relative flex flex-col px-[3vw] py-[2.4vh]"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <div className="grain" />
      <Header session={sessionRef.current} live />

      <main className="flex-1 min-h-0 grid grid-cols-[36%_1fr] gap-[2.4vw] mt-[2vh] z-20">
        {/* 左：马斯克在场 */}
        <MuskPresence active neutralSrc={muskNeutral} skepticalSrc={muskSkeptical} />

        {/* 右：被审视的你 */}
        <div className="relative flex flex-col min-h-0">
          <div className="flex items-end justify-between mb-3 shrink-0">
            <div>
              <div className="hud-label">Subject // 你</div>
              <div className="font-display text-[var(--ink)] leading-none"
                   style={{ fontSize: 'clamp(22px, 3vw, 46px)' }}>
                UNDER&nbsp;REVIEW
              </div>
            </div>
            <div className="text-right leading-none">
              <div className="hud-label mb-1">剩余</div>
              <div className={`font-display tabular-nums leading-none ${low ? 'glow-red' : ''}`}
                   style={{ fontSize: 'clamp(54px, 8vw, 120px)', color: low ? 'var(--signal)' : 'var(--ink)' }}>
                {seconds}
              </div>
            </div>
          </div>

          {/* 摄像头取景器 */}
          <div className="relative flex-1 min-h-0 rounded-md overflow-hidden border border-[var(--line)] bg-black">
            <video ref={videoRef} autoPlay muted playsInline
                   className="absolute inset-0 w-full h-full object-cover" />
            <canvas ref={overlayRef}
                    className="absolute inset-0 w-full h-full object-cover pointer-events-none z-[3]" />

            {/* 取景角括号 */}
            <span className="bracket tl z-10" />
            <span className="bracket tr z-10" />
            <span className="bracket bl z-10" />
            <span className="bracket br z-10" />

            {/* 中心准星 */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-[2]">
              <div className="relative w-16 h-16 opacity-50">
                <span className="absolute left-1/2 top-0 -translate-x-1/2 w-px h-4 bg-[var(--signal)]" />
                <span className="absolute left-1/2 bottom-0 -translate-x-1/2 w-px h-4 bg-[var(--signal)]" />
                <span className="absolute top-1/2 left-0 -translate-y-1/2 h-px w-4 bg-[var(--signal)]" />
                <span className="absolute top-1/2 right-0 -translate-y-1/2 h-px w-4 bg-[var(--signal)]" />
              </div>
            </div>

            {/* 顶部状态 */}
            <div className="absolute top-3 left-3 z-10 flex items-center gap-2 px-2 py-1 bg-black/55 rounded">
              <span className={`w-2 h-2 rounded-full ${faceLocked ? 'bg-[#39ff8b]' : 'bg-[var(--signal)] rec-dot'}`} />
              <span className="hud-label" style={{ color: faceLocked ? '#39ff8b' : 'var(--signal)' }}>
                {faceLocked ? 'FACE LOCK · 478 PTS' : 'ACQUIRING FACE…'}
              </span>
            </div>

            {/* 底部遥测 */}
            <div className="absolute bottom-3 left-3 z-10 hud-label">▸ ANALYZING SUBJECT</div>
            <div className="absolute bottom-3 right-3 z-10 hud-label text-right">
              SESS {sessionRef.current} · 5 FPS
            </div>
          </div>

          {/* 实时字幕（Soniox） */}
          <div className="mt-3 shrink-0 rounded-md border border-[var(--line)] bg-black/40 px-4 py-2.5 min-h-[64px]">
            <div className="hud-label mb-1 flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full ${soniox.active ? 'bg-[#39ff8b] rec-dot' : 'bg-[var(--hud)]'}`} />
              Live Transcript · 实时识别
            </div>
            <div className="font-hud leading-snug" style={{ fontSize: 'clamp(13px, 1.2vw, 16px)' }}>
              {captionFinal || soniox.interimText ? (
                <span className="text-[var(--ink)]">
                  {captionFinal}
                  <span className="text-[var(--muted)]">{soniox.interimText}</span>
                </span>
              ) : (
                <span className="text-[var(--muted)]">
                  {soniox.error ? `识别异常：${soniox.error}` : '开始说话，马斯克在听…'}
                </span>
              )}
            </div>
          </div>

          {/* 时间进度条 */}
          <div className="h-[3px] mt-3 bg-white/8 overflow-hidden rounded-full shrink-0">
            <div className="h-full rounded-full transition-[width] duration-1000 ease-linear"
                 style={{ width: `${progress}%`, background: low ? 'var(--signal)' : 'var(--hud)' }} />
          </div>
        </div>
      </main>

      {/* 底栏 */}
      <footer className="flex items-center justify-between mt-[1.8vh] z-20 shrink-0">
        <div className="hud-label">他在听 · 说重点</div>
        <button
          onClick={endPresentation}
          className="inline-flex items-center gap-2 px-6 py-2.5 border border-white/15 text-[var(--muted)] font-hud tracking-[0.22em] uppercase text-xs hover:border-[var(--signal)] hover:text-[var(--signal)] transition-colors duration-200"
        >
          结束路演 ▸
        </button>
      </footer>
    </motion.div>
  );
}

/* 顶部 HUD 条 */
function Header({ session, live }: { session: string; live: boolean }) {
  return (
    <header className="absolute top-[2.4vh] left-[3vw] right-[3vw] flex items-center justify-between z-30">
      <div className="flex items-center gap-3">
        <span className="font-display text-2xl leading-none">
          <span style={{ color: 'var(--signal)' }}>X</span>
          <span className="text-[var(--ink)]">.AI</span>
        </span>
        <span className="hud-label hidden sm:inline">Temporary Review Booth</span>
      </div>
      <div className="flex items-center gap-5">
        <span className="hud-label">SESSION&nbsp;#{session}</span>
        <span className="hud-label flex items-center gap-1.5" style={{ color: live ? 'var(--signal)' : 'var(--hud)' }}>
          <span className={`w-2 h-2 rounded-full ${live ? 'bg-[var(--signal)] rec-dot' : 'bg-[var(--hud)]'}`} />
          {live ? 'REC' : 'STANDBY'}
        </span>
      </div>
    </header>
  );
}

export default Presenting;
