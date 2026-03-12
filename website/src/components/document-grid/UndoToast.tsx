import React from 'react';

interface UndoToastProps {
  showUndo: boolean;
  onUndo: () => void;
  onClose: () => void;
}

export const UndoToast = ({ showUndo, onUndo, onClose }: UndoToastProps) => {
  if (!showUndo) return null;
  
  return (
    <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-50 animate-in fade-in slide-in-from-bottom-4 duration-300">
      <div className="bg-gray-900 text-white px-6 py-3 rounded-full shadow-2xl flex items-center gap-4 border border-gray-700">
        <span className="text-sm font-medium">Zmena značky uložená</span>
        <button 
          onClick={onUndo}
          className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-3 py-1 rounded-full transition-colors uppercase tracking-wider"
        >
          Späť
        </button>
        <button 
          onClick={onClose}
          className="text-gray-400 hover:text-white transition-colors"
        >
          ✕
        </button>
      </div>
    </div>
  );
};
