'use client';

/**
 * Alert Type Filter Tabs
 *
 * Filter tabs showing alert counts by type.
 */

import React from 'react';

interface AlertTypeTabsProps {
  typeCounts: Record<string, number>;
  selectedTypes: string[];
  onTypeChange: (types: string[]) => void;
}

const TYPE_CONFIG: Record<string, { label: string; color: string }> = {
  structuring: { label: 'Structuring', color: 'bg-red-500' },
  velocity: { label: 'Velocity', color: 'bg-orange-500' },
  sanctions: { label: 'Sanctions', color: 'bg-purple-500' },
  kyc: { label: 'KYC', color: 'bg-blue-500' },
  unusual_behavior: { label: 'Unusual', color: 'bg-yellow-500' },
  geographic: { label: 'Geographic', color: 'bg-green-500' },
};

export function AlertTypeTabs({
  typeCounts,
  selectedTypes,
  onTypeChange,
}: AlertTypeTabsProps) {
  const totalCount = Object.values(typeCounts).reduce((a, b) => a + b, 0);
  const isAllSelected = selectedTypes.length === 0;

  const handleTabClick = (type: string | null) => {
    if (type === null) {
      // All selected
      onTypeChange([]);
    } else if (selectedTypes.includes(type)) {
      // Deselect this type
      const newTypes = selectedTypes.filter((t) => t !== type);
      onTypeChange(newTypes);
    } else {
      // Select this type (add to selection)
      onTypeChange([...selectedTypes, type]);
    }
  };

  return (
    <div className="flex items-center space-x-2 overflow-x-auto pb-2">
      {/* All Tab */}
      <button
        onClick={() => handleTabClick(null)}
        className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
          isAllSelected
            ? 'bg-slate-700 text-white'
            : 'bg-slate-800 text-slate-400 hover:bg-slate-750 hover:text-slate-300'
        }`}
      >
        All
        <span
          className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
            isAllSelected ? 'bg-slate-600' : 'bg-slate-700'
          }`}
        >
          {totalCount}
        </span>
      </button>

      {/* Type Tabs */}
      {Object.entries(typeCounts).map(([type, count]) => {
        const config = TYPE_CONFIG[type] || { label: type, color: 'bg-slate-500' };
        const isSelected = selectedTypes.includes(type);

        return (
          <button
            key={type}
            onClick={() => handleTabClick(type)}
            className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
              isSelected
                ? 'bg-slate-700 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-750 hover:text-slate-300'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${config.color} mr-2`} />
            {config.label}
            <span
              className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                isSelected ? 'bg-slate-600' : 'bg-slate-700'
              }`}
            >
              {count}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export default AlertTypeTabs;
