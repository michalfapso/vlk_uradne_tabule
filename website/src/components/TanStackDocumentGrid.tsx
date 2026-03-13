import React, { useState, useMemo, useRef, useEffect } from 'react';
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

import {
  categoryColors,
  formatDate,
  TagActionBar,
  EvaluationCard,
  GridControls,
  GridPagination,
  UndoToast,
  EmptyState,
  DesktopTable,
} from './document-grid';

interface DocumentGridProps {
  initialData: any[];
}

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
  const [regexString] = useState(DEFAULT_REGEX_STRING);
  const [highlightedDocId, setHighlightedDocId] = useState<string | null>(null);

  // Local state for delayed hiding and undo
  const [pendingHides, setPendingHides] = useState<Record<string, boolean>>({});
  const [lastAction, setLastAction] = useState<{ docId: string, datum: string, oldTag: string | null } | null>(null);
  const [showUndo, setShowUndo] = useState(false);
  const [showCopyToast, setShowCopyToast] = useState(false);
  const undoTimerRef = useRef<NodeJS.Timeout | null>(null);
  const copyToastTimerRef = useRef<NodeJS.Timeout | null>(null);
  const hasScrolledInitial = useRef(false);

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
      const myTag = tagEntry?.tag || null;
      
      return {
        ...doc,
        myTag,
        datum_display: doc.analyza?.datum_zverejnenia || doc.datum,
        isImportant: myTag ? (myTag === 'dôležité' || myTag === 'vstupujeme do správneho konania') : isImportantSystem,
        isImportantSystem,
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
      return docs.filter(d => {
        if (pendingHides[d.docId]) return true;
        if (d.docId === highlightedDocId) return true;
        return d.isImportant;
      });
    }

    return docs;
  }, [initialData, userTags, importantOnly, krajFilter, okresFilter, regexString, pendingHides, highlightedDocId]);

  // Handle pendingHides cleanup in a separate effect to avoid infinite loop
  useEffect(() => {
    if (Object.keys(pendingHides).length === 0) return;

    let blacklistRegex: RegExp | null = null;
    try {
      blacklistRegex = new RegExp(regexString, "i");
    } catch (e) {
      console.error("Invalid regex:", e);
    }

    const currentDocIds = new Set(initialData.map(d => d.docId));
    
    setPendingHides(prev => {
      let changed = false;
      const next = { ...prev };
      for (const id in next) {
        if (!currentDocIds.has(id)) {
          delete next[id];
          changed = true;
          continue;
        }
        
        const doc = initialData.find(d => d.docId === id);
        if (doc) {
          const tagEntry = userTags.find((t: any) => t.docId === id);
          const myTag = tagEntry?.tag || null;
          const importance = isDataImportant(doc, blacklistRegex);
          const isImportant = myTag ? (myTag === 'dôležité' || myTag === 'vstupujeme do správneho konania') : importance.important;
          
          // Cleanup if:
          // 1. Filters are turned off
          // 2. Document is important again (e.g. after undo) AND it's not the one we just tagged
          //    (The "not the one we just tagged" check prevents premature cleanup during the "out" animation)
          if (!importantOnly || (isImportant && lastAction?.docId !== id)) {
            delete next[id];
            changed = true;
          }
        }
      }
      return changed ? next : prev;
    });
  }, [initialData, userTags, importantOnly, regexString, pendingHides, lastAction]);

  const onTagChange = async (docId: string, datum: string, newTag: string | null, currentTag: string | null) => {
    setLastAction({ docId, datum, oldTag: currentTag });
    setShowUndo(true);
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    undoTimerRef.current = setTimeout(() => setShowUndo(false), 5000);

    const doc = dataWithTags.find(d => d.docId === docId);
    const wouldBeHidden = importantOnly && doc && doc.isImportant && (newTag === 'nedôležité' || newTag === null);
    
    if (wouldBeHidden) {
      setPendingHides(prev => ({ ...prev, [docId]: true }));
      
      // Clear pending hide after animation duration
      setTimeout(() => {
        setPendingHides(prev => {
          if (!prev[docId]) return prev;
          const next = { ...prev };
          delete next[docId];
          return next;
        });
      }, 1000);
    }

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

  const handleUndo = async () => {
    if (!lastAction) return;
    const { docId, datum, oldTag } = lastAction;
    
    // Ensure it's in pendingHides so it's added to DOM (but hidden) before it becomes important
    // This allows for a smooth "in" animation when it eventually becomes important.
    setPendingHides(prev => ({ ...prev, [docId]: true }));

    try {
      await setTagMutation({
        docId: docId,
        tag: oldTag || "",
        docDate: datum || new Date().toISOString()
      });
      
      // We don't clear pendingHides immediately here. 
      // Instead, we let the useEffect cleanup handle it when isImportant becomes true.
      // This ensures a smooth "in" animation instead of an instant re-mount.

      setLastAction(null);
      setShowUndo(false);
    } catch (error) {
      console.error("Failed to undo tag:", error);
    }
  };

  const handleLinkClick = (docId: string) => {
    const url = new URL(window.location.href);
    url.searchParams.set('docId', docId);
    window.history.pushState({}, '', url);
    
    setHighlightedDocId(docId);
    setExpanded(prev => (typeof prev === 'object' ? { ...prev, [docId]: true } : { [docId]: true }));
    
    // Copy to clipboard
    navigator.clipboard.writeText(url.toString()).then(() => {
      setShowCopyToast(true);
      if (copyToastTimerRef.current) clearTimeout(copyToastTimerRef.current);
      copyToastTimerRef.current = setTimeout(() => setShowCopyToast(false), 3000);
    });

    // Scroll to the document
    setTimeout(() => {
      const element = [
        document.getElementById(`doc-row-${docId}`),
        document.getElementById(`doc-card-${docId}`)
      ].find(el => el && el.offsetParent !== null);

      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 500);
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
            <TagActionBar 
              docId={rowData.docId} 
              datum={rowData.datum_display} 
              currentTag={rowData.myTag} 
              onTagChange={onTagChange}
              isPending={!!pendingHides[rowData.docId]}
            />
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
        const sourceType = a.gis?.source_type;
        if (sourceType) {
          const displayType = sourceType === 'KATASTRALNE_UZEMIE' ? 'KU' : sourceType;
          badges.push(<span key="source-type" className="px-1.5 py-0.5 bg-gray-600 text-white rounded text-[9px] font-bold uppercase mb-1 inline-block shadow-sm">{displayType}</span>);
        }
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
  ], [isAuthenticated, userTags, setTagMutation, pendingHides]);

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

  // Handle URL-linked document and initial load
  useEffect(() => {
    if (initialData.length === 0) return;
    
    const params = new URLSearchParams(window.location.search);
    const docId = params.get('docId');
    if (!docId) return;

    // 1. Automatic "Important Only" Toggle
    if (importantOnly) {
      const doc = initialData.find(d => d.docId === docId);
      if (doc) {
        let blacklistRegex: RegExp | null = null;
        try {
          blacklistRegex = new RegExp(regexString, "i");
        } catch (e) {}
        
        const tagEntry = userTags.find((t: any) => t.docId === docId);
        const myTag = tagEntry?.tag || null;
        const importance = isDataImportant(doc, blacklistRegex);
        const isImportant = myTag ? (myTag === 'dôležité' || myTag === 'vstupujeme do správneho konania') : importance.important;

        if (!isImportant) {
          setImportantOnly(false);
          return; // Wait for re-render
        }
      }
    }

    // 2. Ensure it's expanded and highlighted
    if (highlightedDocId !== docId) {
      setHighlightedDocId(docId);
    }
    const isExpanded = expanded === true || (typeof expanded === 'object' && expanded[docId]);
    if (!isExpanded) {
      setExpanded(prev => (typeof prev === 'object' ? { ...prev, [docId]: true } : { [docId]: true }));
    }

    // 3. Jump to correct page
    const allFilteredRows = table.getFilteredRowModel().rows;
    const rowIndex = allFilteredRows.findIndex(r => r.original.docId === docId);
    if (rowIndex !== -1) {
      const pageSize = table.getState().pagination.pageSize;
      const targetPage = Math.floor(rowIndex / pageSize);
      if (table.getState().pagination.pageIndex !== targetPage) {
        table.setPageIndex(targetPage);
        return; // Wait for page change to render
      }
    }

    // 4. Scroll to it once it's rendered
    if (!hasScrolledInitial.current) {
      const timer = setTimeout(() => {
        const element = [
          document.getElementById(`doc-row-${docId}`),
          document.getElementById(`doc-card-${docId}`)
        ].find(el => el && el.offsetParent !== null);

        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' });
          hasScrolledInitial.current = true;
        }
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [initialData, userTags, importantOnly, table, highlightedDocId, expanded, regexString]);

  return (
    <div className="document-grid-container flex flex-col gap-4 mb-8 font-sans">
      <GridControls 
        importantOnly={importantOnly}
        setImportantOnly={setImportantOnly}
        krajFilter={krajFilter}
        setKrajFilter={setKrajFilter}
        okresFilter={okresFilter}
        setOkresFilter={setOkresFilter}
        allKraje={allKraje}
        allOkresy={allOkresy}
        globalFilter={globalFilter}
        setGlobalFilter={setGlobalFilter}
        rowCount={table.getFilteredRowModel().rows.length}
        totalCount={initialData.length}
        isAllExpanded={table.getIsAllRowsExpanded()}
        toggleAllExpanded={() => table.toggleAllRowsExpanded()}
      />

      <DesktopTable 
        table={table} 
        pendingHides={pendingHides} 
        highlightedDocId={highlightedDocId}
        onLinkClick={handleLinkClick}
      />

      <div className="xl:hidden flex flex-col">
        {table.getRowModel().rows.map(row => (
          <EvaluationCard 
            key={row.id} 
            row={row} 
            onTagChange={onTagChange}
            isPending={!!pendingHides[row.original.docId]}
            isAuthenticated={isAuthenticated}
            highlightedDocId={highlightedDocId}
            onLinkClick={handleLinkClick}
          />
        ))}
      </div>

      <GridPagination table={table} />

      <UndoToast 
        showUndo={showUndo} 
        onUndo={handleUndo} 
        onClose={() => setShowUndo(false)} 
      />

      {showCopyToast && (
        <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-50 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <div className="bg-gray-900 text-white px-6 py-3 rounded-full shadow-2xl flex items-center gap-3 border border-gray-700">
            <span className="text-blue-400">🔗</span>
            <span className="text-sm font-medium text-gray-100">Odkaz na dokument bol skopírovaný</span>
          </div>
        </div>
      )}

      {table.getRowModel().rows.length === 0 && (
        <EmptyState onClearFilters={() => {
          setGlobalFilter('');
          setImportantOnly(false);
          setKrajFilter(null);
          setOkresFilter(null);
        }} />
      )}
    </div>
  );
}

