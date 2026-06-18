import { useCallback, useEffect, useRef, useState } from 'react';

// Soniox WebSocket STT 的 SDK（动态导入）
let SonioxClient: any = null;

interface Token {
  text: string;
  start_ms: number;
  end_ms: number;
  is_final: boolean;
}

interface UseSonioxReturn {
  start: () => void;
  stop: () => { text: string; tokens: Token[] };
  finalText: string;
  interimText: string;
  active: boolean;
  error: string | null;
}

/**
 * Soniox 实时语音转写 Hook。
 * 通过后端 /api/soniox/temp-key 获取临时密钥，建立 WebSocket 连接。
 *
 * 使用方式：
 *   const soniox = useSoniox();
 *   soniox.start();  // 开始识别
 *   const { text, tokens } = soniox.stop();  // 停止并取结果
 */
export function useSoniox(): UseSonioxReturn {
  const [finalText, setFinalText] = useState('');
  const [interimText, setInterimText] = useState('');
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clientRef = useRef<any>(null);
  const finalRef = useRef('');
  const tokensRef = useRef<Token[]>([]);
  const activeRef = useRef(false);

  // 加载 Soniox SDK
  useEffect(() => {
    if (SonioxClient) return;
    import('@soniox/speech-to-text-web').then((mod) => {
      SonioxClient = mod.SonioxClient;
    }).catch(() => {
      setError('Soniox SDK 加载失败');
    });
  }, []);

  const start = useCallback(async () => {
    if (activeRef.current || !SonioxClient) return;

    try {
      // 从后端获取临时 key
      const resp = await fetch('/api/soniox/temp-key', { method: 'POST' });
      if (!resp.ok) {
        setError('Soniox 临时密钥获取失败');
        return;
      }
      const { apiKey } = await resp.json();
      if (!apiKey) {
        setError('Soniox 临时密钥为空');
        return;
      }

      finalRef.current = '';
      tokensRef.current = [];
      setFinalText('');
      setInterimText('');
      setError(null);

      const client = new SonioxClient(apiKey);

      client.on('error', (err: any) => {
        setError(String(err));
      });

      client.on('results', (results: any) => {
        if (!results?.length) return;
        for (const r of results) {
          if (r.is_final) {
            const text = r.text || '';
            finalRef.current += text;
            setFinalText(finalRef.current);

            if (r.tokens) {
              for (const t of r.tokens) {
                tokensRef.current.push({
                  text: t.text || '',
                  start_ms: t.start_ms ?? 0,
                  end_ms: t.end_ms ?? 0,
                  is_final: true,
                });
              }
            }
          } else if (r.text) {
            setInterimText(r.text);
          }
        }
      });

      await client.start({
        audio_params: {
          encoding: 'pcm_s16le',
          sample_rate: 16000,
          channels: 1,
        },
      });

      clientRef.current = client;
      activeRef.current = true;
      setActive(true);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  const stop = useCallback((): { text: string; tokens: Token[] } => {
    const client = clientRef.current;
    if (client) {
      try { client.stop(); } catch { /* ignore */ }
      try { client.close(); } catch { /* ignore */ }
    }
    clientRef.current = null;
    activeRef.current = false;
    setActive(false);
    setInterimText('');

    return {
      text: finalRef.current,
      tokens: tokensRef.current,
    };
  }, []);

  // 清理
  useEffect(() => {
    return () => {
      const client = clientRef.current;
      if (client) {
        try { client.stop(); } catch { /* ignore */ }
        try { client.close(); } catch { /* ignore */ }
      }
    };
  }, []);

  return {
    start,
    stop,
    finalText,
    interimText,
    active,
    error,
  };
}
