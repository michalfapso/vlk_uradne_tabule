# [docId].astro Card Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor card components to extract shared header logic, make [docId].astro visually consistent with the grid, and support authenticated tagging.

**Architecture:** Extract `DocumentCardSummary` from `EvaluationCard` to enable code reuse. Rename existing components for clarity. Create `DocumentDetailView` React island for [docId].astro. No changes to grid behavior.

**Tech Stack:** React, Astro, Convex, TanStack Table, Tailwind CSS

---

## File Structure

### Files to Create
- `website/src/components/document-grid/DocumentCardSummary.tsx` — Extracted card header component
- `website/src/components/document-grid/DocumentDetailView.tsx` — React island for [docId].astro

### Files to Modify
- `website/src/components/document-grid/EvaluationCard.tsx` — Refactor to use DocumentCardSummary (rename to DocumentCard.tsx)
- `website/src/pages/doc/[docId].astro` — Add DocumentDetailView island + navigation + max-width container

### Files to Rename (Optional cleanup)
- `website/src/components/document-grid/DesktopTable.tsx` → `DocumentTable.tsx`
- `website/src/components/document-grid/ExpandedRowContent.tsx` → `DocumentDetail.tsx`

### Import Updates Required (after renames)
- `TanStackDocumentGrid.tsx` — Update imports for renamed components
- `DocumentDetailView.tsx` — Import renamed components
- Any other imports of renamed files

---

## Chunk 1: Extract DocumentCardSummary

### Task 1: Create DocumentCardSummary.tsx (Static Component)

**Files:**
- Create: `website/src/components/document-grid/DocumentCardSummary.tsx`

- [ ] **Step 1: Write empty component with props interface**

```typescript
import React from 'react';
import { categoryColors } from './constants';
import { formatDate, getBorderColorClass } from './utils';

interface DocumentCardSummaryProps {
  docId: string;
  datum_display: string;
  data: {
    analyza?: {
      kategorie_vlk?: string[];
      typ_zasahu?: string[];
      miesto_realizacie?: Record<string, any>;
      ziadatel_navrhovatel?: string;
      zakony?: Array<{ cislo: string; paragrafy?: string[] }>;
      gis?: Record<string, any>;
      typ_uzemia?: string[];
    };
    nazov?: string;
  };
  hasGis: boolean;
  myTag?: string | null;
  tagUI?: React.ReactNode; // Optional slot for TagActionBar
}

export const DocumentCardSummary = ({
  docId,
  datum_display,
  data,
  hasGis,
  myTag,
  tagUI
}: DocumentCardSummaryProps) => {
  const a = data.analyza || {};

  return (
    <div>
      {/* Will be filled with extracted markup */}
    </div>
  );
};
```

- [ ] **Step 2: Extract badge rendering markup from EvaluationCard.tsx (lines 49–83)**

Copy the badges section (kategorie_vlk, ochrana badges, MAPA link) into the component.

