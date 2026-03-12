import React from 'react';
import { tagOptions } from './constants';

export const TagActionBar = ({ 
  docId, 
  datum, 
  currentTag, 
  onTagChange, 
  isPending, 
  hideLabel = false,
  labelSide = false
}: { 
  docId: string, 
  datum: string, 
  currentTag: string | null, 
  onTagChange: (docId: string, datum: string, newTag: string | null, currentTag: string | null) => void,
  isPending: boolean,
  hideLabel?: boolean,
  labelSide?: boolean 
}) => {
  const activeOption = tagOptions.find(opt => opt.value === currentTag) || tagOptions[0];

  return (
    <div className={`flex ${labelSide ? 'flex-row items-center gap-2' : 'flex-col gap-1'} ${isPending ? 'animate-pulse bg-yellow-50 rounded p-1' : ''}`}>
      <div className="flex items-center gap-1">
        {tagOptions.map(opt => (
          <button
            key={opt.label}
            onClick={(e) => {
              e.stopPropagation();
              onTagChange(docId, datum, opt.value, currentTag);
            }}
            title={opt.label}
            className={`w-7 h-7 flex items-center justify-center rounded-md border transition-all hover:scale-110 ${currentTag === opt.value ? `bg-white shadow-sm border-blue-400 scale-110` : 'bg-gray-50 border-gray-200 opacity-60 hover:opacity-100'}`}
          >
            <span className={`text-sm ${opt.icon === '✖' && currentTag !== opt.value ? 'text-gray-300' : opt.color}`}>{opt.icon}</span>
          </button>
        ))}
      </div>
      {!hideLabel && (
        <div className={`text-[9px] font-bold uppercase px-1 whitespace-nowrap ${currentTag ? activeOption.color : 'text-gray-500'}`}>
          {currentTag ? activeOption.label : 'Bez značky'}
        </div>
      )}
    </div>
  );
};


