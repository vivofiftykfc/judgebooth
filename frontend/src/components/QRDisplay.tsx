interface QRDisplayProps {
  qrPath: string;
}

function QRDisplay({ qrPath }: QRDisplayProps) {
  return (
    <div className="flex flex-col items-center gap-4">
      <div className="bg-white rounded-xl p-3">
        <img
          src={qrPath}
          alt="Scan QR code for review report"
          className="w-48 h-48 md:w-56 md:h-56 object-contain"
        />
      </div>
      <p className="text-gray-400 text-lg md:text-xl text-center">
        Scan to save your review report
      </p>
    </div>
  );
}

export default QRDisplay;