```typescript
const a = data.analyza || {};

return (
  <div>
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mb-3">
      <div className="text-xs font-bold text-gray-500 uppercase whitespace-nowrap">{formatDate(datum_display)}</div>

      {tagUI && (
        <div onClick={e => e.stopPropagation()}>
          {tagUI}
        </div>
      )}

      <div className="flex flex-wrap gap-1">
        {(a.kategorie_vlk || []).map((cat: string, idx: number) => (
          <span key={idx} className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase ${categoryColors[cat] || 'bg-gray-200 text-gray-700'}`}>
            {cat}
          </span>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-1">
        {/* Ochrana Badges */}
        {a.gis?.source_type && (
          <span className="px-1.5 py-0.5 bg-gray-600 text-white rounded text-[8px] font-bold uppercase shadow-sm">
            {a.gis.source_type === 'KATASTRALNE_UZEMIE' ? 'KU' : a.gis.source_type}
          </span>
        )}
        {a.gis?.zasiahnute_chranene_uzemia?.['5st_konsUEV'] && <span className="px-1.5 py-0.5 bg-red-700 text-white rounded text-[8px] font-bold uppercase shadow-sm">5. STUPEŇ!</span>}
        {(a.gis?.zasiahnute_chranene_uzemia?.['UEV'] || a.gis?.zasiahnute_chranene_uzemia?.['CHVU']) && <span className="px-1.5 py-0.5 bg-green-700 text-white rounded text-[8px] font-bold uppercase shadow-sm">Natura 2000</span>}
        {Array.isArray(a.typ_uzemia) && a.typ_uzemia.some((t: string) => /chko|národný park/i.test(t)) && (
          <span className="px-1.5 py-0.5 bg-green-600 text-white rounded text-[8px] font-bold uppercase shadow-sm">CHKO/NP</span>
        )}
        {a.miesto_realizacie?.lokalita_zastavane_uzemie && (
          <span className="px-1.5 py-0.5 bg-gray-400 text-white rounded text-[8px] font-bold uppercase shadow-sm">Intravilán</span>
        )}

        {hasGis && (
          <a
            href={`https://michalfapso.github.io/vlk_zonacia_tanap/?ext_url=https://michalfapso.github.io/vlk_uradne_tabule/data/${docId}/gis.geojson&ext_crs=EPSG:4326`}
            target="_blank"
            onClick={(e) => e.stopPropagation()}
            className="px-1.5 py-0.5 bg-blue-100 text-blue-800 border border-blue-200 rounded text-[8px] font-bold uppercase shadow-sm hover:bg-blue-200 transition-colors cursor-pointer no-underline"
          >
            🗺️ MAPA
          </a>
        )}
      </div>
    </div>
```

- [ ] **Step 3: Extract title and summary markup (lines 86–111)**

Add the title and inline summary section.

```typescript
    <h4 className="text-sm font-bold text-gray-900 mb-2 leading-snug line-clamp-2">
      {Array.isArray(a.typ_zasahu) ? a.typ_zasahu.join(", ") : (a.typ_zasahu || data.nazov || "-")}
    </h4>

    <div className="flex flex-col sm:flex-row sm:flex-wrap gap-x-6 gap-y-2 text-[11px] mb-1">
      <div className="flex items-center gap-2">
        <span className="text-gray-500 text-[9px] uppercase font-bold tracking-tighter whitespace-nowrap">Lokalita:</span>
        <span className="font-bold text-gray-800">{a.miesto_realizacie?.obec || "-"}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-gray-500 text-[9px] uppercase font-bold tracking-tighter whitespace-nowrap">Žiadateľ:</span>
        <span className="font-medium text-blue-800 line-clamp-1">{a.ziadatel_navrhovatel || "-"}</span>
      </div>
      {a.zakony && Array.isArray(a.zakony) && a.zakony.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-gray-500 text-[9px] uppercase font-bold tracking-tighter whitespace-nowrap">Zákony:</span>
          <span className="font-medium text-gray-800">
            {a.zakony.map((l: any, idx: number) => (
              <span key={idx}>
                {idx > 0 && ", "}{l.cislo}{l.paragrafy ? ` (§ ${l.paragrafy.join(", ")})` : ""}
              </span>
            ))}
          </span>
        </div>
      )}
    </div>
  </div>
);
```

- [ ] **Step 4: Run TypeScript check to verify no errors**

```bash
npm run type-check
```

Expected: No TypeScript errors in `DocumentCardSummary.tsx`

- [ ] **Step 5: Commit**

```bash
git add website/src/components/document-grid/DocumentCardSummary.tsx
git commit -m "feat: extract DocumentCardSummary component from EvaluationCard

Isolates card header rendering logic (badges, date, title, summary) into
reusable component. Accepts optional tagUI slot for injecting TagActionBar.
Will be used by both EvaluationCard and DocumentDetailView.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Chunk 2: Refactor EvaluationCard to use DocumentCardSummary

### Task 2: Update EvaluationCard.tsx to use DocumentCardSummary

