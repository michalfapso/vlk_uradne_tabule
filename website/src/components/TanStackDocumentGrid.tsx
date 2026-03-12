import React, { useState, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getExpandedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ExpandedState,
} from '@tanstack/react-table';
import { useQuery, useMutation } from "convex/react";
import { api } from "../../convex/_generated/api";
import { ConvexClientBareProvider } from "./ConvexClientProvider";
import { isDataImportant, DEFAULT_REGEX_STRING } from "../scripts/documentAnalysis.js";
import { useStore } from '@nanostores/react';
import { $isAuthenticated } from '../stores/authStore';

interface DocumentGridProps {
  initialData: any[];
}

const tagOptions = [
  { label: 'Bez značky', value: null },
  { label: 'Nedôležité', value: 'nedôležité' },
  { label: 'Dôležité', value: 'dôležité' },
  { label: 'Vstupujeme do konania', value: 'vstupujeme do správneho konania' }
];

const categoryColors: Record<string, string> = {
  'LES_VYRUB': 'bg-green-700 text-white',
  'VYSTAVBA_V_PRIRODE': 'bg-orange-500 text-white',
  'ZIVOCICHY_USMRCOVANIE': 'bg-red-600 text-white',
  'CHEMIA': 'bg-purple-600 text-white',
  'VJAZD_VOZIDLA': 'bg-gray-500 text-white',
  'POLNOHOSPODARSTVO': 'bg-yellow-600 text-white',
  'VEDA_A_VYSKUM': 'bg-blue-500 text-white',
  'INZINIERSKE_SIETE': 'bg-blue-300 text-gray-800',
  'INE': 'bg-gray-300 text-gray-800'
};

const formatDate = (s: string) => s ? new Date(s).toLocaleDateString("sk-SK") : "N/A";

export default function TanStackDocumentGrid({ initialData }: DocumentGridProps) {
  return (
    <ConvexClientBareProvider>
      <DocumentGridContent initialData={initialData} />
    </ConvexClientBareProvider>
  );
}

