import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getRandomLine } from '../data/muskLines';

interface MuskPresenceProps {
  active: boolean;
  neutralSrc: string;
  skepticalSrc: string;
}

/**
 * 马斯克在场状态：左侧肖像 + 随机旁白 interjection 系统。
 * active=true 时在路演中，会随机触发"马斯克内心独白"。
 */
function MuskPresence({ active, neutralSrc, skepticalSrc }: MuskPresenceProps) {
  const [line, setLine] = useState<string | null>(null);
  const [key, setKey] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!active) {
      setLine(null);
      if (timerRef.current) clearTimeout(timerRef.current);
      return;
    }

    const schedule = () => {
      const delay = 4000 + Math.random() * 8000; // 4-12s 随机间隔
      timerRef.current = setTimeout(() => {
        setLine(getRandomLine());
        setKey((k) => k + 1);
        // 显示 3-5s 后消失
        setTimeout(() => {
          setLine(null);
          schedule(); // 安排下一条
        }, 3000 + Math.random() * 2000);
      }, delay);
    };

    schedule();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [active]);

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center select-none">
      {/* 肖像 */}
      <motion.div
        className="relative w-full h-full flex items-center justify-center"
        animate={{ opacity: active ? 1 : 0.6 }}
        transition={{ duration: 0.5 }}
      >
        <img
          src={active ? skepticalSrc : neutralSrc}
          alt="Elon Musk"
          className="w-full h-full object-contain"
          draggable={false}
        />
      </motion.div>

      {/* 旁白气泡 */}
      <AnimatePresence>
        {line && (
          <motion.div
            key={key}
            className="absolute bottom-[8%] left-1/2 -translate-x-1/2 w-[80%] px-4 py-2.5 rounded-md border border-[var(--signal)]/40 bg-black/70 backdrop-blur-sm"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
          >
            <p className="font-hud text-[var(--signal)] text-xs leading-relaxed text-center tracking-wider">
              &ldquo;{line}&rdquo;
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 名字标签 */}
      <div className="absolute top-[4%] left-1/2 -translate-x-1/2">
        <span className="font-display text-sm tracking-[0.3em] text-white/30">
          ELON MUSK
        </span>
      </div>
    </div>
  );
}

export default MuskPresence;