**Files:**
- Modify: `website/src/components/document-grid/EvaluationCard.tsx`

- [ ] **Step 1: Add import for DocumentCardSummary**

At the top of the file, add:

```typescript
import { DocumentCardSummary } from './DocumentCardSummary';
```

- [ ] **Step 2: Replace card header markup with DocumentCardSummary component**

In the component body (inside the `<div>` with className `p-4 cursor-pointer...`), replace lines 35–111 with:

```typescript
<DocumentCardSummary
  docId={data.docId}
  datum_display={data.datum_display}
  data={{
    analyza: data.analyza,
    nazov: data.nazov
  }}
  hasGis={data.hasGis}
  myTag={data.myTag}
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
```

- [ ] **Step 3: Verify EvaluationCard.tsx compiles**

```bash
npm run type-check
```

Expected: No TypeScript errors

- [ ] **Step 4: Test in browser that expand/collapse still works**

Navigate to index.astro and verify:
- Cards render correctly
- Click card to expand → ExpandedRowContent appears
- Click again to collapse → ExpandedRowContent disappears
- No console errors

- [ ] **Step 5: Commit**

```bash
git add website/src/components/document-grid/EvaluationCard.tsx
git commit -m "refactor: use DocumentCardSummary in EvaluationCard

Replace inline card header markup with DocumentCardSummary component.
Behavior unchanged; expand/collapse still works via row state.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Chunk 3: Create DocumentDetailView Component

### Task 3: Create DocumentDetailView.tsx (React island for [docId].astro)

**Files:**
- Create: `website/src/components/document-grid/DocumentDetailView.tsx`

- [ ] **Step 1: Write empty component with props interface**

```typescript
import React, { useState } from 'react';
import { useStore } from 'nanostores/react';
import { $isAuthenticated } from '../../auth';
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
    <div>
      {/* Will be filled with card markup */}
    </div>
  );
};
```

- [ ] **Step 2: Add card container and DocumentCardSummary**

```typescript
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
        myTag={currentTag}
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
```

- [ ] **Step 3: Run TypeScript check**

```bash
npm run type-check
```

Expected: No TypeScript errors

- [ ] **Step 4: Commit**

```bash
git add website/src/components/document-grid/DocumentDetailView.tsx
git commit -m "feat: create DocumentDetailView for [docId].astro

New React island component for document detail page. Always shows expanded
content, supports authenticated tagging via TagActionBar. Wraps
DocumentCardSummary + ExpandedRowContent.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Chunk 4: Update [docId].astro Page

### Task 4: Integrate DocumentDetailView into [docId].astro

**Files:**
- Modify: `website/src/pages/doc/[docId].astro`

- [ ] **Step 1: Add imports for DocumentDetailView and ConvexClientProvider**

At the top of the frontmatter section, add:

```typescript
import DocumentDetailView from '../../components/document-grid/DocumentDetailView.tsx';
import ConvexClientProvider from '../../components/ConvexClientProvider.tsx';
```

- [ ] **Step 2: Extract datum_display from meta or analysis**

In the frontmatter, after the existing metadata extraction (around line 92), add:

```typescript
// Extract datum_display (used for tagging)
const datum_display = meta?.datum || analysis?.datum_dokumentu || 'N/A';

// Construct data object for DocumentDetailView
const documentData = {
  analyza: analysis || {},
  nazov: meta?.nazov || null,
  url: meta?.url || null,
  hasGis: fs.existsSync(gisPath)
};
```

- [ ] **Step 3: Replace page content with new layout**

Replace the entire `<Layout>` section (lines 99–244) with:

```astro
<Layout title={`Document: ${docId}`}>
  <ConvexClientProvider>
    <div class="container p-4 max-w-[1200px] mx-auto">
      {/* Navigation Header */}
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-gray-900">Document Details</h1>
        <a
          href="/"
          class="inline-flex items-center px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
        >
          ← Back to Documents
        </a>
      </div>

      {/* DocumentDetailView Component */}
      <DocumentDetailView
        client:load
        docId={docId}
        datum_display={datum_display}
        data={documentData}
        isAuthenticated={false}
      />
    </div>
  </ConvexClientProvider>
</Layout>
```

