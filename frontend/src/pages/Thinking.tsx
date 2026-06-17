import { motion } from 'framer-motion';

function Thinking() {
  return (
    <motion.div
      className="flex flex-col items-center justify-center w-full h-full px-8"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <motion.div
        className="relative mb-12"
        animate={{
          scale: [1, 1.15, 1],
          opacity: [0.6, 1, 0.6],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      >
        <div className="w-24 h-24 md:w-32 md:h-32 rounded-full border-2 border-gray-500 flex items-center justify-center">
          <svg
            className="w-12 h-12 md:w-16 md:h-16 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
        </div>
      </motion.div>

      <motion.h2
        className="text-white font-bold text-center leading-tight mb-4"
        style={{ fontSize: 'clamp(24px, 3.5vw, 48px)' }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5 }}
      >
        Analyzing with first principles...
      </motion.h2>

      <motion.p
        className="text-gray-500 text-center"
        style={{ fontSize: 'clamp(16px, 2vw, 24px)' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6, duration: 0.5 }}
      >
        Breaking down your project at the fundamental level
      </motion.p>

      <motion.div
        className="flex gap-2 mt-12"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.9, duration: 0.5 }}
      >
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-2 h-2 md:w-3 md:h-3 rounded-full bg-gray-500"
            animate={{
              opacity: [0.3, 1, 0.3],
            }}
            transition={{
              duration: 1.2,
              repeat: Infinity,
              delay: i * 0.3,
              ease: 'easeInOut',
            }}
          />
        ))}
      </motion.div>
    </motion.div>
  );
}

export default Thinking;
