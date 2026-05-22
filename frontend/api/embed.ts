// Vercel serverless function — embeddings proxy.
// Phase 1: stub. Returns deterministic hashed pseudo-vectors so downstream code can
// be built and tested without an API key. Phase 4 will swap in OpenAI's
// text-embedding-3-small (1536 dims) and add rate limiting.

export const config = { runtime: 'nodejs' };

const STUB_DIM = 16;

interface EmbedRequest {
  texts: string[];
  model?: string;
}

function hashStringToVector(s: string, dim: number): number[] {
  const v = new Array<number>(dim).fill(0);
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    v[i % dim] = (v[i % dim] + c * (1 + (i % 7))) % 9973;
  }
  const norm = Math.sqrt(v.reduce((a, b) => a + b * b, 0)) || 1;
  return v.map((x) => x / norm);
}

export default async function handler(req: Request): Promise<Response> {
  if (req.method !== 'POST') {
    return Response.json({ error: 'Method not allowed' }, { status: 405 });
  }

  let body: EmbedRequest;
  try {
    body = (await req.json()) as EmbedRequest;
  } catch {
    return Response.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!Array.isArray(body.texts) || body.texts.some((t) => typeof t !== 'string')) {
    return Response.json({ error: 'texts must be an array of strings' }, { status: 400 });
  }
  if (body.texts.length > 96) {
    return Response.json({ error: 'max 96 texts per call' }, { status: 400 });
  }

  return Response.json({
    stub: true,
    model: body.model ?? 'stub-hash-16',
    dim: STUB_DIM,
    vectors: body.texts.map((t) => hashStringToVector(t, STUB_DIM)),
  });
}