- [ ] **Step 4: Verify page renders correctly**

Navigate to a document URL (e.g., `/doc/some-document-id`) and verify:
- Page loads without errors
- Card displays with correct styling
- Navigation link "← Back to Documents" is visible and clickable
- Expanded content is always visible (no collapse button)
- GIS badge and MAPA link render correctly
- If authenticated: TagActionBar appears in header

- [ ] **Step 5: Test unauthenticated view**

Open the page in incognito mode or clear auth state, verify:
- Page still renders
- TagActionBar is hidden
- All other content is visible

- [ ] **Step 6: Commit**

```bash
git add website/src/pages/doc/[docId].astro
git commit -m "feat: integrate DocumentDetailView into [docId].astro

Replace basic layout with DocumentDetailView component (React island).
Adds navigation header with link back to index. Constrains card to 1200px,
centers on page. Always shows expanded details.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Chunk 5: Optional Component Renaming (Polish)

### Task 5: Rename DesktopTable → DocumentTable

**Files:**
- Move: `website/src/components/document-grid/DesktopTable.tsx` → `website/src/components/document-grid/DocumentTable.tsx`
- Modify: All files that import DesktopTable

- [ ] **Step 1: Rename the file**

```bash
git mv website/src/components/document-grid/DesktopTable.tsx website/src/components/document-grid/DocumentTable.tsx
```

- [ ] **Step 2: Update export in DocumentTable.tsx**

In the file, change:
```typescript
export const DesktopTable = (...)
```
to:
```typescript
export const DocumentTable = (...)
```

- [ ] **Step 3: Update imports in TanStackDocumentGrid.tsx**

Find and replace:
```typescript
import { DesktopTable } from './document-grid/DesktopTable';
```
with:
```typescript
import { DocumentTable } from './document-grid/DocumentTable';
```

And update any usage of `<DesktopTable` to `<DocumentTable`.

- [ ] **Step 4: Run TypeScript check**

```bash
npm run type-check
```

Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add website/src/components/document-grid/DocumentTable.tsx website/src/components/TanStackDocumentGrid.tsx
git commit -m "refactor: rename DesktopTable → DocumentTable for clarity

Improves naming consistency: DocumentCard, DocumentTable, DocumentDetail
reflect what they render, not screen size.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

### Task 6: Rename ExpandedRowContent → DocumentDetail

**Files:**
- Move: `website/src/components/document-grid/ExpandedRowContent.tsx` → `website/src/components/document-grid/DocumentDetail.tsx`
- Modify: All files that import ExpandedRowContent

- [ ] **Step 1: Rename the file**

```bash
git mv website/src/components/document-grid/ExpandedRowContent.tsx website/src/components/document-grid/DocumentDetail.tsx
```

- [ ] **Step 2: Update export in DocumentDetail.tsx**

Change:
```typescript
export const ExpandedRowContent = (...)
```
to:
```typescript
export const DocumentDetail = (...)
```

- [ ] **Step 3: Update imports in all files that reference ExpandedRowContent**

Files to check and update:
- `website/src/components/document-grid/EvaluationCard.tsx`
- `website/src/components/document-grid/DocumentTable.tsx`
- `website/src/components/document-grid/DocumentDetailView.tsx`

Replace:
```typescript
import { ExpandedRowContent } from './ExpandedRowContent';
```
with:
```typescript
import { DocumentDetail } from './DocumentDetail';
```

And update component usage from `<ExpandedRowContent` to `<DocumentDetail`.

- [ ] **Step 4: Run TypeScript check**

```bash
npm run type-check
```

Expected: No errors

- [ ] **Step 5: Test grid and detail page**

- Navigate to index.astro, verify grid still works
- Navigate to [docId].astro, verify page still works
- No console errors

- [ ] **Step 6: Commit**

```bash
git add website/src/components/document-grid/DocumentDetail.tsx website/src/components/document-grid/EvaluationCard.tsx website/src/components/document-grid/DocumentTable.tsx website/src/components/document-grid/DocumentDetailView.tsx
git commit -m "refactor: rename ExpandedRowContent → DocumentDetail

