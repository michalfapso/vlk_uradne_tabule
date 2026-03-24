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

**Change:** Restructure the navigation area to add a header bar with AuthSection

**New structure:**
1. Add a header bar above the main content with:
   - Back button on the left
   - AuthSection on the right
   - Gray background (`bg-gray-50`) and border-bottom (`border-b`)
   - Flex layout with `justify-between` for spacing

2. Keep the "Document Details" heading in the main content area

**Code pattern:**
```astro
<div class="flex justify-between items-center p-4 bg-gray-50 border-b">
    <a href="/">
        ← Back to Documents
    </a>
    <Header client:load />
</div>

<Layout title={...}>
    <ConvexClientProvider>
        <div class="p-4 max-w-[1200px] mx-auto">
            <h1 class="text-2xl font-bold text-gray-900 mb-6">Document Details</h1>
            {/* DocumentDetailView component */}
        </div>
    </ConvexClientProvider>
</Layout>
```

## Infrastructure Already in Place

- **AuthSection component** (`website/src/components/AuthSection.tsx`): Displays auth status and sign in/out buttons
- **Header component** (`website/src/components/Header.tsx`): Wraps AuthSection with ConvexClientProvider
- **TagActionBar** (`website/src/components/document-grid/TagActionBar.tsx`): Already integrated in DocumentDetailView for authenticated users
- **Importance calculation** (`DocumentDetailView.tsx`): Already uses user tags to affect "Dôležitosť:" field display
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

1. Verify header appears correctly on document detail page
2. Verify AuthSection displays login/logout button appropriately
3. Verify authenticated users see TagActionBar
4. Verify tag selection affects "Dôležitosť:" field display
5. Verify back button navigation works
6. Test responsive behavior on mobile/tablet

## Files to Modify

- `website/src/pages/doc/[docId].astro` - Add header bar with AuthSection

## Dependencies

- No new dependencies needed
- Reuses existing Header and AuthSection components
- Requires ConvexClientProvider wrapping (already present in current layout)

## Risk Assessment

**Low risk** - Purely additive change:
- No modifications to existing component logic
- Reuses battle-tested Header component
- No changes to data flow or authentication system
- Layout restructuring is minimal and straightforward
