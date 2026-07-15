import React from 'react';

export default function InputPanel({ value, onChange, disabled }) {
  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1 text-xs text-gray-500 bg-gray-900 border-b border-gray-800">
        Program Input (stdin)
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder="Enter stdin data here...&#10;Example:&#10;Abhinanth&#10;20"
        className="flex-1 w-full bg-gray-950 text-gray-200 text-sm p-3 resize-none
                   placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-600
                   disabled:opacity-50 font-mono"
        spellCheck={false}
      />
    </div>
  );
}
