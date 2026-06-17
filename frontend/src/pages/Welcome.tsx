import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { useBoothStore } from '../stores/boothStore';

function Welcome() {
  const hasPostedRef = useRef(false);

  useEffect(() => {
    if (hasPostedRef.current) return;
    hasPostedRef.current = true;

    fetch('/api/step/welcome', { method: 'POST' }).catch(() => {
      useBoothStore.getState().setError('Failed to reset booth');
    });
  }, []);

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

      <motion.p
        className="text-gray-600 mt-12"
        style={{ fontSize: 'clamp(14px, 1.5vw, 20px)' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2, duration: 0.5 }}
      >
        Preparing your session...
      </motion.p>
    </motion.div>
  );
}

export default Welcome;
