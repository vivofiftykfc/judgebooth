import { motion } from 'framer-motion';
import QRDisplay from '../components/QRDisplay';
import { useBoothStore } from '../stores/boothStore';

function PhotoOutput() {
  const data = useBoothStore((state) => state.data);

  const handleRestart = () => {
    window.location.reload();
  };

  return (
    <motion.div
      className="flex flex-col items-center justify-center w-full h-full px-8"
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
        Your Booth Photo
      </motion.h2>

      <motion.div
        className="mb-10"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.3, duration: 0.5 }}
      >
        {data.photo ? (
          <img
            src={data.photo}
            alt="Booth photo"
            className="max-w-full max-h-[50vh] rounded-xl border border-gray-700 shadow-2xl"
          />
        ) : (
          <div className="w-80 h-60 bg-gray-900 border border-gray-700 rounded-xl flex items-center justify-center">
            <p className="text-gray-600 text-xl">Photo not available</p>
          </div>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.5 }}
      >
        {data.qr ? (
          <QRDisplay qrPath={data.qr} />
        ) : (
          <p className="text-gray-600 text-lg">QR code not available</p>
        )}
      </motion.div>

      <motion.p
        className="text-gray-400 mt-4 text-center"
        style={{ fontSize: 'clamp(16px, 1.8vw, 24px)' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.9, duration: 0.5 }}
      >
        Scan the code to save your review report
      </motion.p>

      <motion.button
        className="px-10 py-4 border-2 border-gray-600 text-gray-300 rounded-lg text-xl md:text-2xl hover:border-white hover:text-white transition-colors duration-200 mt-10"
        onClick={handleRestart}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.2, duration: 0.4 }}
      >
        Start Again
      </motion.button>
    </motion.div>
  );
}

export default PhotoOutput;
