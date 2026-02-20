import React from 'react';
import { RouterProvider } from 'react-router';
import { Toaster } from 'sonner';
import { router } from './routes';
import { EmailsProvider } from './state/emails';

export default function App() {
  return (
    <>
      <EmailsProvider>
        <RouterProvider router={router} />
      </EmailsProvider>
      <Toaster position="bottom-right" richColors />
    </>
  );
}
