import React from 'react';
import { TagActionBar } from './TagActionBar';
import { ExpandedRowContent } from './ExpandedRowContent';
import { DocumentCardSummary } from './DocumentCardSummary';
import { getBorderColorClass } from './utils';

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
  const isExpanded = row.getIsExpanded();
  const borderColorClass = getBorderColorClass(data);
  const isHighlighted = data.docId === highlightedDocId;

  return (
    <div 
      id={`doc-card-${data.docId}`}
      className={`bg-white rounded-xl shadow-md border-l-4 overflow-hidden transition-all duration-700 w-full ${borderColorClass} ${isPending ? 'opacity-0 max-h-0 mb-0 pointer-events-none' : 'opacity-100 mb-4'} ${isHighlighted ? 'ring-2 ring-blue-500 ring-inset bg-blue-50' : ''} ${!data.isImportant && !isPending ? 'grayscale-[0.3]' : ''} ${isExpanded ? 'max-h-none' : 'max-h-[1000px]'}`}
      onClick={() => row.toggleExpanded()}
    >
      <div className={`p-4 cursor-pointer transition-all duration-700 ${isPending ? 'py-0' : 'py-4'}`}>
        <DocumentCardSummary
          docId={data.docId}
          datum_display={data.datum_display}
          data={{
            analyza: data.analyza,
            nazov: data.nazov
          }}
          hasGis={data.hasGis}
          tagUI={
            isAuthenticated ? (
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
            ) : undefined
          }
        />
      </div>
      
      {isExpanded && (
        <div className="bg-gray-50 border-t border-gray-200 animate-in slide-in-from-top duration-200">
          <ExpandedRowContent row={row} onLinkClick={onLinkClick} />
        </div>
      )}
    </div>
  );
};


