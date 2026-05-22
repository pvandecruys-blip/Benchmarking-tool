import type { ParsedDocument } from '../types';

export async function parseText(file: File): Promise<ParsedDocument> {
  const text = await file.text();
  return {
    filename: file.name,
    size_bytes: file.size,
    text,
    pages: [text],
    page_count: 1,
  };
}
