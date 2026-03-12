import React from 'react';
import { flexRender, type Table } from '@tanstack/react-table';
import { ExpandedRowContent } from './ExpandedRowContent';
import { getBorderColorClass } from './utils';

interface DesktopTableProps {
  table: Table<any>;
  pendingHides: Record<string, boolean>;
}

export const DesktopTable = ({ table, pendingHides }: DesktopTableProps) => {
  const columnsCount = table.getVisibleLeafColumns().length;

  return (
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
            {table.getRowModel().rows.map(row => {
              const isPending = pendingHides[row.original.docId];
              const data = row.original;
              const borderColorClass = getBorderColorClass(data);

              return (
                <React.Fragment key={row.id}>
                  <tr 
                    className={`border-b border-gray-100 transition-all duration-700 cursor-pointer border-l-4 ${borderColorClass} ${row.getIsExpanded() ? 'bg-blue-50/50' : 'hover:bg-gray-50'} ${!data.isImportant && !isPending ? 'opacity-60 grayscale-[0.4]' : ''} ${isPending ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
                    onClick={() => row.toggleExpanded()}
                  >
                    {row.getVisibleCells().map(cell => (
                      <td key={cell.id} className="p-0 align-top">
                        <div className={`p-3 transition-all duration-700 ${isPending ? 'max-h-0 py-0 opacity-0 overflow-hidden' : 'max-h-[200px]'}`}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </div>
                      </td>
                    ))}
                  </tr>
                  {row.getIsExpanded() && !isPending && (
                    <tr>
                      <td colSpan={columnsCount} className="p-0 border-b border-gray-200">
                        <ExpandedRowContent row={row} />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
