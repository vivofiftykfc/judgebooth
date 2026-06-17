import { motion } from 'framer-motion';

type ReviewCardType = 'insight' | 'list' | 'quote';

interface ReviewCardProps {
  title: string;
  content: string | string[];
  type: ReviewCardType;
}

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.15, duration: 0.5, ease: 'easeOut' },
  }),
};

function ReviewCard({ title, content, type }: ReviewCardProps) {
  return (
    <motion.div
      className="border border-gray-700 rounded-xl p-6 md:p-8 w-full max-w-3xl mx-auto"
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      custom={1}
    >
      <h3 className="text-gray-400 text-lg md:text-xl mb-3 tracking-wide uppercase">
        {title}
      </h3>

      {type === 'insight' && typeof content === 'string' && (
        <p className="text-white text-2xl md:text-3xl font-bold leading-relaxed">
          {content}
        </p>
      )}

      {type === 'list' && Array.isArray(content) && (
        <ul className="space-y-3">
          {content.map((item, idx) => (
            <li
              key={idx}
              className="text-gray-200 text-xl md:text-2xl flex items-start gap-3"
            >
              <span className="text-gray-500 mt-1.5 shrink-0">--</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}

      {type === 'quote' && typeof content === 'string' && (
        <p className="text-gray-300 text-xl md:text-2xl italic leading-relaxed border-l-4 border-gray-600 pl-4">
          "{content}"
        </p>
      )}
    </motion.div>
  );
}

export default ReviewCard;
