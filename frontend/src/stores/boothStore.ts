import { create } from 'zustand';

interface ReviewData {
  transcript?: string;
  fluency?: {
    avg_wpm: number;
    pause_count: number;
    longest_pause_seconds?: number;
    filler_word_count: number;
    filler_examples?: string[];
    stutter_count?: number;
    wpm_volatility?: number;
    summary: string;
  };
  emotion?: {
    tension_index: number;
    smile_index: number;
    overall_emotion: string;
    gaze_at_camera_pct: number;
    head_stability_score?: number;
    summary: string;
  };
  review?: {
    insight: string;
    highlights: string[];
    sharp_question: string;
    suggestions: string[];
    closing: string;
  };
  review_audio?: string;
  photo?: string;
  qr?: string;
  error?: string;
}

type BoothStep = 'welcome' | 'presenting' | 'thinking' | 'reviewing' | 'photo' | 'complete';

interface BoothState {
  step: BoothStep;
  countdown: number;
  data: ReviewData;
}

interface BoothStore extends BoothState {
  updateFromSSE: (state: BoothState) => void;
  setError: (err: string) => void;
}

const initialState: BoothState = {
  step: 'welcome',
  countdown: 0,
  data: {},
};

export const useBoothStore = create<BoothStore>((set) => ({
  ...initialState,

  updateFromSSE: (state: BoothState) =>
    set(() => ({
      step: state.step,
      countdown: state.countdown,
      data: state.data,
    })),

  setError: (err: string) =>
    set(() => ({
      data: { error: err },
    })),
}));
