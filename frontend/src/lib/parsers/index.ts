// Document parser dispatch — replaces backend/app/services/document_parser.py
// and pptx_parser.py. Everything here runs in the browser; nothing hits the
// network.

import type { ParsedDocument, ParsedPresentation } from '../types';
import { parsePptx } from './pptx';
import { parsePdf } from './pdf';
import { parseDocx } from './docx';
import { parseText } from './text';

export type SourceExt = 'pdf' | 'docx' | 'md' | 'txt';

function extOf(filename: string): string {
  const idx = filename.lastIndexOf('.');
  return idx === -1 ? '' : filename.slice(idx + 1).toLowerCase();
}

export async function parsePresentation(file: File): Promise<ParsedPresentation> {
  if (extOf(file.name) !== 'pptx') {
    throw new Error(`Presentation must be .pptx (got: ${file.name})`);
  }
  return parsePptx(file);
}

export async function parseSourceDocument(file: File): Promise<ParsedDocument> {
  const ext = extOf(file.name);
  switch (ext) {
    case 'pdf':
      return parsePdf(file);
    case 'docx':
      return parseDocx(file);
    case 'md':
    case 'txt':
      return parseText(file);
    default:
      throw new Error(`Unsupported source document type: .${ext}`);
  }
}

export { parsePptx, parsePdf, parseDocx, parseText };