Clarifies component purpose. Used in DocumentCard, DocumentTable, and
DocumentDetailView for showing expanded analysis details.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Final Verification

### Task 7: Integration Testing and Verification

- [ ] **Step 1: Build the project**

```bash
npm run build
```

Expected: Build succeeds, no errors or warnings related to renamed imports

- [ ] **Step 2: Test grid view (index.astro)**

Navigate to `/` and verify:
- Documents render in grid
- Cards show badges, date, title, summary
- TagActionBar appears for authenticated users
- Click card to expand → shows ExpandedRowContent
- Click again to collapse
- MAPA links work
- No visual regressions

- [ ] **Step 3: Test detail view ([docId].astro)**

Navigate to `/doc/{docId}` and verify:
- Card renders with same styling as grid
- Navigation header with "← Back to Documents" link visible
- Card is constrained to ~1200px, centered
- Always-expanded content visible (no collapse button)
- If authenticated: TagActionBar works, tag changes save
- If not authenticated: TagActionBar hidden
- GIS badge and MAPA links render correctly
- Edge cases: missing data fields don't cause errors

- [ ] **Step 4: Cross-browser testing (optional but recommended)**

Test on:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (if available)
- Mobile viewport (375px width)

Verify card layout is responsive on all screen sizes.

- [ ] **Step 5: Performance check (optional)**

Run Lighthouse on both pages:
```bash
npm run lighthouse -- https://localhost:3000/
npm run lighthouse -- https://localhost:3000/doc/{any-docId}
```

Verify no significant regressions in performance metrics.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "test: verify all pages render and behave correctly

Tested grid view, detail page, authentication states, edge cases.
All cards render with consistent styling. No visual regressions."
```

---

## Success Criteria Verification

Before marking implementation complete, verify:

- ✅ [docId].astro displays document card identical to grid card view
- ✅ Always-expanded detail section visible (no collapse button)
- ✅ Authenticated users can set tags on detail page
- ✅ Link to index.astro (/) visible in header
- ✅ Card max-width is ~1200px, centered on page
- ✅ Grid expand/collapse behavior unchanged
- ✅ No visual regressions in grid view
- ✅ No TypeScript errors
- ✅ No console errors in browser
- ✅ Build completes successfully

---

## Notes for Implementer

1. **DocumentCardSummary is stateless:** It only renders markup based on props. No hooks, no state. This keeps it simple and reusable.

2. **DocumentDetailView manages tag state:** Uses `useState` to track current tag. When TagActionBar changes tag, update state. The component doesn't persist to Convex (that's TagActionBar's job via mutation).

3. **ExpandedRowContent (now DocumentDetail) expects `row.original`:** When calling it from DocumentDetailView, pass a mock row object with structure: `{ original: { docId, datum_display, ...analysisData } }`.

4. **Client:load vs client:idle:** Using `client:load` ensures the React island hydrates immediately. This is important for authentication checks and tag updates.

5. **Auth check at runtime:** [docId].astro passes `isAuthenticated={false}` at build time. DocumentDetailView then calls `useStore($isAuthenticated)` at runtime to get the actual auth state and conditionally show TagActionBar.

6. **Styling reuse:** All Tailwind classes are copied from EvaluationCard. No new CSS needed. The border color, badges, text sizing all match exactly.

7. **Testing order:** Test Phase 2 (refactored grid) before moving to Phase 3 (new detail page). This way if grid breaks, you know it's from Phase 2 changes.

8. **Git hygiene:** One commit per task. Clear, descriptive commit messages. Tests can be combined into final verification commit.
