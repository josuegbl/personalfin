---
name: "BankFinances Frontend"
description: "Use when modifying the React, TypeScript, Vite, Tailwind, React Query, pages, components, or frontend API integration in frontend/."
applyTo: ["frontend/src/**/*.ts", "frontend/src/**/*.tsx", "frontend/*.ts", "frontend/*.js", "frontend/*.json"]
---

# Frontend Instructions

- The frontend is React 18 + TypeScript + Vite + Tailwind CSS. Keep the existing structure: pages in `frontend/src/pages/`, shared UI in `frontend/src/components/`, API calls in `frontend/src/api/client.ts`, and shared domain types in `frontend/src/types/index.ts`.
- User-facing text is Spanish. Preserve the existing visual language, Tailwind utility style, `clsx` conditionals, `lucide-react` icons, and Spanish currency/date formatting helpers in `frontend/src/utils/format.ts`.
- Treat backend field names and the `/api/v1` contract as shared API surface. When changing a request or response, update the matching TypeScript type and backend schema/router together.
- Use the existing React Query patterns and resource-oriented query keys. After mutations, invalidate every affected query, including accounts, dashboard, transactions, and forecast data as applicable.
- Preserve forecast month and expense-tier behavior, including `null` tiers meaning all months. Avoid changing hardcoded historical defaults without checking the product plan.
- File uploads must let the browser set the multipart boundary; do not set `Content-Type` manually for `FormData` requests.
- Run focused validation from `frontend/`: `npx tsc --noEmit` for a non-writing check or `npm run build` for the full TypeScript and Vite build. There is currently no frontend test or lint script.
- Read [CLAUDE.md](../../CLAUDE.md) for the full architecture and [Plan_Desarrollo_Economia_Familiar.md](../../Plan_Desarrollo_Economia_Familiar.md) for product semantics before changing financial workflows.