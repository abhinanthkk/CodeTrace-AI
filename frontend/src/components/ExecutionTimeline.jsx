import React, { useEffect, useRef } from 'react';

export default function ExecutionTimeline({
  timeline,
  status,
  selectedStep,
  onSelectStep,
}) {
  const listRef = useRef(null);

  // Auto-scroll to selected step
  useEffect(() => {
    if (!selectedStep || !listRef.current) return;
    const el = listRef.current.querySelector(`[data-step="${selectedStep}"]`);
    if (el) {
      el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedStep]);

  if (!timeline || timeline.length === 0) {
    return (
      <div className="h-full flex flex-col">
        <div className="px-3 py-1 text-xs text-gray-500 bg-gray-900 border-b border-gray-800">
          Execution Timeline
        </div>
        <div className="flex-1 flex items-center justify-center text-gray-600 text-sm">
          {status ? 'No execution steps recorded.' : 'Run code to see the execution timeline.'}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1 text-xs text-gray-500 bg-gray-900 border-b border-gray-800 flex justify-between">
        <span>Execution Timeline</span>
        <span className="text-gray-600">{timeline.length} steps</span>
      </div>
      <div ref={listRef} className="flex-1 overflow-auto">
        {timeline.map((step) => (
          <TimelineStep
            key={step.step}
            step={step}
            isSelected={selectedStep === step.step}
            onClick={() => onSelectStep(step.step)}
          />
        ))}
      </div>
    </div>
  );
}

function TimelineStep({ step, isSelected, onClick }) {
  const isError = step.event === 'exception';
  const hasChanges = Object.keys(step.changes || {}).length > 0;
  const hasOutput = (step.output || '').trim().length > 0;

  // Determine icon
  let icon = '●';
  let iconColor = 'text-gray-500';
  if (isError) {
    icon = '◆';
    iconColor = 'text-red-500';
  } else if (hasChanges) {
    icon = '●';
    iconColor = 'text-blue-400';
  } else if (hasOutput) {
    icon = '●';
    iconColor = 'text-green-400';
  } else if (step.event === 'return') {
    icon = '◉';
    iconColor = 'text-purple-400';
  }

  const lineClass = [
    'timeline-step',
    'flex items-start gap-3 px-3 py-2 cursor-pointer border-b border-gray-800/50 text-sm',
    isSelected ? 'selected' : '',
    isError ? 'error' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div data-step={step.step} className={lineClass} onClick={onClick}>
      {/* Icon column */}
      <div className={`mt-0.5 flex-shrink-0 ${iconColor}`}>
        {icon}
      </div>

      {/* Content column */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-600 font-mono">
            Step {step.step}
          </span>
          <span className="text-xs text-gray-500">
            Line {step.line}
          </span>
          <span className={`text-xs px-1 rounded ${isError ? 'bg-red-900/40 text-red-400' : 'bg-gray-800 text-gray-400'}`}>
            {step.event}
          </span>
        </div>

        {/* Changes preview */}
        {hasChanges && (
          <div className="mt-1 text-xs">
            {Object.entries(step.changes).slice(0, 3).map(([name, change]) => (
              <span key={name} className="inline-block mr-2 text-gray-300">
                <span className="text-blue-400">{name}</span>
                <span className="text-gray-600">
                  {' '}
                  {change.type === 'created'
                    ? `= ${formatValue(change.value)}`
                    : change.type === 'updated'
                    ? `: ${formatValue(change.old_value)} → ${formatValue(change.new_value)}`
                    : change.type === 'deleted'
                    ? ' (removed)'
                    : ''}
                </span>
              </span>
            ))}
            {Object.keys(step.changes).length > 3 && (
              <span className="text-gray-600">
                +{Object.keys(step.changes).length - 3} more
              </span>
            )}
          </div>
        )}

        {/* Output preview */}
        {hasOutput && (
          <div className="mt-0.5 text-xs text-green-400 font-mono truncate">
            → {step.output.trim().slice(0, 60)}
          </div>
        )}

        {/* Exception preview */}
        {isError && step.exception && (
          <div className="mt-0.5 text-xs text-red-400 font-medium">
            {step.exception.type}: {step.exception.message}
          </div>
        )}
      </div>
    </div>
  );
}

function formatValue(val) {
  if (val === null) return 'null';
  if (val === undefined) return 'undefined';
  if (typeof val === 'string') {
    return val.length > 25 ? `"${val.slice(0, 25)}..."` : `"${val}"`;
  }
  if (Array.isArray(val)) {
    return `[${val.length} items]`;
  }
  return String(val).slice(0, 30);
}
