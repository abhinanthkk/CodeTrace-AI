import React from 'react';

const STATUS_CONFIG = {
  live: { text: 'LIVE', color: 'text-green-400', dot: 'bg-green-400' },
  checking: { text: 'CHECKING', color: 'text-yellow-400', dot: 'bg-yellow-400 animate-pulse' },
  clean: { text: 'NO ISSUES', color: 'text-green-400', dot: 'bg-green-400' },
  issues: { text: null, color: 'text-orange-400', dot: 'bg-orange-400' }, // text set dynamically
  unavailable: { text: 'LINT UNAVAILABLE', color: 'text-gray-500', dot: 'bg-gray-500' },
};

export default function LiveStatus({ lintStatus, issueCount }) {
  const config = STATUS_CONFIG[lintStatus] || STATUS_CONFIG.live;

  let text = config.text;
  if (lintStatus === 'issues' && issueCount > 0) {
    text = `${issueCount} ISSUE${issueCount !== 1 ? 'S' : ''}`;
  }

  return (
    <span className={`flex items-center gap-1.5 text-xs ${config.color}`}>
      <span className={`w-2 h-2 rounded-full ${config.dot}`} />
      {text}
    </span>
  );
}
