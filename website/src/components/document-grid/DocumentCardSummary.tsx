import React from 'react';
import { categoryColors } from './constants';
import { formatDate, getBorderColorClass } from './utils';

interface DocumentCardSummaryProps {
  docId: string;
  datum_display: string;
  data: {
    analyza?: {
      kategorie_vlk?: string[];
      typ_zasahu?: string[];
      miesto_realizacie?: Record<string, any>;
      ziadatel_navrhovatel?: string;
      zakony?: Array<{ cislo: string; paragrafy?: string[] }>;
      gis?: Record<string, any>;
      typ_uzemia?: string[];
    };
    nazov?: string;
  };
  hasGis: boolean;
  myTag?: string | null;
  tagUI?: React.ReactNode;
}

export const DocumentCardSummary = ({
  docId,
  datum_display,
  data,
  hasGis,
  myTag,
  tagUI
}: DocumentCardSummaryProps) => {
  const a = data.analyza || {};

  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mb-3">
        <div className="text-xs font-bold text-gray-500 uppercase whitespace-nowrap">{formatDate(datum_display)}</div>

        {tagUI && (
          <div onClick={e => e.stopPropagation()}>
            {tagUI}
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
          {a.gis?.source_type && (
            <span className="px-1.5 py-0.5 bg-gray-600 text-white rounded text-[8px] font-bold uppercase shadow-sm">
              {a.gis.source_type === 'KATASTRALNE_UZEMIE' ? 'KU' : a.gis.source_type}
            </span>
          )}
          {a.gis?.zasiahnute_chranene_uzemia?.['5st_konsUEV'] && <span className="px-1.5 py-0.5 bg-red-700 text-white rounded text-[8px] font-bold uppercase shadow-sm">5. STUPEŇ!</span>}
          {(a.gis?.zasiahnute_chranene_uzemia?.['UEV'] || a.gis?.zasiahnute_chranene_uzemia?.['CHVU']) && <span className="px-1.5 py-0.5 bg-green-700 text-white rounded text-[8px] font-bold uppercase shadow-sm">Natura 2000</span>}
          {Array.isArray(a.typ_uzemia) && a.typ_uzemia.some((t: string) => /chko|národný park/i.test(t)) && (
            <span className="px-1.5 py-0.5 bg-green-600 text-white rounded text-[8px] font-bold uppercase shadow-sm">CHKO/NP</span>
          )}
          {a.miesto_realizacie?.lokalita_zastavane_uzemie && (
            <span className="px-1.5 py-0.5 bg-gray-400 text-white rounded text-[8px] font-bold uppercase shadow-sm">Intravilán</span>
          )}

          {hasGis && (
            <a
              href={`https://michalfapso.github.io/vlk_zonacia_tanap/?ext_url=https://michalfapso.github.io/vlk_uradne_tabule/data/${docId}/gis.geojson&ext_crs=EPSG:4326`}
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
        {a.zakony && Array.isArray(a.zakony) && a.zakony.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-gray-500 text-[9px] uppercase font-bold tracking-tighter whitespace-nowrap">Zákony:</span>
            <span className="font-medium text-gray-800">
              {a.zakony.map((l: any, idx: number) => (
                <span key={idx}>
                  {idx > 0 && ", "}{l.cislo}{l.paragrafy ? ` (§ ${l.paragrafy.join(", ")})` : ""}
                </span>
              ))}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
