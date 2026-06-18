/** 马斯克在场时随机穿插的旁白 */
export const MUSK_LINES: string[] = [
  'Hmm, interesting…',
  'Not bad, not bad.',
  'I\'ve seen this before.',
  'Get to the point.',
  'Is that all you\'ve got?',
  'I like the ambition.',
  'Bold move. Let\'s see if it pays off.',
  'I\'d invest in that.',
  'That\'s actually… clever.',
  'Keep going.',
  'You have my attention.',
  'I\'m not impressed yet.',
  'Now you\'re thinking.',
  'That\'s a first-principles approach. Good.',
  'I\'d fire whoever designed that.',
  'Ship it.',
  'This could be big.',
  'Needs more engineering.',
  'Show me the demo.',
  'Interesting approach.',
];

export function getRandomLine(): string {
  return MUSK_LINES[Math.floor(Math.random() * MUSK_LINES.length)];
}

// 按路演进度分段的旁白
export const PHASE_LINES: Record<string, string[]> = {
  opening: [
    'Let\'s see what you\'ve got.',
    'You have 60 seconds. Don\'t waste them.',
    'Alright, impress me.',
  ],
  middle: [
    'I\'m listening.',
    'Get to the hard part.',
    'Cut the fluff.',
    'Show me the numbers.',
  ],
  closing: [
    'Time\'s almost up.',
    'Give me your best final point.',
    'Make it count.',
  ],
};
