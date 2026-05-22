import * as pdfjsLib from 'pdfjs-dist';
// Vite-native way to ship the worker as a static asset alongside our bundle.
// The `?url` suffix returns the resolved URL to the worker file at build time.
import pdfjsWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import type { ParsedDocument } from '../types';

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl;

export async function parsePdf(file: File): Promise<ParsedDocument> {
  const arrayBuffer = await file.arrayBuffer();
  const doc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

  const pages: string[] = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const page = await doc.getPage(i);
    const content = await page.getTextContent();
    // content.items is (TextItem | TextMarkedContent)[]; only TextItem has .str.
    const lines = content.items
      .map((it) => ('str' in it ? it.str : ''))
      .filter((s) => s.length > 0);
    pages.push(lines.join(' '));
    page.cleanup();
  }
  await doc.destroy();

  return {
    filename: file.name,
    size_bytes: file.size,
    text: pages.join('\n\n'),
    pages,
    page_count: pages.length,
  };
}
