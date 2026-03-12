import React from 'react';
import { TagActionBar } from './TagActionBar';
import { ExpandedRowContent } from './ExpandedRowContent';
import { categoryColors } from './constants';
import { formatDate, getBorderColorClass } from './utils';

export const EvaluationCard = ({ 
  row, 
  onTagChange, 
  isPending, 
  isAuthenticated,
  highlightedDocId,
  onLinkClick
}: { 
  row: any, 
  onTagChange: (docId: string, datum: string, newTag: string | null, currentTag: string | null) => void,
  isPending: boolean,
  isAuthenticated: boolean,
  highlightedDocId: string | null,
  onLinkClick: (docId: string) => void
}) => {
  const data = row.original;
  const a = data.analyza || {};
  const isExpanded = row.getIsExpanded();
  const borderColorClass = getBorderColorClass(data);
  const isHighlighted = data.docId === highlightedDocId;

  return (
    <div 
      id={`doc-${data.docId}`}
      className={`bg-white rounded-xl shadow-md border-l-4 overflow-hidden transition-all duration-700 w-full cursor-pointer ${borderColorClass} ${isPending ? 'opacity-0 max-h-0 mb-0 pointer-events-none' : 'opacity-100 mb-4'} ${isHighlighted ? 'ring-2 ring-blue-500 ring-inset bg-blue-50' : ''} ${!data.isImportant && !isPending ? 'grayscale-[0.3]' : ''} ${isExpanded ? 'max-h-none' : 'max-h-[1000px]'}`}
      onClick={() => row.toggleExpanded()}
    >
      <div className={`p-4 transition-all duration-700 ${isPending ? 'py-0' : 'py-4'}`}>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mb-3">
          <div className="text-xs font-bold text-gray-500 uppercase whitespace-nowrap">{formatDate(data.datum_display)}</div>
          {isAuthenticated && (
            <div onClick={e => e.stopPropagation()}>
              <TagActionBar 
                docId={data.docId} 
                datum={data.datum_display} 
                currentTag={data.myTag} 
                onTagChange={onTagChange}
                isPending={isPending}
                labelSide={true} 
              />
            </div>
          )}
          <div className="flex flex-wrap gap-1">
            {(a.kategorie_vlk || []).map((cat: string, idx: number) => (
              <span key={idx} className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase ${categoryColors[cat] || 'bg-gray-200 text-gray-700'}`}>
                {cat}
              </span>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-1">
            {/* Ochrana Badges */}
            {a.gis?.zasiahnute_chranene_uzemia?.['5st_konsUEV'] && <span className="px-1.5 py-0.5 bg-red-700 text-white rounded text-[8px] font-bold uppercase shadow-sm">5. STUPEŇ!</span>}
            {(a.gis?.zasiahnute_chranene_uzemia?.['UEV'] || a.gis?.zasiahnute_chranene_uzemia?.['CHVU']) && <span className="px-1.5 py-0.5 bg-green-700 text-white rounded text-[8px] font-bold uppercase shadow-sm">Natura 2000</span>}
            
            {data.hasGis && (
              <a 
                href={`https://michalfapso.github.io/vlk_zonacia_tanap/?ext_url=https://michalfapso.github.io/vlk_uradne_tabule/data/${data.docId}/gis.geojson&ext_crs=EPSG:4326`}
                target="_blank"
                onClick={(e) => e.stopPropagation()}
                className="px-1.5 py-0.5 bg-blue-100 text-blue-800 border border-blue-200 rounded text-[8px] font-bold uppercase shadow-sm hover:bg-blue-200 transition-colors cursor-pointer no-underline"
              >
                🗺️ MAPA
              </a>
            )}
          </div>
        </div>
        
        <h4 className="text-sm font-bold text-gray-900 mb-2 leading-snug line-clamp-2">
          {Array.isArray(a.typ_zasahu) ? a.typ_zasahu.join(", ") : (a.typ_zasahu || data.nazov || "-")}
        </h4>

        <div className="flex flex-col sm:flex-row sm:flex-wrap gap-x-6 gap-y-2 text-[11px] mb-1">
          <div className="flex items-center gap-2">
            <span className="text-gray-500 text-[9px] uppercase font-bold tracking-tighter whitespace-nowrap">Lokalita:</span>
            <span className="font-bold text-gray-800">{a.miesto_realizacie?.obec || "-"}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-500 text-[9px] uppercase font-bold tracking-tighter whitespace-nowrap">Žiadateľ:</span>
            <span className="font-medium text-blue-800 line-clamp-1">{a.ziadatel_navrhovatel || "-"}</span>
          </div>
        </div>
      </div>
      
      {isExpanded && (
        <div className="bg-gray-50 border-t border-gray-200 animate-in slide-in-from-top duration-200">
          <ExpandedRowContent row={row} onLinkClick={onLinkClick} />
        </div>
      )}
    </div>
  );
};


