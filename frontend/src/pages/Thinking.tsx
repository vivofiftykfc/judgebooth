import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import muskSkeptical from '../assets/musk_skeptical.png';

// 分析"终端"滚动的伪日志（第一性原理味道，循环播放填充等待）
const LOG_POOL = [
  '转写语音流',
  '读取 478 个面部关键点',
  '评估紧张度 / 眼神接触',
  '拆解到第一性原理',
  '计算笨蛋指数（价值 ÷ 复杂度）',
  '检验物理可行性',
  '质疑核心需求',
  '搜索可删除的部分',
  '比对现有方案的差距',
  '组织措辞',
];

interface Line {
  id: number;
  text: string;
}

function Thinking() {
  const [log, setLog] = useState<Line[]>([]);
  const idRef = useRef(0);

  useEffect(() => {
    let i = 0;
    const tick = () => {
      idRef.current += 1;
      setLog((prev) => {
        const next = [...prev, { id: idRef.current, text: LOG_POOL[i % LOG_POOL.length] }];
        i += 1;
        return next.slice(-7);
      });
    };
    tick();
    const id = setInterval(tick, 1500);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="chamber w-full h-full relative flex flex-col px-[3vw] py-[2.4vh]">
      <div className="grain" />

      {/* 顶栏 */}
      <header className="absolute top-[2.4vh] left-[3vw] right-[3vw] flex items-center justify-between z-30">
        <div className="flex items-center gap-3">
          <span className="font-display text-2xl leading-none">
            <span style={{ color: 'var(--signal)' }}>X</span>
            <span className="text-[var(--ink)]">.AI</span>
          </span>
          <span className="hud-label hidden sm:inline">Temporary Review Booth</span>
        </div>
        <span className="hud-label flex items-center gap-1.5" style={{ color: 'var(--signal)' }}>
          <span className="w-2 h-2 rounded-full bg-[var(--signal)] rec-dot" />
          Analyzing
        </span>
      </header>

      <main className="flex-1 min-h-0 grid grid-cols-[40%_1fr] gap-[2.4vw] mt-[5vh] z-20">
        {/* 左：马斯克在审视 */}
        <motion.div
          className="relative rounded-md overflow-hidden border border-[var(--line)] bg-black"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
        >
          <img src={muskSkeptical} alt="Evaluator"
               className="breathe w-full h-full object-cover" />
          <div className="scanbar" />
          <div className="absolute inset-x-0 bottom-0 h-1/3 pointer-events-none"
               style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.78), transparent)' }} />
          <div className="absolute left-3 bottom-3 z-10">
            <div className="font-display text-[var(--ink)] leading-none"
                 style={{ fontSize: 'clamp(20px, 2.2vw, 34px)' }}>
              ELON&nbsp;MUSK
            </div>
            <div className="hud-label mt-1" style={{ color: 'var(--signal)' }}>◣ Deconstructing</div>
          </div>
        </motion.div>

        {/* 右：拆解过程 */}
        <div className="flex flex-col min-h-0">
          <motion.div className="hud-label mb-4" style={{ color: 'var(--signal)' }}
                      initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
            ▍First-Principles Breakdown
          </motion.div>
          <motion.h1
            className="font-display text-[var(--ink)] leading-[0.95]"
            style={{ fontSize: 'clamp(34px, 5vw, 76px)' }}
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.6 }}
          >
            正在拆解
            <br />
            <span style={{ color: 'var(--muted)' }}>你的项目</span>
          </motion.h1>
          <motion.p className="text-[var(--muted)] mt-4 leading-relaxed max-w-md"
                    style={{ fontSize: 'clamp(14px, 1.4vw, 18px)' }}
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7 }}>
            把它砍到物理层面，看还剩下什么。
          </motion.p>

          {/* 分析终端 */}
          <div className="mt-6 flex-1 min-h-0 rounded-md border border-[var(--line)] bg-black/40 p-4 overflow-hidden font-hud"
               style={{ fontSize: 'clamp(12px, 1.1vw, 15px)' }}>
            {log.map((l, idx) => {
              const isLast = idx === log.length - 1;
              return (
                <motion.div
                  key={l.id}
                  className="flex items-center gap-2 py-0.5"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: isLast ? 1 : 0.45, x: 0 }}
                  transition={{ duration: 0.35 }}
                  style={{ color: isLast ? 'var(--signal)' : 'var(--muted)' }}
                >
                  <span className="opacity-70">{isLast ? '▸' : '✓'}</span>
                  <span>{l.text}</span>
                  {isLast && <span className="ml-1 rec-dot">_</span>}
                </motion.div>
              );
            })}
          </div>

          {/* 不确定进度条 */}
          <div className="relative h-[3px] mt-4 bg-white/5 overflow-hidden rounded-full">
            <motion.div
              className="absolute top-0 h-full w-1/3 rounded-full"
              style={{ background: 'var(--signal)' }}
              animate={{ x: ['-110%', '320%'] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

export default Thinking;
