import React, { useState, useEffect } from 'react';
import { useStore } from '@nanostores/react';
import { $isAuthenticated } from '../../stores/authStore';
import { DocumentCardSummary } from './DocumentCardSummary';
import { ExpandedRowContent } from './ExpandedRowContent';
import { TagActionBar } from './TagActionBar';
import { getBorderColorClass } from './utils';

interface AnalyzaData {
  kategorie_vlk?: string[];
  typ_zasahu?: string[];
  typ_dokumentu?: string;
  cislo_konania_spisu?: string;
  ziadatel_navrhovatel?: string;
  zakony?: Array<{ cislo: string; paragrafy?: string[] }>;
  gis?: {
    source_type?: string;
    zasiahnute_chranene_uzemia?: Record<string, any>;
  };
  typ_uzemia?: string[];
  miesto_realizacie?: Record<string, any>;
  myTag?: string | null;
  zhrnutie?: string;
  dotknute_zivocichy_rastliny?: string[];
  [key: string]: any; // Allow other properties
}

interface DocumentDetailViewProps {
  docId: string;
  datum_display: string;
  data: {
    analyza?: AnalyzaData;
    nazov?: string;
    url?: string;
    hasGis: boolean;
  };
}

export const DocumentDetailView = ({
  docId,
  datum_display,
  data
}: DocumentDetailViewProps) => {
  const isAuthenticated = useStore($isAuthenticated);
  const [currentTag, setCurrentTag] = useState<string | null>(data?.analyza?.myTag || null);
  const [borderColorClass, setBorderColorClass] = useState<string>(getBorderColorClass(data?.analyza || {}));

  // Sync tag state when props change
  useEffect(() => {
    setCurrentTag(data?.analyza?.myTag || null);
  }, [data?.analyza?.myTag]);

  // Recalculate border color when tag changes
  useEffect(() => {
    setBorderColorClass(getBorderColorClass(data?.analyza || {}));
  }, [currentTag, data?.analyza]);

  return (
    <div
      className={`bg-white rounded-xl shadow-md border-l-4 overflow-hidden w-full ${borderColorClass}`}
    >
      <div className="p-4">
        <DocumentCardSummary
          docId={docId}
          datum_display={datum_display}
          data={{
            analyza: data.analyza,
            nazov: data.nazov
          }}
          hasGis={data?.hasGis || false}
          tagUI={
            isAuthenticated ? (
              <div onClick={e => e.stopPropagation()}>
                <TagActionBar
                  docId={docId}
                  datum={datum_display}
                  currentTag={currentTag}
                  onTagChange={(docId, datum, newTag, oldTag) => {
                    setCurrentTag(newTag);
                  }}
                  isPending={false}
                  labelSide={true}
                />
              </div>
            ) : undefined
          }
        />
      </div>

      {/* Always render expanded content */}
      <div className="bg-gray-50 border-t border-gray-200">
        <ExpandedRowContent
          row={{
            original: {
              docId,
              datum_display,
              ...data?.analyza,
              url: data?.url,
              hasGis: data?.hasGis,
              myTag: currentTag
            }
          }}
          onLinkClick={(docId) => {
            // Copy link to clipboard
            const url = `/doc/${docId}`;
            navigator.clipboard.writeText(url).catch((err) => {
              console.error('Failed to copy link:', err);
            });
          }}
        />
      </div>
    </div>
  );
};
