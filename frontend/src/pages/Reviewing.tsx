import { useCallback, useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useBoothStore } from '../stores/boothStore';

const EMOTION_LABEL: Record<string, string> = {
  relaxed_confident: '自信放松',
  slightly_nervous: '略显紧张',
  tense: '紧张',
  neutral: '情绪平稳',
};

// 按"好坏程度"(0-100，越高越好)给梯度颜色：绿 → 琥珀 → 红
function toneColor(goodness: number): string {
  if (goodness >= 66) return '#39ff8b';
  if (goodness >= 33) return '#ffb13b';
  return '#ff4d4d';
}
const EMOTION_COLOR: Record<string, string> = {
  relaxed_confident: '#39ff8b',
  slightly_nervous: '#ffb13b',
  tense: '#ff4d4d',
  neutral: 'var(--hud)',
};

function Reviewing() {
  const data = useBoothStore((state) => state.data);
  const review = data.review;
  const fluency = data.fluency;
  const emotion = data.emotion;
  const audioUrl = data.review_audio;
  const postedRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!audioUrl || !audioRef.current) return;
    audioRef.current.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
  }, [audioUrl]);

  const toggleAudio = useCallback(() => {
    const a = audioRef.current;
    if (!a) return;
    if (a.paused) a.play().catch(() => {});
    else a.pause();
  }, []);

  const handleContinue = useCallback(() => {
    if (postedRef.current) return;
    postedRef.current = true;
    fetch('/api/step/reviewing/complete', { method: 'POST' }).catch(() => {
      useBoothStore.getState().setError('Failed to complete review');
    });
  }, []);

  if (!review) {
    return (
      <div className="chamber w-full h-full flex items-center justify-center relative">
        <div className="grain" />
        <div className="text-center z-20">
          <div className="hud-label mb-3" style={{ color: 'var(--signal)' }}>Compiling Verdict</div>
          <motion.div
            className="font-display text-[var(--muted)]"
            style={{ fontSize: 'clamp(28px,4vw,56px)' }}
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 1.6, repeat: Infinity }}
          >
            正在整理评审…
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="chamber w-full h-full relative flex flex-col">
      <div className="grain" />
      {/* 顶栏 */}
      <header className="absolute top-[2.4vh] left-[3vw] right-[3vw] flex items-center justify-between z-30">
        <span className="font-display text-2xl leading-none">
          <span style={{ color: 'var(--signal)' }}>X</span>
          <span className="text-[var(--ink)]">.AI</span>
        </span>
        <span className="hud-label">Final Verdict</span>
      </header>

      <div className="flex-1 min-h-0 overflow-y-auto px-[4vw] pt-[8.5vh] pb-12 z-20">
        <div className="max-w-[1200px] mx-auto">
          {/* 标题 + 朗读 */}
          <div className="flex items-end justify-between flex-wrap gap-4 mb-8">
            <div>
              <motion.div className="hud-label mb-2" style={{ color: 'var(--signal)' }}
                          initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                ▍马斯克已看完
              </motion.div>
              <motion.h1 className="font-display text-[var(--ink)] leading-none"
                         style={{ fontSize: 'clamp(40px,5.5vw,84px)' }}
                         initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                         transition={{ duration: 0.5 }}>
                他的<span className="glow-red" style={{ color: 'var(--signal)' }}>判决</span>
              </motion.h1>
            </div>

            {audioUrl && (
              <div className="flex items-center gap-3">
                <audio ref={audioRef} src={audioUrl}
                       onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
                       onEnded={() => setPlaying(false)} />
                <button onClick={toggleAudio}
                        className="inline-flex items-center gap-2 px-5 py-2.5 border border-[var(--signal)] text-[var(--signal)] font-hud text-sm tracking-[0.15em] hover:bg-[var(--signal)] hover:text-black transition-colors">
                  {playing ? '⏸ 暂停' : '▶ 听他说'}
                </button>
                {playing && (
                  <span className="flex items-end gap-0.5 h-5" aria-hidden>
                    {[0, 1, 2, 3].map((i) => (
                      <motion.span key={i} className="w-0.5 bg-[var(--signal)]"
                                   animate={{ height: ['30%', '100%', '30%'] }}
                                   transition={{ duration: 0.7, repeat: Infinity, delay: i * 0.12 }} />
                    ))}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* 主体：评审 + 表现 */}
          <div className="grid grid-cols-1 lg:grid-cols-[1.7fr_1fr] gap-[2vw] items-start">
            {/* 左：评审 */}
            <motion.div className="flex flex-col gap-4"
                        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.15, duration: 0.5 }}>
              {/* 洞察（头条） */}
              <div className="rounded-md border border-[var(--signal)]/40 bg-[var(--signal-dim)] px-6 py-5">
                <div className="hud-label mb-2" style={{ color: 'var(--signal)' }}>One-line Insight · 本质洞察</div>
                <div className="font-display text-[var(--ink)] leading-tight"
                     style={{ fontSize: 'clamp(22px,2.6vw,40px)' }}>
                  {review.insight}
                </div>
              </div>

              <Section title="Hardcore Highlights · 硬核亮点">
                {review.highlights?.length ? (
                  <ul className="space-y-2">
                    {review.highlights.map((h, i) => (
                      <li key={i} className="flex gap-2 text-[var(--ink)]" style={{ fontSize: 'clamp(14px,1.3vw,18px)' }}>
                        <span style={{ color: 'var(--signal)' }}>▸</span><span>{h}</span>
                      </li>
                    ))}
                  </ul>
                ) : <Empty text="没听到值得说的亮点。" />}
              </Section>

              <Section title="Sharp Question · 尖锐提问" accent>
                <p className="text-[var(--signal-soft)] leading-snug" style={{ fontSize: 'clamp(16px,1.6vw,24px)' }}>
                  “{review.sharp_question}”
                </p>
              </Section>

              <Section title="Hardcore Suggestions · 硬核建议">
                {review.suggestions?.length ? (
                  <ul className="space-y-2">
                    {review.suggestions.map((s, i) => (
                      <li key={i} className="flex gap-2 text-[var(--ink)]" style={{ fontSize: 'clamp(14px,1.3vw,18px)' }}>
                        <span style={{ color: 'var(--signal)' }}>{i + 1}.</span><span>{s}</span>
                      </li>
                    ))}
                  </ul>
                ) : <Empty text="—" />}
              </Section>

              <Section title="Closing · 结语">
                <p className="text-[var(--ink)] leading-snug" style={{ fontSize: 'clamp(16px,1.6vw,24px)' }}>
                  {review.closing}
                </p>
              </Section>
            </motion.div>

            {/* 右：你的表现 */}
            <motion.div
              className="rounded-md border border-[var(--line)] bg-black/30 p-5 lg:sticky lg:top-2"
              initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3, duration: 0.5 }}
            >
              <div className="hud-label mb-4" style={{ color: 'var(--signal)' }}>Your Performance · 你的表现</div>

              {emotion ? (
                <>
                  <div className="mb-4">
                    <div className="hud-label">综合状态</div>
                    <div className="font-display leading-none mt-1"
                         style={{ fontSize: 'clamp(22px,2vw,32px)', color: EMOTION_COLOR[emotion.overall_emotion] || 'var(--ink)' }}>
                      {EMOTION_LABEL[emotion.overall_emotion] || emotion.overall_emotion}
                    </div>
                  </div>
                  <Bar label="看镜头" value={emotion.gaze_at_camera_pct} suffix="%" />
                  <Bar label="头部稳定" value={emotion.head_stability_score ?? 0} suffix="/100" />
                  <Bar label="微笑度" value={emotion.smile_index * 100} suffix="%" />
                  <Bar
                    label="紧张度"
                    value={emotion.tension_index * 100}
                    suffix="%"
                    goodness={Math.max(0, Math.min(100, (1 - emotion.tension_index / 0.6) * 100))}
                  />
                </>
              ) : <Empty text="未采集到面部数据" />}

              <div className="h-px bg-white/8 my-4" />

              {fluency ? (
                <div className="grid grid-cols-3 gap-2 text-center">
                  <Metric label="语速" value={Math.round(fluency.avg_wpm)} unit="字/分" />
                  <Metric label="停顿" value={fluency.pause_count} unit="次" />
                  <Metric label="口头禅" value={fluency.filler_word_count} unit="次" />
                </div>
              ) : <Empty text="未采集到语音数据" />}

              {(fluency?.summary || emotion?.summary) && (
                <p className="mt-4 text-[var(--muted)] leading-relaxed" style={{ fontSize: '12px' }}>
                  {fluency?.summary}{fluency?.summary && emotion?.summary ? '；' : ''}{emotion?.summary}
                </p>
              )}
            </motion.div>
          </div>

          {/* 继续 */}
          <div className="flex justify-center mt-10">
            <motion.button onClick={handleContinue}
              className="inline-flex items-center gap-2 px-9 py-3.5 border border-white/20 text-[var(--muted)] font-hud tracking-[0.2em] uppercase text-sm hover:border-[var(--signal)] hover:text-[var(--signal)] transition-colors"
              initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
              去合影 ▸
            </motion.button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children, accent }: { title: string; children: React.ReactNode; accent?: boolean }) {
  return (
    <div className={`rounded-md border px-6 py-4 ${accent ? 'border-[var(--signal)]/30 bg-[var(--signal-dim)]' : 'border-[var(--line)] bg-black/25'}`}>
      <div className="hud-label mb-2" style={{ color: accent ? 'var(--signal)' : 'var(--hud)' }}>{title}</div>
      {children}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-[var(--muted)]" style={{ fontSize: '14px' }}>{text}</p>;
}

function Bar({ label, value, suffix = '', invert, goodness }: { label: string; value: number; suffix?: string; invert?: boolean; goodness?: number }) {
  const pct = Math.max(0, Math.min(100, value));
  // goodness：0-100，越高越好；不传则按方向从 value 推（invert=越低越好）
  const g = goodness !== undefined ? goodness : invert ? 100 - pct : pct;
  const color = toneColor(g);
  return (
    <div className="mb-3">
      <div className="flex justify-between items-baseline mb-1">
        <span className="hud-label">{label}</span>
        <span className="font-hud tabular-nums" style={{ color, fontSize: '13px' }}>
          {Math.round(value)}{suffix}
        </span>
      </div>
      <div className="h-1.5 bg-white/8 rounded-full overflow-hidden">
        <motion.div className="h-full rounded-full" style={{ background: color }}
                    initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8, ease: 'easeOut' }} />
      </div>
    </div>
  );
}

function Metric({ label, value, unit }: { label: string; value: number; unit: string }) {
  return (
    <div>
      <div className="font-display text-[var(--ink)] leading-none" style={{ fontSize: 'clamp(20px,1.8vw,30px)' }}>{value}</div>
      <div className="hud-label mt-1">{label}</div>
      <div className="text-[var(--muted)]" style={{ fontSize: '10px' }}>{unit}</div>
    </div>
  );
}

export default Reviewing;
