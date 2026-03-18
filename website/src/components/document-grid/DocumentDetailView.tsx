import React, { useState, useEffect, useMemo } from 'react';
import { useStore } from '@nanostores/react';
import { $isAuthenticated } from '../../stores/authStore';
import { DocumentCardSummary } from './DocumentCardSummary';
import { DocumentDetail } from './DocumentDetail';
import { TagActionBar } from './TagActionBar';
import { getBorderColorClass } from './utils';
import { isDataImportant, DEFAULT_REGEX_STRING } from '../../scripts/documentAnalysis.js';

interface DocumentDetailViewProps {
  docId: string;
  datum_display: string;
  data: Record<string, any>;
}

export const DocumentDetailView = ({
  docId,
  datum_display,
  data
}: DocumentDetailViewProps) => {
  const isAuthenticated = useStore($isAuthenticated);
  const [currentTag, setCurrentTag] = useState<string | null>(data?.analyza?.myTag || null);
  const [borderColorClass, setBorderColorClass] = useState<string>(getBorderColorClass(data?.analyza || {}));

  // Calculate importance properties
  const importanceData = useMemo(() => {
    let blacklistRegex: RegExp | null = null;
    try {
      blacklistRegex = new RegExp(DEFAULT_REGEX_STRING, "i");
    } catch (e) {
      console.error("Invalid regex:", e);
    }

    const importance = isDataImportant(data, blacklistRegex);
    const isImportantSystem = importance.important;

    return {
      isImportant: currentTag ? (currentTag === 'dôležité' || currentTag === 'vstupujeme do správneho konania') : isImportantSystem,
      isImportantSystem,
      importanceReason: importance.reason
    };
  }, [data, currentTag]);

  // Sync tag state when props change
  useEffect(() => {
    setCurrentTag(data?.analyza?.myTag || null);
  }, [data?.analyza?.myTag]);

  // Recalculate border color when tag changes
  useEffect(() => {
    const dataWithImportance = { ...data?.analyza, ...importanceData };
    setBorderColorClass(getBorderColorClass(dataWithImportance));
  }, [currentTag, data?.analyza, importanceData]);

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
        <DocumentDetail
          row={{
            original: {
              ...data,
              myTag: currentTag,
              ...importanceData
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
