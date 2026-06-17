import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useBoothStore } from '../stores/boothStore';

function Welcome() {
  const hasPostedRef = useRef(false);
  const countdown = useBoothStore((state) => state.countdown);
  const step = useBoothStore((state) => state.step);
  const [connecting, setConnecting] = useState(true);

  useEffect(() => {
    if (hasPostedRef.current) return;
    hasPostedRef.current = true;

    // 标记连接中
    const timeout = setTimeout(() => {
      // 3 秒后 step 还是 welcome 说明后端没响应
      if (step === 'welcome') {
        setConnecting(true);
      }
    }, 3000);

    fetch('/api/step/welcome', { method: 'POST' })
      .then(() => setConnecting(false))
      .catch(() => {
        setConnecting(true);
      });

    return () => clearTimeout(timeout);
  }, [step]);

  // 一旦收到 SSE 更新（step 不再是 welcome），连接成功
  useEffect(() => {
    if (step !== 'welcome') {
      setConnecting(false);
    }
  }, [step]);

  return (
    <motion.div
      className="flex flex-col items-center justify-center w-full h-full px-8"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.8, ease: 'easeOut' }}
    >
      <motion.h1
        className="text-white font-bold text-center leading-tight mb-6"
        style={{ fontSize: 'clamp(36px, 6vw, 72px)' }}
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.6 }}
      >
        Welcome to X.AI
        <br />
        Review Booth
      </motion.h1>

      <motion.p
        className="text-gray-400 text-center max-w-2xl"
        style={{ fontSize: 'clamp(18px, 2.5vw, 32px)' }}
        initial={{ y: 30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.6, duration: 0.6 }}
      >
        I am Elon Musk. You have 2 minutes to present your project.
      </motion.p>

      {countdown > 0 && (
        <motion.p
          className="text-gray-600 mt-12 text-4xl font-mono"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.0, duration: 0.5 }}
        >
          {countdown}
        </motion.p>
      )}

      {/* 连接状态提示 */}
      <motion.div
        className="mt-12 flex flex-col items-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5, duration: 0.5 }}
      >
        {connecting ? (
          <>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
              <span className="text-gray-500" style={{ fontSize: 'clamp(13px, 1.3vw, 16px)' }}>
                Connecting to server...
              </span>
            </div>
            <p className="text-gray-700 text-xs" style={{ fontSize: 'clamp(11px, 1vw, 13px)' }}>
              Make sure the backend is running (uvicorn main:app)
            </p>
          </>
        ) : (
          <p className="text-gray-600" style={{ fontSize: 'clamp(14px, 1.5vw, 20px)' }}>
            {countdown > 0 ? 'preparing...' : 'Preparing your session...'}
          </p>
        )}
      </motion.div>
    </motion.div>
  );
}

export default Welcome;
