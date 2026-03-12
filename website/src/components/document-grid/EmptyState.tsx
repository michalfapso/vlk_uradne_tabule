import React from 'react';

interface EmptyStateProps {
  onClearFilters: () => void;
}

export const EmptyState = ({ onClearFilters }: EmptyStateProps) => {
  return (
    <div className="text-center py-20 bg-white rounded-xl shadow-inner border border-dashed border-gray-300">
      <div className="text-4xl mb-4">🔍</div>
      <div className="text-gray-500 font-bold uppercase tracking-widest text-sm">Nenašli sa žiadne dokumenty</div>
      <button 
        onClick={onClearFilters}
        className="mt-4 text-blue-600 font-bold text-xs uppercase hover:underline"
      >
        Zrušiť všetky filtre
      </button>
    </div>
  );
};

