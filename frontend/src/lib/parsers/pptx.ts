import JSZip from 'jszip';
import type { ParsedPresentation, SlideRecord, SlideShape } from '../types';

// PPTX = OOXML in a ZIP. Slide files live at ppt/slides/slide{N}.xml.
// Slide order comes from ppt/presentation.xml + its rels (a slide may be re-ordered
// such that slide5.xml is first in the deck). We resolve order via:
//   presentation.xml  : <p:sldIdLst><p:sldId r:id="rIdN"/>...</p:sldIdLst>
//   _rels/presentation.xml.rels : <Relationship Id="rIdN" Target="slides/slide{X}.xml"/>

interface SlideOrderEntry {
  rId: string;
  target: string; // e.g. "slides/slide3.xml"
  slideId: string;
}

function getElementsByTagNS(root: Element | Document, localName: string): Element[] {
  // PPTX uses namespace prefixes a: / p: / r:. We accept any prefix for the
  // given local name so DOMParser quirks across browsers don't bite us.
  const out: Element[] = [];
  const all = root.getElementsByTagName('*');
  for (let i = 0; i < all.length; i++) {
    const el = all[i];
    const ln = el.localName ?? el.tagName.split(':').pop();
    if (ln === localName) out.push(el);
  }
  return out;
}

function textContent(el: Element): string {
  return getElementsByTagNS(el, 't')
    .map((t) => t.textContent ?? '')
    .join('');
}

function parseTable(graphicFrame: Element): string[][] | null {
  const tbls = getElementsByTagNS(graphicFrame, 'tbl');
  if (tbls.length === 0) return null;
  const tbl = tbls[0];
  const rows = getElementsByTagNS(tbl, 'tr');
  return rows.map((row) =>
    getElementsByTagNS(row, 'tc').map((cell) => textContent(cell).trim()),
  );
}

function parseShape(spEl: Element, shape_id: number): SlideShape {
  // Name from <p:cNvPr name="...">
  const cNvPrs = getElementsByTagNS(spEl, 'cNvPr');
  const shape_name = cNvPrs[0]?.getAttribute('name') ?? `Shape ${shape_id}`;

  // All paragraphs inside this shape, joined with newlines.
  const paragraphs = getElementsByTagNS(spEl, 'p').map((p) => textContent(p));
  const text = paragraphs.filter((s) => s.length > 0).join('\n');

  return { shape_id, shape_name, text, table: null };
}

function parseGraphicFrame(gfEl: Element, shape_id: number): SlideShape {
  const cNvPrs = getElementsByTagNS(gfEl, 'cNvPr');
  const shape_name = cNvPrs[0]?.getAttribute('name') ?? `Table ${shape_id}`;
  const table = parseTable(gfEl);
  const text = table ? table.map((row) => row.join('\t')).join('\n') : '';
  return { shape_id, shape_name, text, table };
}

function detectTitleFromShapes(
  spEls: Element[],
  shapes: SlideShape[],
): string {
  // PPTX marks the title shape with <p:ph type="title"/> or "ctrTitle".
  for (let i = 0; i < spEls.length; i++) {
    const phs = getElementsByTagNS(spEls[i], 'ph');
    for (const ph of phs) {
      const t = ph.getAttribute('type');
      if (t === 'title' || t === 'ctrTitle') {
        const firstLine = shapes[i].text.split('\n')[0]?.trim() ?? '';
        if (firstLine) return firstLine;
      }
    }
  }
  // Fallback: first non-empty line of the first non-empty shape.
  for (const s of shapes) {
    const firstLine = s.text.split('\n')[0]?.trim();
    if (firstLine) return firstLine;
  }
  return '(untitled slide)';
}

