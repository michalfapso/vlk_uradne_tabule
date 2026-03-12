import React from 'react';

interface GridControlsProps {
  importantOnly: boolean;
  setImportantOnly: (val: boolean) => void;
  krajFilter: string | null;
  setKrajFilter: (val: string | null) => void;
  okresFilter: string | null;
  setOkresFilter: (val: string | null) => void;
  allKraje: string[];
  allOkresy: string[];
  globalFilter: string;
  setGlobalFilter: (val: string) => void;
  rowCount: number;
  totalCount: number;
  isAllExpanded: boolean;
  toggleAllExpanded: () => void;
}

export const GridControls = ({
  importantOnly,
  setImportantOnly,
  krajFilter,
  setKrajFilter,
  okresFilter,
  setOkresFilter,
  allKraje,
  allOkresy,
  globalFilter,
  setGlobalFilter,
  rowCount,
  totalCount,
  isAllExpanded,
  toggleAllExpanded,
}: GridControlsProps) => {
  return (
    <div className="flex flex-col lg:flex-row lg:items-center justify-between bg-white p-4 rounded-xl shadow-md border border-gray-200 gap-4">
      <div className="flex flex-wrap items-center gap-4 lg:gap-6">
        <button 
          onClick={() => setImportantOnly(!importantOnly)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all text-xs font-bold uppercase tracking-wider ${importantOnly ? 'bg-blue-600 text-white border-blue-700 shadow-inner' : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'}`}
        >
          <div className={`w-3 h-3 rounded-full ${importantOnly ? 'bg-white' : 'bg-gray-300'}`} />
          Len dôležité
        </button>

        <div className="flex items-center gap-2">
          <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Kraj:</label>
          <select 
            value={krajFilter || ''} 
            onChange={(e) => { setKrajFilter(e.target.value || null); setOkresFilter(null); }}
            className="text-xs font-semibold p-1.5 border border-gray-200 rounded-lg bg-gray-50 focus:ring-2 focus:ring-blue-500 outline-none"
          >
            <option value="">Všetky</option>
            {allKraje.map(k => <option key={k} value={k}>{k}</option>)}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Okres:</label>
          <select 
            value={okresFilter || ''} 
            onChange={(e) => setOkresFilter(e.target.value || null)}
            className="text-xs font-semibold p-1.5 border border-gray-200 rounded-lg bg-gray-50 focus:ring-2 focus:ring-blue-500 outline-none"
          >
            <option value="">Všetky</option>
            {allOkresy.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>

        <div className="flex items-center gap-2 flex-grow max-w-xs">
          <input 
            type="text"
            value={globalFilter ?? ''}
            onChange={e => setGlobalFilter(e.target.value)}
            placeholder="Hľadať v tabuľke..."
            className="text-xs p-1.5 border border-gray-200 rounded-lg bg-gray-50 focus:ring-2 focus:ring-blue-500 outline-none w-full"
          />
        </div>
      </div>

      <div className="flex items-center justify-between lg:justify-end gap-4 border-t lg:border-t-0 pt-4 lg:pt-0">
        <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest bg-gray-50 px-3 py-1.5 rounded-full border border-gray-100">
          <span className="text-blue-600">{rowCount}</span> / {totalCount} DOKUMENTOV
        </div>
        <button 
          onClick={toggleAllExpanded}
          className="bg-white hover:bg-gray-50 text-gray-700 font-bold py-1.5 px-3 rounded-lg transition-colors text-[10px] uppercase tracking-wider border border-gray-200 shadow-sm"
        >
          {isAllExpanded ? "Zabaliť" : "Rozbaliť"} VŠETKY
        </button>
      </div>
    </div>
  );
};

