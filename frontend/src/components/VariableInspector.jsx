import React from 'react';

export default function VariableInspector({ variables, changes }) {
  const varNames = Object.keys(variables);
  const changeNames = Object.keys(changes);

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1 text-xs text-gray-500 bg-gray-900 border-b border-gray-800">
        Variable Inspector
      </div>
      <div className="flex-1 overflow-auto p-3">
        {varNames.length === 0 ? (
          <p className="text-gray-600 text-sm italic">No variables at this step.</p>
        ) : (
          <div className="space-y-2">
            {varNames.map((name) => {
              const change = changes[name];
              const isNew = change?.type === 'created';
              const isUpdated = change?.type === 'updated';
              const isDeleted = change?.type === 'deleted';
              const value = variables[name];

              return (
                <div
                  key={name}
                  className={`rounded border px-3 py-2 text-sm ${
                    isNew
                      ? 'border-green-800 bg-green-900/20'
                      : isUpdated
                      ? 'border-blue-800 bg-blue-900/20'
                      : isDeleted
                      ? 'border-red-800 bg-red-900/20'
                      : 'border-gray-800 bg-gray-900/50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-medium text-gray-200">
                      {name}
                    </span>
                    {isNew && (
                      <span className="text-xs px-1 rounded bg-green-900/50 text-green-400">
                        new
                      </span>
                    )}
                    {isUpdated && (
                      <span className="text-xs px-1 rounded bg-blue-900/50 text-blue-400">
                        changed
                      </span>
                    )}
                    {isDeleted && (
                      <span className="text-xs px-1 rounded bg-red-900/50 text-red-400">
                        removed
                      </span>
                    )}
                    <span className="text-xs text-gray-600 font-mono">
                      {typeLabel(value)}
                    </span>
                  </div>
                  <div className="mt-1 font-mono text-xs">
                    {isUpdated ? (
                      <div>
                        <span className="text-red-400 line-through">
                          {formatValue(change.old_value)}
                        </span>
                        <span className="text-gray-600 mx-1">→</span>
                        <span className="text-green-400">
                          {formatValue(change.new_value)}
                        </span>
                      </div>
                    ) : (
                      <span className="text-gray-400">
                        {formatValue(value)}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function typeLabel(val) {
  if (val === null) return 'None';
  if (val === undefined) return 'undefined';
  if (Array.isArray(val)) return `list[${val.length}]`;
  const t = typeof val;
  if (t === 'object') return val?.constructor?.name || 'object';
  return t;
}

function formatValue(val, depth = 0) {
  if (depth > 2) return '...';
  if (val === null) return <span className="text-gray-500">None</span>;
  if (val === undefined) return <span className="text-gray-500">—</span>;
  if (typeof val === 'string') {
    if (val.length > 80) return `"${val.slice(0, 80)}..."`;
    return <span className="text-green-400">"{val}"</span>;
  }
  if (typeof val === 'number') return <span className="text-yellow-400">{val}</span>;
  if (typeof val === 'boolean') return <span className="text-purple-400">{String(val)}</span>;
  if (Array.isArray(val)) {
    if (val.length === 0) return <span className="text-gray-500">[]</span>;
    const items = val.slice(0, 5).map((v, i) => (
      <span key={i}>
        {formatValue(v, depth + 1)}
        {i < Math.min(val.length, 5) - 1 ? ', ' : ''}
      </span>
    ));
    return (
      <span>
        <span className="text-gray-500">[</span>
        {items}
        {val.length > 5 && <span className="text-gray-600">, ...{val.length - 5} more</span>}
        <span className="text-gray-500">]</span>
      </span>
    );
  }
  if (typeof val === 'object') {
    const keys = Object.keys(val).slice(0, 3);
    return (
      <span>
        <span className="text-gray-500">{'{'}</span>
        {keys.map((k, i) => (
          <span key={k}>
            <span className="text-blue-300">{k}</span>
            <span className="text-gray-500">: </span>
            {formatValue(val[k], depth + 1)}
            {i < keys.length - 1 ? ', ' : ''}
          </span>
        ))}
        {Object.keys(val).length > 3 && (
          <span className="text-gray-600">, ...</span>
        )}
        <span className="text-gray-500">{'}'}</span>
      </span>
    );
  }
  return String(val);
}
