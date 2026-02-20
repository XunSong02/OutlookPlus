import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router';
import { MailLayout } from './components/MailLayout';
import { EmailDetailWrapper, EmailDetailPlaceholder } from './components/EmailDetailWrapper';

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/inbox" replace />,
  },
  {
    path: "/:folder",
    element: <MailLayout />,
    children: [
      {
        index: true,
        element: <EmailDetailPlaceholder />,
      },
      {
        path: ":emailId",
        element: <EmailDetailWrapper />,
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/inbox" replace />,
  },
]);
