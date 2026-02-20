
  # AI Email Manager UX

  This is a code bundle for AI Email Manager UX. The original project is available at https://www.figma.com/design/mFpPSMzQZjv9lAtgs2fdYp/AI-Email-Manager-UX.

  ## Running the code

  Run `npm i` to install the dependencies.

  Run `npm run dev` to start the development server.

  ## Demo / Requirements Notes

  - Responsive design is implemented for at least two screen sizes:
    - Below 768px: single-pane navigation (list OR detail).
    - 768px and up: three-pane layout (sidebar + list + reading pane).
  - Accessibility (WCAG-oriented):
    - Keyboard-accessible email rows and visible focus rings.
    - Icon-only buttons include accessible names (`aria-label`).
    - Compose modal uses dialog semantics and supports Escape-to-close.
    - Respects `prefers-reduced-motion`.
    - Images include `alt` text where applicable.
  - Backend/data is mocked so the frontend can be demonstrated end-to-end:
    - Email data is seeded from mock data.
    - “Send email”, “AI actions”, and “Suggested actions” use a local mock service (no real API).
  