async function parseSlideOrder(zip: JSZip): Promise<SlideOrderEntry[]> {
  const presFile = zip.file('ppt/presentation.xml');
  const relsFile = zip.file('ppt/_rels/presentation.xml.rels');
  if (!presFile || !relsFile) {
    throw new Error('Invalid PPTX: missing presentation.xml or its rels');
  }
  const presXml = await presFile.async('string');
  const relsXml = await relsFile.async('string');
  const parser = new DOMParser();
  const presDoc = parser.parseFromString(presXml, 'application/xml');
  const relsDoc = parser.parseFromString(relsXml, 'application/xml');

  // Build rId -> target map from rels.
  const relMap = new Map<string, string>();
  const relEls = relsDoc.getElementsByTagName('Relationship');
  for (let i = 0; i < relEls.length; i++) {
    const id = relEls[i].getAttribute('Id');
    const target = relEls[i].getAttribute('Target');
    if (id && target) relMap.set(id, target);
  }

  // Walk <p:sldIdLst><p:sldId id="..." r:id="..."/>
  const sldIds = getElementsByTagNS(presDoc, 'sldId');
  const order: SlideOrderEntry[] = [];
  for (const el of sldIds) {
    const slideId = el.getAttribute('id') ?? '';
    // r:id may appear as r:id or just id depending on parser; prefer the one
    // that matches an entry in relMap.
    const attrs = el.attributes;
    let rId = '';
    for (let i = 0; i < attrs.length; i++) {
      const a = attrs[i];
      if (a.localName === 'id' && (a.prefix === 'r' || a.namespaceURI?.includes('relationships'))) {
        rId = a.value;
        break;
      }
    }
    if (!rId) {
      // Fallback: try every attribute looking for one whose value is in relMap.
      for (let i = 0; i < attrs.length; i++) {
        if (relMap.has(attrs[i].value)) {
          rId = attrs[i].value;
          break;
        }
      }
    }
    const target = relMap.get(rId);
    if (!target) continue;
    // target is like "slides/slide3.xml" — make absolute zip path.
    const absTarget = target.startsWith('/') ? target.slice(1) : `ppt/${target}`;
    order.push({ rId, target: absTarget, slideId });
  }

  // If presentation.xml didn't help (rare), fallback: sort slide*.xml by number.
  if (order.length === 0) {
    const fallback: SlideOrderEntry[] = [];
    zip.folder('ppt/slides')?.forEach((relativePath, file) => {
      const m = /^slide(\d+)\.xml$/.exec(relativePath);
      if (m && !file.dir) {
        fallback.push({
          rId: '',
          target: `ppt/slides/${relativePath}`,
          slideId: m[1],
        });
      }
    });
    fallback.sort((a, b) => parseInt(a.slideId) - parseInt(b.slideId));
    return fallback;
  }

  return order;
}

async function parseSlide(
  zip: JSZip,
  slideTarget: string,
  slide_number: number,
  slide_id: string,
): Promise<SlideRecord> {
  const file = zip.file(slideTarget);
  if (!file) {
    throw new Error(`Slide file not found: ${slideTarget}`);
  }
  const xml = await file.async('string');
  const doc = new DOMParser().parseFromString(xml, 'application/xml');

  // Collect shapes (<p:sp>) and graphic frames (<p:graphicFrame> for tables).
  const spEls = getElementsByTagNS(doc, 'sp');
  const gfEls = getElementsByTagNS(doc, 'graphicFrame');

  const shapes: SlideShape[] = [];
  let next_id = 1;
  for (const sp of spEls) shapes.push(parseShape(sp, next_id++));
  for (const gf of gfEls) shapes.push(parseGraphicFrame(gf, next_id++));

  const slide_title = detectTitleFromShapes(spEls, shapes.slice(0, spEls.length));
  const all_text = shapes
    .map((s) => s.text)
    .filter((t) => t.length > 0)
    .join('\n\n');

  return {
    slide_number,
    slide_title,
    slide_id,
    shapes,
    all_text,
    excluded: false,
  };
}

export async function parsePptx(file: File): Promise<ParsedPresentation> {
  const buf = await file.arrayBuffer();
  const zip = await JSZip.loadAsync(buf);

  const order = await parseSlideOrder(zip);
  const slides: SlideRecord[] = [];
  for (let i = 0; i < order.length; i++) {
    slides.push(await parseSlide(zip, order[i].target, i + 1, order[i].slideId));
  }

  return { filename: file.name, size_bytes: file.size, slides };
}
