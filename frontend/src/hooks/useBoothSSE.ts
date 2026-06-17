import { useEffect, useRef } from 'react';
import { useBoothStore } from '../stores/boothStore';

interface BoothState {
  step: 'welcome' | 'presenting' | 'thinking' | 'reviewing' | 'photo' | 'complete';
  countdown: number;
  data: {
    transcript?: string;
    fluency?: {
      avg_wpm: number;
      pause_count: number;
      filler_word_count: number;
      summary: string;
    };
    emotion?: {
      tension_index: number;
      smile_index: number;
      overall_emotion: string;
      gaze_at_camera_pct: number;
      summary: string;
    };
    review?: {
      insight: string;
      highlights: string[];
      sharp_question: string;
      suggestions: string[];
      closing: string;
    };
    photo?: string;
    qr?: string;
    error?: string;
  };
}

export function useBoothSSE(): void {
  const updateFromSSE = useBoothStore((state) => state.updateFromSSE);
  const setError = useBoothStore((state) => state.setError);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let isMounted = true;

    function connect(): void {
      if (!isMounted) return;

      const es = new EventSource('/api/stream');
      eventSourceRef.current = es;

      es.onmessage = (event: MessageEvent) => {
        if (!isMounted) return;
        try {
          const parsed: BoothState = JSON.parse(event.data);
          updateFromSSE(parsed);
        } catch {
          setError('Failed to parse server message');
        }
      };

      es.onerror = () => {
        es.close();
        eventSourceRef.current = null;
        if (isMounted) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 3000);
        }
      };
    }

    connect();

    return () => {
      isMounted = false;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [updateFromSSE, setError]);
}
