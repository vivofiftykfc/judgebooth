import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { useBoothStore } from '../stores/boothStore';
import muskPortrait from '../assets/musk.png';

const INTRO_MS = 3500; // 开场停留时长，之后自动进入 presenting

function Welcome() {
  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(() => {
      if (cancelled) return;
      fetch('/api/step/welcome', { method: 'POST' })
        .then(() => {
          if (!cancelled) {
            useBoothStore.getState().updateFromSSE({
              step: 'presenting', countdown: 10, data: {},
            });
          }
        })
        .catch(() => {
          useBoothStore.getState().setError('Failed to reset booth');
        });
    }, INTRO_MS);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, []);

  return (
    <div className="chamber w-full h-full relative flex flex-col items-center justify-center px-[6vw]">
      <div className="grain" />

      {/* 顶栏 */}
      <header className="absolute top-[2.4vh] left-[3vw] right-[3vw] flex items-center justify-between z-30">
        <div className="flex items-center gap-3">
          <span className="font-display text-2xl leading-none">
            <span style={{ color: 'var(--signal)' }}>X</span>
            <span className="text-[var(--ink)]">.AI</span>
          </span>
          <span className="hud-label hidden sm:inline">Temporary Review Booth</span>
        </div>
        <span className="hud-label flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[var(--hud)]" />
          Standby
        </span>
      </header>

      <div className="flex flex-col items-center z-20">
        {/* kicker */}
        <motion.div
          className="hud-label mb-6"
          style={{ color: 'var(--signal)' }}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          ▍Evaluation Session · 评审席启动
        </motion.div>

        {/* 肖像 */}
        <motion.img
          src={muskPortrait}
          alt="Elon Musk"
          className="breathe object-contain drop-shadow-[0_0_45px_rgba(255,43,43,0.28)]"
          style={{ width: 'min(40vh, 360px)', aspectRatio: '1' }}
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.35, duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        />

        {/* 标题 */}
        <motion.h1
          className="font-display text-[var(--ink)] text-center leading-[0.9] mt-7"
          style={{ fontSize: 'clamp(40px, 6.5vw, 96px)' }}
          initial={{ opacity: 0, y: 22 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.6 }}
        >
          传奇<span style={{ color: 'var(--signal)' }}>评审</span>亭
        </motion.h1>

        {/* 标语 */}
        <motion.p
          className="text-[var(--muted)] text-center max-w-xl mt-5 leading-relaxed"
          style={{ fontSize: 'clamp(15px, 1.7vw, 22px)' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.95, duration: 0.6 }}
        >
          我是埃隆·马斯克。接下来两分钟，<br className="hidden sm:block" />
          证明你做的东西，值得我抬一下眼皮。
        </motion.p>

        {/* 载入条 */}
        <motion.div
          className="mt-12 w-[min(60vw,360px)]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.3, duration: 0.5 }}
        >
          <div className="flex items-center justify-between hud-label mb-2">
            <span>Initializing Session</span>
            <span style={{ color: 'var(--signal)' }} className="rec-dot">●</span>
          </div>
          <div className="h-[3px] bg-white/8 overflow-hidden rounded-full">
            <motion.div
              className="h-full rounded-full"
              style={{ background: 'var(--signal)' }}
              initial={{ width: '0%' }}
              animate={{ width: '100%' }}
              transition={{ duration: INTRO_MS / 1000, ease: 'linear' }}
            />
          </div>
        </motion.div>
      </div>
    </div>
  );
}

export default Welcome;
