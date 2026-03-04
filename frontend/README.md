<img width="3827" height="1851" alt="image" src="https://github.com/user-attachments/assets/2295097c-a30b-436a-8d82-f4d6b54fc699" />
<img width="3839" height="1870" alt="image" src="https://github.com/user-attachments/assets/6a50c729-abfa-44ac-909f-7d0fcb682ae8" />
<img width="3839" height="1864" alt="image" src="https://github.com/user-attachments/assets/4fcdee9b-a918-4eb2-9754-49e6a0a011f4" />
<img width="3839" height="1860" alt="image" src="https://github.com/user-attachments/assets/1a891fe4-4b4e-4c9d-b529-2c9c94c2b8e3" />
<img width="3833" height="1861" alt="image" src="https://github.com/user-attachments/assets/175bce39-7996-4d3f-857e-df6a2d461675" />
<img width="3829" height="1843" alt="image" src="https://github.com/user-attachments/assets/81fced5c-91c8-46c6-a06d-9c531cde46e5" />

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
  
