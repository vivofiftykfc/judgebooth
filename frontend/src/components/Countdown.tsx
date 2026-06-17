import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';

interface CountdownProps {
  seconds: number;
}

function Countdown({ seconds }: CountdownProps) {
  const isLastTen = seconds <= 10 && seconds > 0;
  const [key, setKey] = useState(seconds);

  useEffect(() => {
    setKey(seconds);
  }, [seconds]);

  const displayText = seconds > 0 ? seconds.toString() : '0';

  return (
    <div className="flex items-center justify-center">
      <AnimatePresence mode="wait">
        <motion.span
          key={key}
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 20, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className={`font-mono font-bold tabular-nums ${
            isLastTen ? 'text-red-500' : 'text-white'
          }`}
          style={{ fontSize: 'clamp(64px, 15vw, 160px)' }}
        >
          {displayText}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

export default Countdown;
