import { useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import ReviewCard from '../components/ReviewCard';
import { useBoothStore } from '../stores/boothStore';

function Reviewing() {
  const data = useBoothStore((state) => state.data);
  const review = data.review;
  const postedRef = useRef(false);

  const handleContinue = useCallback(() => {
    if (postedRef.current) return;
    postedRef.current = true;
    fetch('/api/step/reviewing/complete', { method: 'POST' }).catch(() => {
      useBoothStore.getState().setError('Failed to complete review');
    });
  }, []);

  if (!review) {
    return (
      <motion.div
        className="flex items-center justify-center w-full h-full"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <p className="text-gray-500 text-2xl">Waiting for review...</p>
      </motion.div>
    );
  }

  return (
    <motion.div
      className="flex flex-col items-center w-full h-full px-6 py-10 overflow-y-auto"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <motion.h2
        className="text-white font-bold text-center mb-10"
        style={{ fontSize: 'clamp(28px, 4vw, 48px)' }}
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        Elon's Review
      </motion.h2>

      <div className="flex flex-col gap-6 w-full max-w-3xl pb-8">
        <ReviewCard
          title="One-line Insight"
          content={review.insight}
          type="insight"
        />

        <ReviewCard
          title="Hardcore Highlights"
          content={review.highlights}
          type="list"
        />

        <ReviewCard
          title="Sharp Question"
          content={review.sharp_question}
          type="quote"
        />

        <ReviewCard
          title="Hardcore Suggestions"
          content={review.suggestions}
          type="list"
        />

        <ReviewCard
          title="Closing"
          content={review.closing}
          type="quote"
        />
      </div>

      <motion.button
        className="px-10 py-4 border-2 border-gray-600 text-gray-300 rounded-lg text-xl md:text-2xl hover:border-white hover:text-white transition-colors duration-200 mt-4 mb-10"
        onClick={handleContinue}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8, duration: 0.4 }}
      >
        Continue to Photo
      </motion.button>
    </motion.div>
  );
}

export default Reviewing;
