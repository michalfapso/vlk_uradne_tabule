---
name: AuthSection on Document Detail Page
description: Add authentication status display to document detail page top bar, styled consistently with main page
type: design
status: approved
date: 2026-03-24
---

# AuthSection on Document Detail Page Design

## Overview

Add the AuthSection component to the document detail page (`website/src/pages/doc/[docId].astro`) to display user authentication status and enable access to custom tagging features. The component will be styled consistently with the main page header.

## Problem Statement

Currently, the document detail page does not display authentication status, which means:
- Users cannot see if they're logged in when viewing document details
- The UI doesn't clearly indicate that tagging features are available to authenticated users
- Inconsistent header styling between the main page and detail page

## Solution

Add a header bar to the document detail page matching the main page pattern, with:
- Back button on the left
- AuthSection on the right
- Consistent gray background and border styling

## Current State

**Main page (`index.astro`):**
```astro
<div class="flex justify-end p-4 bg-gray-50 border-b">
    <Header client:load />
</div>
```

**Document detail page (`[docId].astro`):**
```astro
<div class="flex items-center justify-between mb-6">
    <h1 class="text-2xl font-bold text-gray-900">Document Details</h1>
    <a href="/" class="inline-flex items-center px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors">
        ← Back to Documents
    </a>
</div>
```

## Proposed Changes

### File: `website/src/pages/doc/[docId].astro`

**Change:** Add a header bar above the content with AuthSection (via Header component), using separate React islands to avoid ConvexClientProvider nesting conflicts.

**Current structure:**
```astro
<Layout>
  <ConvexClientProvider>
    <div class="p-4 max-w-[1200px] mx-auto">
      {/* Navigation with back button */}
      <div class="flex items-center justify-between mb-6">
        <h1>Document Details</h1>
        <a href="/">← Back to Documents</a>
      </div>
      {/* DocumentDetailView component */}
    </div>
  </ConvexClientProvider>
</Layout>
```

**New structure:**

1. Add a header bar ABOVE the existing ConvexClientProvider (matching main page pattern)
2. Header is its own React island with `client:load` containing AuthSection
3. Header's internal ConvexClientProvider handles auth for the entire page
4. Existing ConvexClientProvider wraps only DocumentDetailView content
5. Move "Document Details" heading into the main content area

**Code implementation:**
```astro
<Layout title={...}>
  {/* Header bar with navigation - separate React island */}
  <div class="flex justify-between items-center p-4 bg-gray-50 border-b">
    <a
      href="/"
      class="inline-flex items-center px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
    >
      ← Back to Documents
    </a>
    <Header client:load />
  </div>

  {/* Main content */}
  <ConvexClientProvider>
    <div class="p-4 max-w-[1200px] mx-auto">
      <h1 class="text-2xl font-bold text-gray-900 mb-6">Document Details</h1>
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

**Provider architecture:**
- **Header component** (its own React island): Contains ConvexClientProvider wrapping AuthSection - provides auth state to entire page
- **DocumentDetailView component** (separate React island inside ConvexClientProvider): Uses Convex queries and auth state from Header's provider
- This follows the same pattern as index.astro which also has Header at top level and document grid below

## Infrastructure Already in Place

- **AuthSection component** (`website/src/components/AuthSection.tsx`): Displays auth status and sign in/out buttons using Convex auth
- **Header component** (`website/src/components/Header.tsx`): Wraps AuthSection with ConvexClientProvider, creating the auth provider for the page
- **ConvexClientProvider** (`website/src/components/ConvexClientProvider.tsx`): Provides Convex auth state - only ONE should exist per page
- **TagActionBar** (`website/src/components/document-grid/TagActionBar.tsx`): Already integrated in DocumentDetailView for authenticated users
- **DocumentDetailView** (`website/src/components/document-grid/DocumentDetailView.tsx`):
  - Already uses `$isAuthenticated` from nanostores to conditionally display TagActionBar
  - Already calculates importance based on user tags
- **Importance calculation** (DocumentDetailView.tsx, line 26-42): Already uses user tags to affect "Dôležitosť:" field display
  - When user sets a tag to 'dôležité' or 'vstupujeme do správneho konania', it overrides the auto-detected importance

## Expected Behavior

**Before authentication:**
- Header bar shows back button and sign-in button

**After authentication:**
- Header bar shows back button and user name + sign-out button
- TagActionBar becomes visible in the document detail section
- User can apply tags which immediately affect the "Dôležitosť:" field display

## Styling Consistency

- Uses existing gray color scheme from main page
- Reuses Header component for consistent appearance
- Maintains responsive design with flexible spacing

## Testing Considerations

1. **Header rendering** - Verify header bar appears correctly with gray background and border
2. **Auth status display** - Verify AuthSection shows login button (unauthenticated) or user name + logout button (authenticated)
3. **TagActionBar visibility** - Verify TagActionBar is only visible in DocumentDetail section when authenticated
4. **Tag functionality** - Verify tag selection immediately affects "Dôležitosť:" field display (overrides auto-detection)
5. **Navigation** - Verify back button successfully navigates to home page
6. **React island isolation** - Verify Header and DocumentDetailView are separate React islands that don't cause console errors
7. **Responsive design** - Test on mobile/tablet:
   - Header items should maintain layout (flex justify-between)
   - Back button text should fit or truncate gracefully
   - AuthSection should remain accessible and clickable
8. **Auth state persistence** - Verify authentication state from Header is accessible to DocumentDetailView across page navigation

## Files to Modify

- `website/src/pages/doc/[docId].astro` - Add header bar with AuthSection and restructure ConvexClientProvider placement

## Files NOT to Modify

- `website/src/components/Header.tsx` - No changes needed
- `website/src/components/AuthSection.tsx` - No changes needed
- `website/src/components/document-grid/DocumentDetailView.tsx` - No changes needed (already has auth-aware logic)
- `website/src/components/ConvexClientProvider.tsx` - No changes needed

## Dependencies

- No new dependencies needed
- Reuses existing Header and AuthSection components
- Reuses existing ConvexClientProvider infrastructure
- Maintains separation of React islands for proper auth state management

## Risk Assessment

**Very Low Risk** - Minimal, isolated change:
- No modifications to existing component logic
- Reuses battle-tested Header component (already working on main page)
- No changes to data flow or authentication system
- Moves existing ConvexClientProvider (no logic change, just positioning)
- Layout restructuring follows established pattern from index.astro
- Separate React islands prevent provider conflicts
- Verification is straightforward (visual inspection + tag functionality test)
