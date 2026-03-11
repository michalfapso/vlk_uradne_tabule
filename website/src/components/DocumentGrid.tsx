import React, { useState, useMemo } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Dropdown } from 'primereact/dropdown';
import { useQuery, useMutation, useConvexAuth } from "convex/react";
import { api } from "../../convex/_generated/api";
import { PrimeReactProvider } from 'primereact/api';
import ConvexClientProvider from "./ConvexClientProvider";
import { isDataImportant, DEFAULT_REGEX_STRING } from "../scripts/documentAnalysis.js";

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

export default function DocumentGrid({ initialData }: DocumentGridProps) {
    return (
        <ConvexClientProvider>
            <DocumentGridContent initialData={initialData} />
        </ConvexClientProvider>
    );
}

function DocumentGridContent({ initialData }: DocumentGridProps) {
    const { isAuthenticated, isLoading: authLoading } = useConvexAuth();
    const userTags = useQuery(api.tags.getTags, {}) || [];
    const setTagMutation = useMutation(api.tags.setTag);
    const [expandedRows, setExpandedRows] = useState<any>(null);
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

        const sorted = [...docs].sort((a, b) => {
            const dateA = a.datum_display ? new Date(a.datum_display).getTime() : 0;
            const dateB = b.datum_display ? new Date(b.datum_display).getTime() : 0;
            return dateB - dateA;
        });

        if (importantOnly) {
            return sorted.filter(d => d.isImportant);
        }

        return sorted;
    }, [initialData, userTags, importantOnly, krajFilter, okresFilter, regexString]);

    const onTagChange = async (doc: any, newTag: string | null) => {
        try {
            await setTagMutation({
                docId: doc.docId,
                tag: newTag || "",
                docDate: doc.datum || new Date().toISOString()
            });
        } catch (error) {
            console.error("Failed to set tag:", error);
        }
    };

    const rowExpansionTemplate = (data: any) => {
        const a = data.analyza || {};
        return (
            <div className="p-4 bg-gray-50 border-t-2 border-blue-500 shadow-inner">
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

                <div className="space-y-2">
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

                    {data.log && (
                        <details className="group text-xs text-gray-500 bg-white p-2 rounded border border-gray-200">
                            <summary className="cursor-pointer hover:text-gray-800 font-medium list-none flex items-center">
                                <span className="mr-2 transform transition-transform group-open:rotate-90">▶</span> Log / Chyby
                            </summary>
                            <pre className="mt-2 p-3 bg-gray-50 rounded border border-gray-100 overflow-x-auto whitespace-pre-wrap break-all text-[10px] font-mono">
                                {data.log}
                            </pre>
                        </details>
                    )}
                </div>
            </div>
        );
    };

    const dateBodyTemplate = (rowData: any) => {
        const l = rowData.analyza?.ucast_v_konani?.lehota_na_vyjadrenie;
        const isUrgent = /do\s+[1-7]\b/.test(l);
        return (
            <div className="py-1">
                <div className="font-medium text-gray-700">{formatDate(rowData.datum_display)}</div>
                {l && (
                    <div className={`text-[10px] leading-tight mt-1 ${isUrgent ? 'text-red-600 font-bold' : 'text-gray-500'}`}>
                        {l}
                    </div>
                )}
            </div>
        );
    };

    const categoryBodyTemplate = (rowData: any) => {
        const categories = rowData.analyza?.kategorie_vlk;
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
    };

    const zasahBodyTemplate = (rowData: any) => {
        const a = rowData.analyza;
        if (!a) return <span className="text-gray-400">-</span>;
        return (
            <div className="py-1">
                <div className="font-medium text-gray-800 leading-snug">{Array.isArray(a.typ_zasahu) ? a.typ_zasahu.join(", ") : (a.typ_zasahu || "-")}</div>
                {a.rozsah_zasahu && <div className="text-[11px] text-gray-500 italic mt-1 leading-tight">{a.rozsah_zasahu}</div>}
            </div>
        );
    };

    const lokalitaBodyTemplate = (rowData: any) => {
        const m = rowData.analyza?.miesto_realizacie;
        if (!m) return <span className="text-gray-400">-</span>;
        return (
            <div className="py-1">
                <div className="font-bold text-gray-900">{m.obec || ""}</div>
                {m.nazov_lokality_norm && <div className="text-[11px] text-gray-600 leading-tight mt-0.5">({m.nazov_lokality_norm})</div>}
            </div>
        );
    };

    const ochranaBodyTemplate = (rowData: any) => {
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
    };

    const zakonyBodyTemplate = (rowData: any) => {
        const z = rowData.analyza?.zakony;
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
    };

    const tagsBodyTemplate = (rowData: any) => {
        if (!isAuthenticated) return null;
        return (
            <div onClick={(e) => e.stopPropagation()}>
                <Dropdown 
                    value={rowData.myTag} 
                    options={tagOptions} 
                    onChange={(e) => onTagChange(rowData, e.value)} 
                    placeholder="Vyberte značku"
                    className="w-full text-xs"
                    pt={{
                        root: { className: 'border border-gray-300 rounded px-2 py-1 bg-white hover:border-blue-400 transition-colors' },
                        input: { className: 'text-xs p-0 text-gray-700' },
                        trigger: { className: 'w-4 text-gray-400' },
                        item: { className: 'text-xs p-2 hover:bg-blue-50 cursor-pointer transition-colors' },
                        list: { className: 'bg-white border border-gray-200 shadow-xl rounded py-1' }
                    }}
                />
            </div>
        );
    };

    const onRowClick = (event: any) => {
        const data = event.data;
        let _expandedRows = { ...expandedRows };

        if (_expandedRows[data.docId]) {
            delete _expandedRows[data.docId];
        } else {
            _expandedRows[data.docId] = true;
        }

        setExpandedRows(_expandedRows);
    };

    const onRowToggle = (event: any) => {
        setExpandedRows(event.data);
    };

    return (
        <PrimeReactProvider value={{ unstyled: true }}>
            <div className="document-grid-container flex flex-col gap-4 mb-8">
                <div className="flex flex-wrap items-center justify-between bg-white p-4 rounded-lg shadow border border-gray-200 gap-y-4">
                    <div className="flex flex-wrap items-center gap-6">
                        <div className="flex items-center gap-3 cursor-pointer select-none" onClick={() => setImportantOnly(!importantOnly)}>
                            <div className={`w-12 h-6 rounded-full transition-colors relative inline-flex items-center ${importantOnly ? 'bg-blue-600' : 'bg-gray-300'}`}>
                                <div className={`w-5 h-5 bg-white rounded-full absolute transition-all transform shadow-sm ${importantOnly ? 'translate-x-6' : 'translate-x-1'}`} />
                            </div>
                            <span className="text-sm font-semibold text-gray-700">Len dôležité (5. stupeň / Natura 2000 / Moje značky)</span>
                        </div>

                        <div className="flex items-center gap-2">
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Kraj:</label>
                            <select 
                                value={krajFilter || ''} 
                                onChange={(e) => { setKrajFilter(e.target.value || null); setOkresFilter(null); }}
                                className="text-sm p-1.5 border border-gray-300 rounded-md bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                            >
                                <option value="">Všetky</option>
                                {allKraje.map(k => <option key={k} value={k}>{k}</option>)}
                            </select>
                        </div>

                        <div className="flex items-center gap-2">
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Okres:</label>
                            <select 
                                value={okresFilter || ''} 
                                onChange={(e) => setOkresFilter(e.target.value || null)}
                                className="text-sm p-1.5 border border-gray-300 rounded-md bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                            >
                                <option value="">Všetky</option>
                                {allOkresy.map(o => <option key={o} value={o}>{o}</option>)}
                            </select>
                        </div>

                        <div className="flex items-center gap-2">
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wider whitespace-nowrap">Regex filtre:</label>
                            <input 
                                type="text"
                                value={regexString}
                                onChange={(e) => setRegexString(e.target.value)}
                                placeholder="Regex pre nedôležité..."
                                className="text-sm p-1.5 border border-gray-300 rounded-md bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all w-48 font-mono"
                            />
                        </div>

                        <button 
                            onClick={() => {
                                if (expandedRows && Object.keys(expandedRows).length > 0) {
                                    setExpandedRows(null);
                                } else {
                                    const allIds = dataWithTags.reduce((acc: any, doc: any) => {
                                        acc[doc.docId] = true;
                                        return acc;
                                    }, {});
                                    setExpandedRows(allIds);
                                }
                            }}
                            className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-1.5 px-3 rounded-md transition-colors text-xs border border-gray-300 shadow-sm"
                        >
                            {expandedRows && Object.keys(expandedRows).length > 0 ? "Zabaliť všetky" : "Rozbaliť všetky"}
                        </button>
                    </div>
                    <div className="text-xs text-gray-500 font-medium bg-gray-50 px-3 py-1.5 rounded-full border border-gray-100">
                        Zobrazených <span className="text-blue-600 font-bold">{dataWithTags.length}</span> z {initialData.length} dokumentov
                    </div>
                </div>

                <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-x-auto text-sm">
                    <DataTable 
                    value={dataWithTags} 
                    paginator 
                    rows={50} 
                    rowsPerPageOptions={[50, 100, 200]}
                    expandedRows={expandedRows} 
                    onRowToggle={onRowToggle}
                    onRowClick={onRowClick}
                    rowExpansionTemplate={rowExpansionTemplate}
                    dataKey="docId"
                    scrollable={false}
                    sortField="datum_display"
                    sortOrder={-1}
                    removableSort
                    emptyMessage="Nenašli sa žiadne dokumenty."
                    pt={{
                        table: { className: 'w-full text-left border-collapse min-w-[1200px]' },
                        thead: { className: 'bg-gray-50 border-b border-gray-200' },
                        headerRow: { className: '' },
                        bodyRow: ({ data, context }: any) => ({ 
                            className: `border-b border-gray-100 transition-colors cursor-pointer ${context.expanded ? 'bg-blue-50/30' : 'hover:bg-gray-50'} ${data && !data.isImportant && !importantOnly ? 'opacity-60 grayscale-[0.5]' : ''}` 
                        }),
                        rowExpansion: { className: 'bg-white' },
                        paginator: { 
                            root: { className: 'flex items-center justify-center flex-wrap gap-2 p-4 bg-gray-50 border-t border-gray-200' },
                            prevPageButton: { className: 'p-2 hover:bg-gray-200 rounded-full transition-colors disabled:opacity-30' },
                            nextPageButton: { className: 'p-2 hover:bg-gray-200 rounded-full transition-colors disabled:opacity-30' },
                            firstPageButton: { className: 'p-2 hover:bg-gray-200 rounded-full transition-colors disabled:opacity-30' },
                            lastPageButton: { className: 'p-2 hover:bg-gray-200 rounded-full transition-colors disabled:opacity-30' },
                            pageButton: ({ context }: any) => ({
                                className: `w-8 h-8 flex items-center justify-center rounded-full transition-all ${context.active ? 'bg-blue-600 text-white font-bold shadow-md' : 'hover:bg-gray-200'}`
                            })
                        }
                    }}
                >
                    <Column field="datum_display" header="Lehota / Dátum" body={dateBodyTemplate} sortable style={{ width: '130px' }} 
                        pt={{
                            headerCell: { className: 'p-3 text-gray-700 font-bold border-b border-gray-200' },
                            bodyCell: { className: 'p-3 align-top' },
                            sortIcon: { className: 'ml-1 text-gray-400' }
                        }}
                    />
                    <Column field="analyza.kategorie_vlk" header="Kategória" body={categoryBodyTemplate} style={{ width: '120px' }} 
                        pt={{
                            headerCell: { className: 'p-3 text-gray-700 font-bold border-b border-gray-200' },
                            bodyCell: { className: 'p-3 align-top' }
                        }}
                    />
                    <Column field="analyza.typ_zasahu" header="Zásah a Rozsah" body={zasahBodyTemplate} style={{ width: '300px' }} 
                        pt={{
                            headerCell: { className: 'p-3 text-gray-700 font-bold border-b border-gray-200' },
                            bodyCell: { className: 'p-3 align-top' }
                        }}
                    />
                    <Column field="analyza.miesto_realizacie.obec" header="Lokalita" body={lokalitaBodyTemplate} style={{ width: '150px' }} 
                        pt={{
                            headerCell: { className: 'p-3 text-gray-700 font-bold border-b border-gray-200' },
                            bodyCell: { className: 'p-3 align-top' }
                        }}
                    />
                    <Column header="Ochrana" body={ochranaBodyTemplate} style={{ width: '110px' }} 
                        pt={{
                            headerCell: { className: 'p-3 text-gray-700 font-bold border-b border-gray-200' },
                            bodyCell: { className: 'p-3 align-top' }
                        }}
                    />
                    <Column field="analyza.ziadatel_navrhovatel" header="Žiadateľ" style={{ width: '180px' }} 
                        pt={{
                            headerCell: { className: 'p-3 text-gray-700 font-bold border-b border-gray-200' },
                            bodyCell: { className: 'p-3 align-top leading-tight break-words text-xs' }
                        }}
                    />
                    <Column field="analyza.zakony" header="Zákony" body={zakonyBodyTemplate} style={{ width: '180px' }} 
                        pt={{
                            headerCell: { className: 'p-3 text-gray-700 font-bold border-b border-gray-200' },
                            bodyCell: { className: 'p-3 align-top' }
                        }}
                    />
                    {isAuthenticated && (
                        <Column header="Moje značky" body={tagsBodyTemplate} style={{ width: '180px' }} 
                            pt={{
                                headerCell: { className: 'p-3 text-gray-700 font-bold border-b border-gray-200' },
                                bodyCell: { className: 'p-3 align-top' }
                            }}
                        />
                    )}
                </DataTable>
            </div>
        </div>
    </PrimeReactProvider>
    );
}
