import { useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import Countdown from '../components/Countdown';
import { useBoothStore } from '../stores/boothStore';

function Presenting() {
  const countdown = useBoothStore((state) => state.countdown);
  const step = useBoothStore((state) => state.step);
  const endRequestedRef = useRef(false);

  const handleEndPresentation = useCallback(() => {
    if (endRequestedRef.current) return;
    endRequestedRef.current = true;
    fetch('/api/step/presenting/end', { method: 'POST' }).catch(() => {
      useBoothStore.getState().setError('Failed to end presentation');
    });
  }, []);

  useEffect(() => {
    if (countdown <= 0 && step === 'presenting' && !endRequestedRef.current) {
      handleEndPresentation();
    }
  }, [countdown, step, handleEndPresentation]);

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
        <Countdown seconds={countdown} />
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
        <div className="w-48 h-36 md:w-64 md:h-48 bg-gray-900 border border-gray-700 rounded-lg flex items-center justify-center overflow-hidden">
          <video
            id="camera-preview"
            autoPlay
            muted
            playsInline
            className="w-full h-full object-cover"
          />
        </div>
        <p className="text-gray-600 text-center mt-2 text-sm">
          camera preview
        </p>
      </motion.div>

      <motion.button
        className="px-10 py-4 border-2 border-gray-600 text-gray-300 rounded-lg text-xl md:text-2xl hover:border-red-500 hover:text-red-400 hover:bg-red-500/10 transition-colors duration-200"
        onClick={handleEndPresentation}
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
