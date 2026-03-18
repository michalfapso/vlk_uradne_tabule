import React, { useState } from 'react';
import { useStore } from 'nanostores/react';
import { $isAuthenticated } from '../../stores/authStore';
import { DocumentCardSummary } from './DocumentCardSummary';
import { ExpandedRowContent } from './ExpandedRowContent';
import { TagActionBar } from './TagActionBar';
import { getBorderColorClass } from './utils';

interface DocumentDetailViewProps {
  docId: string;
  datum_display: string;
  data: {
    analyza?: any;
    nazov?: string;
    url?: string;
    hasGis: boolean;
  };
  isAuthenticated: boolean;
}

export const DocumentDetailView = ({
  docId,
  datum_display,
  data,
  isAuthenticated: initialAuth
}: DocumentDetailViewProps) => {
  const isAuthenticated = useStore($isAuthenticated);
  const [currentTag, setCurrentTag] = useState<string | null>(data?.analyza?.myTag || null);

  const borderColorClass = getBorderColorClass(data?.analyza || {});

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
            isAuthenticated?.value ? (
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
            navigator.clipboard.writeText(url);
          }}
        />
      </div>
    </div>
  );
};
