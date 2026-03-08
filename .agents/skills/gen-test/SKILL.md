---
name: gen-test
description: Generate unit or E2E tests following project conventions
disable-model-invocation: true
arguments:
  - name: target
    description: Path to the file to generate tests for
    required: true
  - name: type
    description: "Test type: unit (default) or e2e"
    required: false
---

# Test Generator

Generate tests for the specified target file following this project's established conventions.

## Unit Tests (Vitest + React Testing Library)

When `type` is `unit` (default):

### File Location & Naming
- Test files go in a `__tests__/` directory adjacent to the source file
- File naming: `{source-name}.test.ts` (for non-React) or `{source-name}.test.tsx` (for React components)

### Imports & Setup
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
```

### Patterns by Source Type

**Component Tests** (reference: `frontend/src/components/common/__tests__/data-table.test.tsx`):
- Define mock data and columns outside `describe` block
- Use `userEvent.setup()` for user interactions
- Test states: loading, empty, error, normal rendering
- Use `data-testid` for reliable element selection
- Mock callbacks with `vi.fn()`, verify with `.toHaveBeenCalledWith()`
- Validate DaisyUI CSS classes and accessibility attributes

**Store Tests** (reference: `frontend/src/stores/__tests__/connection-store.test.ts`):
- Mock API client at module level with `vi.mock("@/lib/api/client")`
- Access store state via `.getState()` directly (no React hooks)
- Reset store in `beforeEach` with `.setState()`
- Test async actions with `.mockResolvedValue()` / `.mockRejectedValue()`
- Validate state transitions and side effects

**Hook Tests** (reference: `frontend/src/hooks/__tests__/use-pagination.test.ts`):
- Use `renderHook` from `@testing-library/react`
- Test initial state and state transitions
- Test edge cases and boundary conditions

**Utility Tests** (reference: `frontend/src/lib/__tests__/formatters.test.ts`):
- Simple input/output assertions
- Cover edge cases: null, undefined, empty, boundary values

### Conventions
- Follow AAA pattern (Arrange, Act, Assert)
- Test both success and failure paths
- Group related tests in nested `describe` blocks
- Use descriptive test names: `it("should display loading spinner when isLoading is true")`

## E2E Tests (Playwright)

When `type` is `e2e`:

### File Location & Naming
- Spec files go in `frontend/e2e/specs/`
- Follow numbered naming: `XX-feature-name.spec.ts`
- Check existing files to determine the next number

### Patterns (reference: `frontend/e2e/specs/01-connection.spec.ts`)
- Use Page Object Model pattern with a class per page/feature
- Import `test`, `expect` from `@playwright/test`
- Create page object in `test.beforeEach()`
- Use helper methods: `goto()`, form helpers, action methods
- Assertions: `expect(...).toBeVisible({ timeout: 10_000 })` for async waits
- Use `expectToast()` utility for toast notifications
- Capture screenshots at key test points with `screenshot()` helper

### Config Awareness
- Base URL: `http://localhost:3100`
- Sequential execution (`workers: 1`)
- `setup` project runs `01-connection.spec.ts` first; other tests depend on it
- Global setup/teardown at `e2e/global-setup.ts` and `e2e/global-teardown.ts`

## Execution

After generating tests, run them to verify:
- Unit: `cd frontend && npm run test -- {test-file-path}`
- E2E: `cd frontend && npx playwright test {spec-file-path}`
