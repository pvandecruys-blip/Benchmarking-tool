import mammoth from 'mammoth';
import type { ParsedDocument } from '../types';

export async function parseDocx(file: File): Promise<ParsedDocument> {
  const arrayBuffer = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ arrayBuffer });
  const text = result.value ?? '';

  // DOCX has no hard page concept; treat whole document as one page.
  return {
    filename: file.name,
    size_bytes: file.size,
    text,
    pages: [text],
    page_count: 1,
  };
}
