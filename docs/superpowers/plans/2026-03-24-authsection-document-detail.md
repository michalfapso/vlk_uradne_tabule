# AuthSection on Document Detail Page - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AuthSection to the document detail page header bar, enabling users to see authentication status and access tagging features on the document details view.

**Architecture:** Restructure `[docId].astro` to place Header (containing AuthSection) above the main content as a separate React island, with ConvexClientProvider wrapping only the main content. This follows the pattern used in `index.astro` and leverages the singleton Convex client to maintain auth state sync across islands via nanostores.

**Tech Stack:** Astro, React (via islands), Convex auth, nanostores

---

## File Structure

**Files to modify:**
- `website/src/pages/doc/[docId].astro` - Restructure header and ConvexClientProvider placement

**No new files created** - Reuses existing Header, AuthSection, DocumentDetailView components

---

## Task 1: Understand Current Structure

- [ ] **Step 1: Review current [docId].astro file**

Open: `website/src/pages/doc/[docId].astro`

Current structure (lines 130-154):
```astro
<Layout title={pageTitle}>
  <ConvexClientProvider>
    <div class="p-4 max-w-[1200px] mx-auto">
      {/* Navigation Header */}
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-gray-900">Document Details</h1>
        <a href="/" class="inline-flex items-center px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors">
          ← Back to Documents
        </a>
      </div>
      {/* DocumentDetailView Component */}
      <DocumentDetailView ... />
    </div>
  </ConvexClientProvider>
</Layout>
```

- [ ] **Step 2: Verify necessary imports**

Check: `website/src/pages/doc/[docId].astro` (lines 1-15)

Ensure these imports exist:
- `import Layout from '../../layouts/Layout.astro';` ✓ (line 9)
- `import { DocumentDetailView } from '../../components/document-grid/DocumentDetailView.tsx';` ✓ (line 12)
- `import ConvexClientProvider from '../../components/ConvexClientProvider.tsx';` ✓ (line 13)

**Need to add** (if not present):
- `import Header from '../../components/Header.tsx';`

- [ ] **Step 3: Compare with index.astro header pattern**

Open: `website/src/pages/index.astro` (lines 360-362)

Note the pattern:
```astro
<div class="flex justify-end p-4 bg-gray-50 border-b">
    <Header client:load />
</div>
```

Header is a separate React island. Its internal ConvexClientProvider combines with DocumentDetailView's wrapper - both use the same singleton Convex client, so auth state syncs via nanostores.

- [ ] **Step 3: Verify Header and AuthSection components work correctly**

Quick check:
- Header.tsx imports AuthSection and wraps it with ConvexClientProvider ✓
- AuthSection.tsx uses Convex auth and updates nanostores auth state ✓
- DocumentDetailView.tsx reads from nanostores $isAuthenticated ✓

---

## Task 2: Add Header Bar to Document Detail Page

- [ ] **Step 1: Add header bar structure above content**

Modify: `website/src/pages/doc/[docId].astro`

Replace the navigation section (lines 130-143) with a new header bar structure:

```astro
<Layout title={pageTitle ? `${pageTitle} - Úradné Tabule` : `Document: ${docId}`}>
  {/* Header bar with navigation - separate React island */}
  <div class="flex justify-between items-center p-4 bg-gray-50 border-b">
    <a
      href="/"
      class="inline-flex items-center px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
      aria-label="Return to document list"
    >
      ← Back to Documents
    </a>
    <Header client:load />
  </div>

  {/* Main content */}
  <ConvexClientProvider>
    <div class="p-4 max-w-[1200px] mx-auto">
      <h1 class="text-2xl font-bold text-gray-900 mb-6">Document Details</h1>

      {/* DocumentDetailView Component */}
      <DocumentDetailView
        client:load
        docId={docId}
        datum_display={datum_display}
        data={documentData}
      />
    </div>
  </ConvexClientProvider>
</Layout>
```

Key changes:
- Header bar is OUTSIDE ConvexClientProvider with `flex justify-between` layout
- Back button on left, Header (with AuthSection) on right
- ConvexClientProvider wraps only main content below
- "Document Details" heading moved inside main content div
- Added `aria-label` to back button for accessibility

- [ ] **Step 2: Verify Astro syntax is correct**

Check:
- All Astro tags properly closed
- Import statements at top of file still present
- Props passed correctly to DocumentDetailView
- No syntax errors in the restructured sections

- [ ] **Step 3: Commit the change**

```bash
git add website/src/pages/doc/[docId].astro
git commit -m "feat: add AuthSection to document detail page header

- Add header bar above content with back button and AuthSection
- Restructure ConvexClientProvider to wrap only main content
- Place Header as separate React island to avoid provider conflicts
- Maintain auth state sync via singleton Convex client + nanostores"
```

---

## Task 3: Test Auth State Sync Across Islands

- [ ] **Step 1: Build and start dev server**

```bash
cd website
npm run dev
```

Expected: Development server starts without errors, no provider warnings in console

- [ ] **Step 2: Verify unauthenticated state**

