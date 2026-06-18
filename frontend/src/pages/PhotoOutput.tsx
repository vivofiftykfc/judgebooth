import { motion } from 'framer-motion';
import QRDisplay from '../components/QRDisplay';
import { useBoothStore } from '../stores/boothStore';

function PhotoOutput() {
  const data = useBoothStore((state) => state.data);
  const step = useBoothStore((state) => state.step);

  const handleRestart = () => {
    // 调 welcome API 重置后端 session，然后跳转 Welcome
    fetch('/api/step/welcome', { method: 'POST' })
      .then(() => {
        useBoothStore.getState().updateFromSSE({
          step: 'welcome', countdown: 10, data: {},
        });
      })
      .catch(() => {
        // 即使后端报错也跳转
        useBoothStore.getState().updateFromSSE({
          step: 'welcome', countdown: 0, data: {},
        });
      });
  };

  return (
    <div className="chamber w-full h-full relative flex flex-col px-[3vw] py-[2.4vh]">
      <div className="grain" />

      {/* HUD 顶栏 */}
      <header className="flex items-center justify-between shrink-0 z-30">
        <div className="flex items-center gap-3">
          <span className="font-display text-2xl leading-none">
            <span style={{ color: 'var(--signal)' }}>X</span>
            <span className="text-[var(--ink)]">.AI</span>
          </span>
          <span className="hud-label hidden sm:inline">Temporary Review Booth</span>
        </div>
        <span className="hud-label flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[var(--hud)]" />
          {step === 'complete' ? 'SESSION END' : 'PRINT'}
        </span>
      </header>

      {/* 主区域：横排左图右信息 */}
      <div className="flex-1 min-h-0 flex items-center justify-center z-20">
        <div className="flex items-start gap-[3vw] max-w-[90vw]">
          {/* 左：合影 */}
          <motion.div
            className="w-[38vw] max-w-[580px]"
            initial={{ opacity: 0, x: -24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2, duration: 0.5 }}
          >
            <div className="hud-label mb-3" style={{ color: 'var(--signal)' }}>
              ▍Session Photograph
            </div>
            {data.photo ? (
              <div className="relative rounded-lg overflow-hidden border border-[var(--line)] bg-black">
                <img src={data.photo} alt="Booth photo" className="w-full h-auto" />
                <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_40px_rgba(0,0,0,0.5)]" />
              </div>
            ) : (
              <div className="aspect-[3/4] bg-black/60 border border-[var(--line)] rounded-lg flex items-center justify-center">
                <p className="text-[var(--muted)] font-hud text-sm tracking-widest">▸ GENERATING…</p>
              </div>
            )}
          </motion.div>

          {/* 右：信息面板 */}
          <motion.div
            className="flex flex-col gap-5 pt-12"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4, duration: 0.5 }}
          >
            {/* 标题 */}
            <div>
              <div className="hud-label mb-1" style={{ color: 'var(--signal)' }}>COMPLETE</div>
              <div className="font-display text-[var(--ink)] leading-[0.92]"
                   style={{ fontSize: 'clamp(28px, 4vw, 64px)' }}>
                Your <span style={{ color: 'var(--signal)' }}>Booth</span> Photo
              </div>
            </div>

            {/* 分隔线 */}
            <div className="w-16 h-[2px]" style={{ background: 'var(--signal)' }} />

            {/* 描述 */}
            <p className="text-[var(--muted)] text-sm leading-relaxed max-w-xs">
              这是你的评审纪念照。扫描下方二维码可查看完整的评审报告——<br />
              含马斯克的 5 段评价、演讲流畅度分析和情绪数据。
            </p>

            {/* 二维码 */}
            <div>
              <div className="hud-label mb-2">SCAN TO SAVE</div>
              {data.qr ? (
                <div className="inline-flex items-center gap-3 p-3 border border-[var(--line)] rounded-lg bg-black/40">
                  <QRDisplay qrPath={data.qr} />
                  <div className="text-left">
                    <p className="text-[var(--muted)] text-xs leading-relaxed">
                      扫码查看<br />完整评审报告
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-[var(--muted)] font-hud text-xs tracking-widest">▸ QR GENERATING…</p>
              )}
            </div>

            {/* 重新开始 */}
            <motion.button
              onClick={handleRestart}
              className="group inline-flex items-center gap-3 px-8 py-3 border border-white/15 text-[var(--muted)] font-hud tracking-[0.22em] uppercase text-xs hover:border-[var(--signal)] hover:text-[var(--signal)] transition-colors duration-200 w-fit"
              whileTap={{ scale: 0.97 }}
            >
              <span className="w-2 h-2 rounded-full bg-white/15 group-hover:bg-[var(--signal)]" />
              重新开始
            </motion.button>
          </motion.div>
        </div>
      </div>

      {/* 底栏 */}
      <footer className="flex items-center justify-between shrink-0 z-30 mt-2">
        <div className="hud-label">评审完成 · 感谢参与</div>
        <div className="hud-label">X.AI REVIEW BOOTH v2</div>
      </footer>
    </div>
  );
}

export default PhotoOutput;