function DocumentGridContent({ initialData }: DocumentGridProps) {
  const isAuthenticated = useStore($isAuthenticated);
  const userTags = useQuery(api.tags.getTags, {}) || [];
  const setTagMutation = useMutation(api.tags.setTag);

  const [sorting, setSorting] = useState<SortingState>([{ id: 'datum_display', desc: true }]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [expanded, setExpanded] = useState<ExpandedState>({});
  const [importantOnly, setImportantOnly] = useState(true);
  const [krajFilter, setKrajFilter] = useState<string | null>(null);
  const [okresFilter, setOkresFilter] = useState<string | null>(null);
  const [regexString, setRegexString] = useState(DEFAULT_REGEX_STRING);

  const allKraje = useMemo(() => [...new Set(initialData.map(doc => doc.kraj).filter(Boolean))].sort(), [initialData]);
  const allOkresy = useMemo(() => {
    const filteredDocs = krajFilter ? initialData.filter(d => d.kraj === krajFilter) : initialData;
    return [...new Set(filteredDocs.map(doc => doc.okres).filter(Boolean))].sort();
  }, [initialData, krajFilter]);

  const dataWithTags = useMemo(() => {
    let blacklistRegex: RegExp | null = null;
    try {
      blacklistRegex = new RegExp(regexString, "i");
    } catch (e) {
      console.error("Invalid regex:", e);
    }

    let docs = initialData.map(doc => {
      const tagEntry = userTags.find((t: any) => t.docId === doc.docId);
      const importance = isDataImportant(doc, blacklistRegex);
      const isImportantSystem = importance.important;
      
      return {
        ...doc,
        myTag: tagEntry?.tag || null,
        datum_display: doc.analyza?.datum_zverejnenia || doc.datum,
        isImportant: isImportantSystem || tagEntry?.tag === 'dôležité' || tagEntry?.tag === 'vstupujeme do správneho konania',
        importanceReason: importance.reason
      };
    });

    if (krajFilter) {
      docs = docs.filter(d => d.kraj === krajFilter);
    }
    if (okresFilter) {
      docs = docs.filter(d => d.okres === okresFilter);
    }

    if (importantOnly) {
      return docs.filter(d => d.isImportant);
    }

    return docs;
  }, [initialData, userTags, importantOnly, krajFilter, okresFilter, regexString]);

  const onTagChange = async (docId: string, datum: string, newTag: string | null) => {
    try {
      await setTagMutation({
        docId: docId,
        tag: newTag || "",
        docDate: datum || new Date().toISOString()
      });
    } catch (error) {
      console.error("Failed to set tag:", error);
    }
  };

  const columns = useMemo<ColumnDef<any>[]>(() => [
    {
      id: 'myTag',
      header: 'Moje značky',
      cell: info => {
        if (!isAuthenticated) return null;
        const rowData = info.row.original;
        return (
          <div onClick={(e) => e.stopPropagation()}>
            <select
              value={rowData.myTag || ''}
              onChange={(e) => onTagChange(rowData.docId, rowData.datum_display, e.target.value)}
              className="w-full text-[11px] border border-gray-300 rounded px-1 py-1 bg-white hover:border-blue-400 transition-colors outline-none"
            >
              {tagOptions.map(opt => (
                <option key={opt.label} value={opt.value || ''}>{opt.label}</option>
              ))}
            </select>
          </div>
        );
      },
    },
    {
      accessorKey: 'datum_display',
      header: 'Lehota / Dátum',
      cell: info => {
        const rowData = info.row.original;
        const l = rowData.analyza?.ucast_v_konani?.lehota_na_vyjadrenie;
        const isUrgent = l && /do\s+[1-7]\b/.test(l);
        return (
          <div className="py-1">
            <div className="font-medium text-gray-700">{formatDate(info.getValue() as string)}</div>
            {l && (
              <div className={`text-[10px] leading-tight mt-1 ${isUrgent ? 'text-red-600 font-bold' : 'text-gray-500'}`}>
                {l}
              </div>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: 'analyza.kategorie_vlk',
      header: 'Kategória',
      cell: info => {
        const categories = info.getValue() as string[];
        if (!Array.isArray(categories)) return <span className="text-gray-400">-</span>;
        return (
          <div className="flex flex-wrap gap-1">
            {categories.map((cat, idx) => (
              <span key={idx} className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase shadow-sm ${categoryColors[cat] || 'bg-gray-200 text-gray-700'}`}>
                {cat}
              </span>
            ))}
          </div>
        );
      },
    },
    {
      id: 'zasah',
      header: 'Zásah a Rozsah',
      cell: info => {
        const a = info.row.original.analyza;
        if (!a) return <span className="text-gray-400">-</span>;
        return (
          <div className="py-1">
            <div className="font-medium text-gray-800 leading-snug">
              {Array.isArray(a.typ_zasahu) ? a.typ_zasahu.join(", ") : (a.typ_zasahu || "-")}
            </div>
            {a.rozsah_zasahu && <div className="text-[11px] text-gray-500 italic mt-1 leading-tight">{a.rozsah_zasahu}</div>}
          </div>
        );
      },
    },
    {
      accessorKey: 'analyza.miesto_realizacie.obec',
      header: 'Lokalita',
      cell: info => {
        const m = info.row.original.analyza?.miesto_realizacie;
        if (!m) return <span className="text-gray-400">-</span>;
        return (
          <div className="py-1">
            <div className="font-bold text-gray-900">{m.obec || ""}</div>
            {m.nazov_lokality_norm && <div className="text-[11px] text-gray-600 leading-tight mt-0.5">({m.nazov_lokality_norm})</div>}
          </div>
        );
      },
    },
    {
      id: 'ochrana',
      header: 'Ochrana',
      cell: info => {
        const rowData = info.row.original;
        const a = rowData.analyza || {};
        const g = a.gis?.zasiahnute_chranene_uzemia || a.zasiahnute_chranene_uzemia;
        const badges = [];
        if (g) {
          if (g['5st_konsUEV']) badges.push(<span key="5st" className="px-1.5 py-0.5 bg-red-700 text-white rounded text-[9px] font-bold uppercase mb-1 inline-block shadow-sm">5. STUPEŇ!</span>);
          if (g['MCHU']) badges.push(<span key="mchu" className="px-1.5 py-0.5 bg-red-600 text-white rounded text-[9px] font-bold uppercase mb-1 inline-block shadow-sm">MCHU</span>);
          if (g['UEV'] || g['CHVU']) badges.push(<span key="natura" className="px-1.5 py-0.5 bg-green-700 text-white rounded text-[9px] font-bold uppercase mb-1 inline-block shadow-sm">Natura 2000</span>);
        }
        if (Array.isArray(a.typ_uzemia) && a.typ_uzemia.some((t: string) => /chko|národný park/i.test(t))) {
          badges.push(<span key="chko" className="px-1.5 py-0.5 bg-green-600 text-white rounded text-[9px] font-bold uppercase mb-1 inline-block shadow-sm">CHKO/NP</span>);
        }
        if (a.miesto_realizacie?.lokalita_zastavane_uzemie) {
          badges.push(<span key="intra" className="px-1.5 py-0.5 bg-gray-400 text-white rounded text-[9px] font-bold uppercase mb-1 inline-block shadow-sm">Intravilán</span>);
        }
        if (rowData.hasGis) {
          badges.push(
            <a 
              key="map-badge" 
              href={`https://michalfapso.github.io/vlk_zonacia_tanap/?ext_url=https://michalfapso.github.io/vlk_uradne_tabule/data/${rowData.docId}/gis.geojson&ext_crs=EPSG:4326`}
              target="_blank"
              onClick={(e) => e.stopPropagation()}
              className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded text-[9px] font-bold uppercase mb-1 inline-block shadow-sm border border-blue-200 hover:bg-blue-200 transition-colors cursor-pointer no-underline"
            >
              🗺️ MAPA
            </a>
          );
        }
        return <div className="flex flex-col items-start gap-0.5 py-1">{badges.length > 0 ? badges : <span className="text-gray-400">-</span>}</div>;
      },
    },
    {
      accessorKey: 'analyza.ziadatel_navrhovatel',
      header: 'Žiadateľ',
      cell: info => <div className="leading-tight break-words text-xs">{info.getValue() as string}</div>,
    },
    {
      accessorKey: 'analyza.zakony',
      header: 'Zákony',
      cell: info => {
        const z = info.getValue() as any[];
        if (!Array.isArray(z)) return <span className="text-gray-400">-</span>;
        return (
          <div className="font-medium text-gray-800 break-words whitespace-normal leading-tight text-xs">
            {z.map((l: any, idx: number) => (
              <div key={idx}>
                {l.cislo}{l.paragrafy ? ` (§ ${l.paragrafy.join(", ")})` : ""}
              </div>
            ))}
          </div>
        );
      },
    }
  ], [isAuthenticated, userTags, setTagMutation]);

  const table = useReactTable({
    data: dataWithTags,
    columns,
    state: {
      sorting,
      globalFilter,
      expanded,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowCanExpand: () => true,
    getRowId: row => row.docId,
  });

  const renderExpandedRow = (row: any) => {
    const data = row.original;
    const a = data.analyza || {};
    return (
      <div className="p-4 bg-gray-50 border-t-2 border-blue-500 shadow-inner w-full" onClick={e => e.stopPropagation()}>
        <div className="mb-6 pb-4 border-b border-gray-200">
          <h3 className="text-lg font-bold text-blue-900 mb-2">Zhrnutie analýzy</h3>
          <p className="text-gray-800 leading-relaxed mb-4">{a.zhrnutie || "Bez zhrnutia."}</p>
          <div className="flex flex-wrap gap-4">
            <a href={data.url} target="_blank" className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 cursor-pointer text-sm no-underline transition-colors shadow-sm">📄 Pôvodný dokument</a>
            {data.hasGis && (
              <a href={`https://michalfapso.github.io/vlk_zonacia_tanap/?ext_url=https://michalfapso.github.io/vlk_uradne_tabule/data/${data.docId}/gis.geojson&ext_crs=EPSG:4326`} target="_blank" className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 cursor-pointer text-sm no-underline transition-colors shadow-sm">🗺️ Mapa</a>
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
              <div className="text-gray-500">Dôležitosť:</div><div className="col-span-2"><span className={data.isImportant ? "font-bold text-red-600" : "text-gray-500"}>{data.isImportant ? "Áno" : "Nie"}</span> <span className="text-[10px] text-gray-400 font-normal">({data.importanceReason})</span></div>
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

  const EvaluationCard = ({ row }: { row: any }) => {
    const data = row.original;
    const a = data.analyza || {};
    const isExpanded = row.getIsExpanded();

    return (
      <div 
        className={`bg-white rounded-xl shadow-md border-l-4 mb-4 overflow-hidden transition-all w-full ${data.isImportant ? 'border-l-red-600' : 'border-l-gray-300 opacity-80 grayscale-[0.3]'}`}
        onClick={() => row.toggleExpanded()}
      >
        <div className="p-4">
          {isAuthenticated && (
            <div className="mb-3" onClick={e => e.stopPropagation()}>
              <select
                value={data.myTag || ''}
                onChange={(e) => onTagChange(data.docId, data.datum_display, e.target.value)}
                className="w-full text-xs border border-blue-200 rounded-lg px-2 py-2 bg-blue-50 font-bold text-blue-800 focus:ring-2 focus:ring-blue-500 outline-none"
              >
                {tagOptions.map(opt => (
                  <option key={opt.label} value={opt.value || ''}>{opt.label}</option>
                ))}
              </select>
            </div>
          )}

          <div className="flex justify-between items-start mb-2">
            <div className="text-xs font-bold text-gray-500 uppercase">{formatDate(data.datum_display)}</div>
            <div className="flex flex-wrap gap-1 justify-end max-w-[60%]">
              {(a.kategorie_vlk || []).map((cat: string, idx: number) => (
                <span key={idx} className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase ${categoryColors[cat] || 'bg-gray-200 text-gray-700'}`}>
                  {cat}
                </span>
              ))}
            </div>
          </div>
          
          <h4 className="text-sm font-bold text-gray-900 mb-2 leading-snug line-clamp-2">
            {Array.isArray(a.typ_zasahu) ? a.typ_zasahu.join(", ") : (a.typ_zasahu || data.nazov || "-")}
          </h4>

          {/* Wider screens inside mobile view (labels/values on same line) */}
          <div className="flex flex-col sm:flex-row sm:flex-wrap gap-x-6 gap-y-2 text-[11px] mb-3">
            <div className="flex items-center gap-2">
              <span className="text-gray-500 text-[9px] uppercase font-bold tracking-tighter whitespace-nowrap">Lokalita:</span>
              <span className="font-bold text-gray-800">{a.miesto_realizacie?.obec || "-"}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-500 text-[9px] uppercase font-bold tracking-tighter whitespace-nowrap">Žiadateľ:</span>
              <span className="font-medium text-blue-800 line-clamp-1">{a.ziadatel_navrhovatel || "-"}</span>
            </div>
            <div className="flex flex-wrap items-center gap-1 sm:ml-auto pt-1 sm:pt-0">
              {/* Ochrana Badges for Mobile */}
              {a.gis?.zasiahnute_chranene_uzemia?.['5st_konsUEV'] && <span className="px-1.5 py-0.5 bg-red-700 text-white rounded text-[8px] font-bold uppercase shadow-sm">5. STUPEŇ!</span>}
              {(a.gis?.zasiahnute_chranene_uzemia?.['UEV'] || a.gis?.zasiahnute_chranene_uzemia?.['CHVU']) && <span className="px-1.5 py-0.5 bg-green-700 text-white rounded text-[8px] font-bold uppercase shadow-sm">Natura 2000</span>}
              {data.hasGis && <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 border border-blue-200 rounded text-[8px] font-bold uppercase shadow-sm">🗺️ MAPA</span>}
              {data.status && Array.isArray(data.status) && data.status.some((s: any) => s.type === 'error') && <span className="px-1.5 py-0.5 bg-red-100 text-red-600 border border-red-200 rounded text-[8px] font-bold uppercase shadow-sm">⚠️ CHYBY</span>}
            </div>
          </div>
        </div>
        
        {isExpanded && (
          <div className="bg-gray-50 border-t border-gray-200 animate-in slide-in-from-top duration-200">
            {renderExpandedRow(row)}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="document-grid-container flex flex-col gap-4 mb-8 font-sans">
      {/* Controls */}
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
            <span className="text-blue-600">{table.getFilteredRowModel().rows.length}</span> / {initialData.length} DOKUMENTOV
          </div>
          <button 
            onClick={() => table.toggleAllRowsExpanded()}
            className="bg-white hover:bg-gray-50 text-gray-700 font-bold py-1.5 px-3 rounded-lg transition-colors text-[10px] uppercase tracking-wider border border-gray-200 shadow-sm"
          >
            {table.getIsAllRowsExpanded() ? "Zabaliť" : "Rozbaliť"} VŠETKY
          </button>
        </div>
      </div>

      {/* Desktop View (now xl breakpoint for better space management) */}
      <div className="hidden xl:block bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[1200px]">
            <thead>
              {table.getHeaderGroups().map(headerGroup => (
                <tr key={headerGroup.id} className="bg-gray-50 border-b border-gray-200">
                  {headerGroup.headers.map(header => (
                    <th 
                      key={header.id} 
                      className="p-3 text-[10px] font-black text-gray-400 uppercase tracking-widest cursor-pointer hover:bg-gray-100 transition-colors"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <div className="flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {{
                          asc: ' 🔼',
                          desc: ' 🔽',
                        }[header.column.getIsSorted() as string] ?? null}
                      </div>
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map(row => (
                <React.Fragment key={row.id}>
                  <tr 
                    className={`border-b border-gray-100 transition-colors cursor-pointer ${row.getIsExpanded() ? 'bg-blue-50/50' : 'hover:bg-gray-50'} ${!row.original.isImportant ? 'opacity-60 grayscale-[0.4]' : ''}`}
                    onClick={() => row.toggleExpanded()}
                  >
                    {row.getVisibleCells().map(cell => (
                      <td key={cell.id} className="p-3 align-top">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                  {row.getIsExpanded() && (
                    <tr>
                      <td colSpan={columns.length} className="p-0 border-b border-gray-200">
                        {renderExpandedRow(row)}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile View (now shown up to xl breakpoint) */}
      <div className="xl:hidden flex flex-col gap-4">
        {table.getRowModel().rows.map(row => (
          <EvaluationCard key={row.id} row={row} />
        ))}
      </div>

      {/* Paginator */}
      <div className="flex flex-wrap items-center justify-center gap-2 p-4 bg-white rounded-xl shadow-md border border-gray-200">
        <button
          className="p-2 bg-gray-100 hover:bg-gray-200 rounded-lg disabled:opacity-30 disabled:hover:bg-gray-100 transition-colors"
          onClick={() => table.setPageIndex(0)}
          disabled={!table.getCanPreviousPage()}
        >
          «
        </button>
        <button
          className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg disabled:opacity-30 disabled:hover:bg-gray-100 transition-colors font-bold text-xs"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
        >
          PREDCHÁDZAJÚCA
        </button>
        
        <div className="flex items-center gap-1">
          {Array.from({ length: Math.min(5, table.getPageCount()) }, (_, i) => {
            const pageIndex = table.getState().pagination.pageIndex;
            const pageCount = table.getPageCount();
            let displayPage = i;
            
            if (pageCount > 5) {
                if (pageIndex > 2) {
                    displayPage = Math.min(pageIndex - 2 + i, pageCount - 5 + i);
                }
            }

            return (
              <button
                key={displayPage}
                onClick={() => table.setPageIndex(displayPage)}
                className={`w-8 h-8 flex items-center justify-center rounded-lg text-xs font-bold transition-all ${table.getState().pagination.pageIndex === displayPage ? 'bg-blue-600 text-white shadow-lg scale-110' : 'bg-gray-50 hover:bg-gray-200 text-gray-600'}`}
              >
                {displayPage + 1}
              </button>
            );
          })}
        </div>

        <button
          className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg disabled:opacity-30 disabled:hover:bg-gray-100 transition-colors font-bold text-xs"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
        >
          NASLEDUJÚCA
        </button>
        <button
          className="p-2 bg-gray-100 hover:bg-gray-200 rounded-lg disabled:opacity-30 disabled:hover:bg-gray-100 transition-colors"
          onClick={() => table.setPageIndex(table.getPageCount() - 1)}
          disabled={!table.getCanNextPage()}
        >
          »
        </button>
        
        <select
          value={table.getState().pagination.pageSize}
          onChange={e => {
            table.setPageSize(Number(e.target.value))
          }}
          className="ml-2 text-xs font-bold bg-gray-50 border border-gray-200 rounded-lg p-1.5 outline-none"
        >
          {[20, 50, 100].map(pageSize => (
            <option key={pageSize} value={pageSize}>
              Zobraziť {pageSize}
            </option>
          ))}
        </select>
      </div>

      {table.getRowModel().rows.length === 0 && (
        <div className="text-center py-20 bg-white rounded-xl shadow-inner border border-dashed border-gray-300">
          <div className="text-4xl mb-4">🔍</div>
          <div className="text-gray-500 font-bold uppercase tracking-widest text-sm">Nenašli sa žiadne dokumenty</div>
          <button 
            onClick={() => {
                setGlobalFilter('');
                setImportantOnly(false);
                setKrajFilter(null);
                setOkresFilter(null);
            }}
            className="mt-4 text-blue-600 font-bold text-xs uppercase hover:underline"
          >
            Zrušiť všetky filtre
          </button>
        </div>
      )}
    </div>
  );
}
