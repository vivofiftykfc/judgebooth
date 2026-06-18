import { useRef, useState } from 'react';
import { SonioxClient } from '@soniox/speech-to-text-web';

interface SonioxToken {
  text: string;
  start_ms?: number;
  end_ms?: number;
  is_final: boolean;
}

/**
 * Soniox 浏览器端实时转写（stt-rt-v5）。
 * - 用后端 /api/soniox/temp-key 换临时 key 建立 WebSocket（真 key 不进前端）
 * - 实时给出 finalText（已定稿）+ interimText（试探中）做实时字幕
 * - stop() 返回最终文本 + 词级 token，交给后端做流畅度/评审
 */
export function useSoniox() {
  const clientRef = useRef<SonioxClient | null>(null);
  const finalTokensRef = useRef<SonioxToken[]>([]);
  const [finalText, setFinalText] = useState('');
  const [interimText, setInterimText] = useState('');
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function start() {
    finalTokensRef.current = [];
    setFinalText('');
    setInterimText('');
    setError(null);

    const client = new SonioxClient({
      apiKey: async () => {
        const r = await fetch('/api/soniox/temp-key', { method: 'POST' });
        if (!r.ok) throw new Error('temp-key 获取失败');
        const d = await r.json();
        return d.apiKey as string;
      },
    });
    clientRef.current = client;

    client.start({
      model: 'stt-rt-v5',
      languageHints: ['zh', 'en'],
      onStarted: () => setActive(true),
      onFinished: () => setActive(false),
      onError: (status: string, message: string) => {
        console.error('[soniox]', status, message);
        setError(`${status}: ${message}`);
        setActive(false);
      },
      onPartialResult: (result: { tokens: SonioxToken[] }) => {
        let interim = '';
        for (const t of result.tokens) {
          if (t.is_final) finalTokensRef.current.push(t);
          else interim += t.text;
        }
        setFinalText(finalTokensRef.current.map((t) => t.text).join(''));
        setInterimText(interim);
      },
    });
  }

  /** 停止并返回最终文本 + 词级 token。 */
  function stop(): { text: string; tokens: SonioxToken[] } {
    try {
      clientRef.current?.stop();
    } catch {
      /* ignore */
    }
    clientRef.current = null;
    setActive(false);
    const tokens = finalTokensRef.current;
    return { text: tokens.map((t) => t.text).join(''), tokens };
  }

  return { start, stop, finalText, interimText, active, error };
}
