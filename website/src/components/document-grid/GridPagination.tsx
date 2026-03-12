import React from 'react';
import type { Table } from '@tanstack/react-table';

interface GridPaginationProps {
  table: Table<any>;
}

export const GridPagination = ({ table }: GridPaginationProps) => {
  return (
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
  );
};

