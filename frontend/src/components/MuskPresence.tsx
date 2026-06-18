import { useEffect, useRef, useState } from 'react';
import { MUSK_LINES } from '../data/muskLines';

/**
 * 马斯克"在场"面板：
 * - 头像（默认占位 SVG 线稿；传入 neutralSrc/skepticalSrc 即用真图）
 * - 呼吸光环 + REC 标记 + 扫描，营造"被盯着"
 * - 路演中随机淡入马斯克短句（active 时启动），插话时切换到"挑眉"表情
 *
 * 替换真图：把 musk_neutral.png / musk_skeptical.png 放进 src/assets/，
 * 在 Presenting 里 import 后作为 props 传进来即可。
 */
interface Props {
  active: boolean;
  neutralSrc?: string;
  skepticalSrc?: string;
}

export default function MuskPresence({ active, neutralSrc, skepticalSrc }: Props) {
  const [line, setLine] = useState<string | null>(null);
  const [speaking, setSpeaking] = useState(false);
  const keyRef = useRef(0);

  useEffect(() => {
    if (!active) {
      setLine(null);
      setSpeaking(false);
      return;
    }
    let timer: ReturnType<typeof setTimeout>;
    const schedule = () => {
      // 12~22s 随机间隔来一句（别太频繁，留白）
      const delay = 12000 + Math.random() * 10000;
      timer = setTimeout(() => {
        keyRef.current += 1;
        setLine(MUSK_LINES[Math.floor(Math.random() * MUSK_LINES.length)]);
        setSpeaking(true);
        setTimeout(() => setSpeaking(false), 3000);
        schedule();
      }, delay);
    };
    schedule();
    return () => clearTimeout(timer);
  }, [active]);

  // 固定用 neutral（两张图构图不一致，硬切会"头一跳"）；说话用光效表达。
  const portraitSrc = neutralSrc ?? skepticalSrc;

  return (
    <div className="relative h-full flex flex-col">
      {/* 头部标识 */}
      <div className="flex items-center justify-between px-1 mb-3">
        <div className="hud-label">Evaluator</div>
        <div className="flex items-center gap-1.5">
          <span className="rec-dot w-2 h-2 rounded-full bg-[var(--signal)]" />
          <span className="hud-label" style={{ color: 'var(--signal)' }}>Live</span>
        </div>
      </div>

      {/* 头像舞台（真图自带 HUD 光环，这里不再叠加额外光环/扫描，避免过强） */}
      <div className="relative flex-1 min-h-0 rounded-md overflow-hidden border border-[var(--line)] bg-black">
        <div className="absolute inset-0 flex items-center justify-center">
          {portraitSrc ? (
            <img src={portraitSrc} alt="Evaluator" className="breathe w-full h-full object-cover" />
          ) : (
            <PlaceholderPortrait speaking={speaking} />
          )}
        </div>

        {/* 说话时：红色内发光（代替切表情，避免头一跳） */}
        <div
          className="absolute inset-0 pointer-events-none transition-opacity duration-500"
          style={{
            opacity: speaking ? 1 : 0,
            boxShadow: 'inset 0 0 70px rgba(255,43,43,0.45)',
            border: '1px solid rgba(255,43,43,0.55)',
          }}
        />

        {/* 底部轻微压暗，让名牌更清楚 */}
        <div className="absolute inset-x-0 bottom-0 h-1/3 pointer-events-none"
             style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.75), transparent)' }} />

        {/* 名牌 */}
        <div className="absolute left-3 bottom-3 z-10">
          <div className="font-display text-[var(--ink)] leading-none"
               style={{ fontSize: 'clamp(20px, 2.2vw, 34px)' }}>
            ELON&nbsp;MUSK
          </div>
          <div className="hud-label mt-1">x.ai · Reviewer #01</div>
        </div>

        {/* 状态角标 */}
        <div className="absolute right-3 top-3 hud-label z-10"
             style={{ color: speaking ? 'var(--signal)' : 'var(--hud)' }}>
          {speaking ? '◣ SPEAKING' : '◉ OBSERVING'}
        </div>
      </div>

      {/* 插话气泡 */}
      <div className="mt-3 min-h-[64px] flex items-center">
        {line && (
          <div key={keyRef.current} className="interject-in w-full">
            <div className="hud-label mb-1" style={{ color: 'var(--signal)' }}>Elon ──</div>
            <div className="font-display glow-red leading-tight"
                 style={{ color: 'var(--signal)', fontSize: 'clamp(22px, 2.6vw, 40px)' }}>
              “{line}”
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* 占位线稿头像（真图来之前用）。简洁面部轮廓 + 会眨的眼睛。 */
function PlaceholderPortrait({ speaking }: { speaking: boolean }) {
  const stroke = speaking ? 'var(--signal)' : 'var(--hud)';
  return (
    <svg viewBox="0 0 200 240" className="breathe h-[90%]" fill="none">
      <g stroke={stroke} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
         style={{ filter: 'drop-shadow(0 0 8px rgba(255,43,43,0.25))' }}>
        {/* 头/脸轮廓 */}
        <path d="M100 30 C140 30 158 64 158 104 C158 150 134 196 100 196 C66 196 42 150 42 104 C42 64 60 30 100 30 Z" />
        {/* 发际 */}
        <path d="M62 60 C78 44 122 44 138 60" opacity="0.7" />
        {/* 眉 */}
        <path d="M64 96 C72 90 86 90 94 95" />
        <path d="M106 95 C114 90 128 90 136 96" transform={speaking ? 'translate(0,-6) rotate(-6 121 92)' : ''} />
        {/* 眼睛（会眨） */}
        <g className="blink">
          <path d="M68 108 C76 102 88 102 94 108" />
          <path d="M106 108 C112 102 124 102 132 108" />
        </g>
        {/* 鼻 */}
        <path d="M100 110 L100 136 C96 142 104 142 100 136" opacity="0.7" />
        {/* 嘴：观察=平直线，插话=不屑下撇 */}
        {speaking
          ? <path d="M82 162 C92 156 112 170 120 158" />
          : <path d="M84 162 L118 162" />}
        {/* 颌线点缀 */}
        <path d="M70 170 C84 188 116 188 132 170" opacity="0.4" />
      </g>
    </svg>
  );
}
