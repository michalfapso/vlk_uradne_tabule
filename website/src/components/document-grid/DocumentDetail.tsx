import React from 'react';

export const DocumentDetail = ({
  row,
  onLinkClick
}: {
  row: any,
  onLinkClick: (docId: string) => void
}) => {
  const data = row.original;
  const a = data.analyza || {};
  return (
    <div className="p-4 bg-gray-50 shadow-inner w-full" onClick={e => e.stopPropagation()}>
      <div className="mb-6 pb-4 border-b border-gray-200">
        <div className="flex items-center gap-2 mb-2">
          <button
            onClick={() => onLinkClick(data.docId)}
            title="Kopírovať odkaz na tento dokument"
            className="p-1 text-blue-900 hover:bg-blue-100 rounded-md transition-colors"
          >
            🔗
          </button>
          <h3 className="text-lg font-bold text-blue-900">Zhrnutie analýzy</h3>
        </div>
        <p className="text-gray-800 leading-relaxed mb-4">{a.zhrnutie || "Bez zhrnutia."}</p>
        <div className="flex flex-wrap gap-4">
          <a href={data.url} target="_blank" className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 cursor-pointer text-sm no-underline transition-colors shadow-sm">📄 Pôvodný dokument</a>
          {data.hasGis && (
            <a 
              href={`https://michalfapso.github.io/vlk_zonacia_tanap/?ext_url=https://michalfapso.github.io/vlk_uradne_tabule/data/${data.docId}/gis.geojson&ext_crs=EPSG:4326`} 
              target="_blank" 
              className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 cursor-pointer text-sm no-underline transition-colors shadow-sm"
            >
              🗺️ Mapa{a.gis?.source_type ? ` (${a.gis.source_type === 'KATASTRALNE_UZEMIE' ? 'KU' : a.gis.source_type})` : ""}
            </a>
          )}
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-6">
        <div className="space-y-3">
          <h4 className="font-bold text-gray-700 uppercase text-xs border-b border-gray-300 pb-1 mb-2">Úradné detaily</h4>
          <div className="grid grid-cols-3 gap-x-2 gap-y-1 text-sm">
            <div className="text-gray-500">Typ:</div><div className="col-span-2">{a.typ_dokumentu || "N/A"}</div>
            <div className="text-gray-500">Číslo:</div><div className="col-span-2 font-mono text-xs">{a.cislo_konania_spisu || "N/A"}</div>
            <div className="text-gray-500">Žiadateľ:</div><div className="col-span-2 font-semibold text-blue-800">{a.ziadatel_navrhovatel || "N/A"}</div>
            <div className="text-gray-500">Druhy:</div><div className="col-span-2 italic text-xs">{(a.dotknute_zivocichy_rastliny || []).join(", ") || "N/A"}</div>
            <div className="text-gray-500">Dôležitosť:</div>
            <div className="col-span-2">
              <div className="mb-1 flex items-center gap-2">
                <span className={`font-bold ${
                  data.myTag === 'vstupujeme do správneho konania' ? "text-green-600" :
                  data.isImportant ? "text-red-600" : "text-gray-500"
                }`}>
                  {data.isImportant ? "Áno" : "Nie"}
                </span>
                {data.myTag && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                    data.myTag === 'vstupujeme do správneho konania' ? 'bg-green-100 text-green-800' :
                    data.myTag === 'dôležité' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    Vlastná značka: {data.myTag}
                  </span>
                )}
              </div>
              <div className="text-[10px] text-gray-400 font-normal leading-tight">
                Auto-detekcia: <span className={data.isImportantSystem ? "font-bold text-red-400" : ""}>{data.isImportantSystem ? "Dôležité" : "Nedôležité"}</span> ({data.importanceReason})
              </div>
            </div>
          </div>
        </div>
        <div className="space-y-3">
          <h4 className="font-bold text-gray-700 uppercase text-xs border-b border-gray-300 pb-1 mb-2">Lokalizácia</h4>
          <div className="text-sm">
            <div className="grid grid-cols-3 gap-x-2 gap-y-1">
              <div className="text-gray-500">Kraj:</div><div className="col-span-2">{a.miesto_realizacie?.kraj || "-"}</div>
              <div className="text-gray-500">Okres:</div><div className="col-span-2">{a.miesto_realizacie?.okres || "-"}</div>
              <div className="text-gray-500">Obec:</div><div className="col-span-2 font-bold">{a.miesto_realizacie?.obec || "-"}</div>
              <div className="text-gray-500">Lokalita:</div><div className="col-span-2">{a.miesto_realizacie?.nazov_lokality || "-"}</div>
              <div className="text-gray-500">Intravilán:</div><div className="col-span-2">{a.miesto_realizacie?.lokalita_zastavane_uzemie ? "Áno" : "Nie"}</div>
            </div>
            <div className="mt-2">
              <div className="text-gray-500 mb-1 font-medium">Katastrálne územia:</div>
              <ul className="list-disc list-inside text-xs space-y-1">
                {(a.miesto_realizacie?.katastralne_uzemia || []).map((ku: any, idx: number) => (
                  <li key={idx}>
                    <b>{ku.nazov}</b> ({ku.parcely?.map((p: any) => `${p.typ}-KN: ${p.cisla.join(", ")}`).join("; ") || ""})
                  </li>
                ))}
                {(!a.miesto_realizacie?.katastralne_uzemia || a.miesto_realizacie.katastralne_uzemia.length === 0) && <li>N/A</li>}
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {data.status && Array.isArray(data.status) && data.status.length > 0 && (
          <details className="group text-xs text-gray-500 bg-white p-2 rounded border border-orange-200">
            <summary className="cursor-pointer hover:text-gray-800 font-medium list-none flex items-center text-orange-700">
              <span className="mr-2 transform transition-transform group-open:rotate-90">▶</span> Status / Spracovanie ({data.status.length})
            </summary>
            <div className="mt-2 space-y-1">
              {data.status.map((s: any, idx: number) => (
                <div key={idx} className={`p-2 rounded border ${s.type === 'error' ? 'bg-red-50 border-red-100 text-red-800' : s.type === 'warning' ? 'bg-yellow-50 border-yellow-100 text-yellow-800' : 'bg-blue-50 border-blue-100 text-blue-800'}`}>
                  <span className="font-mono text-[10px] opacity-60 mr-2">{s.date}</span>
                  <span className="font-bold uppercase text-[9px] mr-2">[{s.type}]</span>
                  {s.text}
                </div>
              ))}
            </div>
          </details>
        )}

        {data.laws && (
          <details className="group text-xs text-gray-500 bg-white p-2 rounded border border-gray-200">
            <summary className="cursor-pointer hover:text-gray-800 font-medium list-none flex items-center">
              <span className="mr-2 transform transition-transform group-open:rotate-90">▶</span> Znenia zákonov
            </summary>
            <pre className="mt-2 p-3 bg-gray-50 rounded border border-gray-100 overflow-x-auto whitespace-pre-wrap break-all font-mono text-[11px]">
              {data.laws}
            </pre>
          </details>
        )}

        {data.log && (
          <details className="group text-xs text-gray-500 bg-white p-2 rounded border border-gray-200">
            <summary className="cursor-pointer hover:text-gray-800 font-medium list-none flex items-center">
              <span className="mr-2 transform transition-transform group-open:rotate-90">▶</span> Log
            </summary>
            <pre className="mt-2 p-3 bg-gray-50 rounded border border-gray-100 overflow-x-auto whitespace-pre-wrap break-all text-[10px] font-mono">
              {data.log}
            </pre>
          </details>
        )}

        {data.analyza && (
          <details className="group text-xs text-gray-500 bg-white p-2 rounded border border-gray-200">
            <summary className="cursor-pointer hover:text-gray-800 font-medium list-none flex items-center">
              <span className="mr-2 transform transition-transform group-open:rotate-90">▶</span> JSON analýza
            </summary>
            <pre className="mt-2 p-3 bg-gray-50 rounded border border-gray-100 overflow-x-auto whitespace-pre-wrap break-all text-[10px] font-mono">
              {JSON.stringify(data.analyza, null, 2)}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
};