Manual test:
1. Navigate to any document detail page (e.g., `/doc/some-doc-id`)
2. Observe header bar appears with:
   - Back button on left
   - "Prihlásiť sa cez Google" button on right (sign-in button)
3. Scroll down to document details section
4. Verify TagActionBar is NOT visible (since not authenticated)
5. Check browser console (F12) - no provider conflict warnings ✓

- [ ] **Step 3: Test auth state sync when signing in**

Manual test:
1. Click "Prihlásiť sa cez Google" button in header
2. Complete Google sign-in flow
3. **Critical verification:** TagActionBar should appear INSTANTLY in the document detail section below
   - This confirms nanostores state sync between Header and DocumentDetailView islands
4. Verify user name appears in header instead of sign-in button
5. Check browser console - no errors ✓

- [ ] **Step 4: Test tag functionality with auth**

Manual test:
1. While signed in, click tag options in TagActionBar
2. Select a tag (e.g., "dôležité")
3. Verify "Dôležitosť:" field immediately shows:
   - "Áno" status in red
   - Tag badge with selected tag label
4. Try changing tags - verify immediate update

- [ ] **Step 5: Test sign-out and re-sync**

Manual test:
1. Click sign-out button in header
2. **Critical verification:** TagActionBar should disappear INSTANTLY from document detail
   - This confirms reverse sync is working
3. Verify sign-in button reappears in header
4. Check browser console - no errors ✓

- [ ] **Step 6: Verify responsive design**

Manual test on different viewports:
1. Desktop (1920px):
   - Header bar properly spaced with back button left, auth section right
2. Tablet (768px):
   - Items remain in single row with good spacing
3. Mobile (375px):
   - Back button and auth section remain visible and clickable
   - No text overflow
   - Flex layout maintains spacing

- [ ] **Step 7: Check other document pages still work**

Manual test:
1. Navigate back to home page (/)
2. Verify main page header and document grid still work
3. Verify no duplication or conflicts
4. Sign in/out from home page - verify it works
5. Navigate to a different document detail page
6. Verify auth state is still correct

---

## Task 4: Verify No Regressions

- [ ] **Step 1: Test document detail page features**

Manual test each feature:
1. **Original document link:** Click "📄 Pôvodný dokument" button - opens in new tab ✓
2. **GIS map link:** If available, click "🗺️ Mapa" button - opens map ✓
3. **Copy link button:** Click 🔗 button in details section - verify in clipboard ✓
4. **Expandable sections:** Click Status, Laws, Log, JSON sections - they expand/collapse ✓
5. **Document data display:** All fields show correctly (Typ, Číslo, Žiadateľ, etc.) ✓

- [ ] **Step 2: Verify search/filter functionality**

If applicable, test:
1. Navigate to home page
2. Search or filter documents
3. Click on a document to go to detail page
4. Verify all data loads correctly
5. Return to home page - verify no state issues

- [ ] **Step 3: Check console for warnings**

Open browser console (F12):
- No ConvexClientProvider warnings ✓
- No React key warnings ✓
- No hydration mismatches ✓
- No nanostores warnings ✓

- [ ] **Step 4: Final commit if all tests pass**

If all manual tests pass:

```bash
git log --oneline -1
# Should show the commit from Task 2
# If additional fixes were needed, create a new commit:
git add website/src/pages/doc/[docId].astro
git commit -m "test: verify AuthSection integration and auth state sync"
```

---

## Notes for Implementation

**Critical Points:**
1. **React islands must remain separate** - Header and DocumentDetailView are different Astro islands with separate React roots. This is correct and required.
2. **Singleton Convex client architecture** - Both ConvexClientProvider instances (Header's internal and main content's wrapper) use the SAME singleton Convex client instance (`const convex = new ConvexReactClient(convexUrl)` from ConvexClientProvider.tsx). This ensures all providers on the page share the same auth context.
3. **Dual sync mechanism** - Auth state syncs via:
   - **Synchronous:** Singleton Convex client ensures both islands see the same auth context
   - **Observable:** AuthSection updates `$isAuthenticated` nanostores atom, which DocumentDetailView reads via `useStore()` hook
4. **No component logic changes needed** - Header, AuthSection, DocumentDetailView work as-is. This is purely a structural change to [docId].astro.

**Testing Approach:**
- This is primarily a visual/integration change, so manual testing is appropriate
- Focus on auth state sync (the critical new integration point)
- Key test: TagActionBar visibility should change instantly when signing in/out (within <100ms)

**If Something Breaks:**
- Provider conflicts: Check that ConvexClientProvider is NOT nested (should only wrap main content)
- Auth state not syncing: Check browser console for errors, verify Header renders without errors
- TagActionBar not visible: Check $isAuthenticated store is being read correctly in DocumentDetailView

---

## Success Criteria

✅ Header bar appears on document detail page with back button and auth section
✅ Sign-in button appears when unauthenticated
✅ User name + sign-out button appear when authenticated
✅ TagActionBar visibility syncs instantly with auth state (no page reload)
✅ No console warnings about provider conflicts
✅ All existing document detail features continue to work
✅ Responsive design works on mobile/tablet/desktop
✅ Changes committed with clear commit message
