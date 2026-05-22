// Vercel serverless function — embeddings proxy.
// Calls OpenAI's text-embedding-3-small (1536 dims, cheap: $0.02 per 1M tokens).
// Anthropic does not offer an embeddings endpoint — that's why this one is
// OpenAI-only even though /api/llm uses Anthropic.

import OpenAI from 'openai';

export const config = { runtime: 'nodejs' };

const MAX_TEXTS_PER_CALL = 96;
const MAX_TOTAL_CHARS = 200_000;
const DEFAULT_MODEL = 'text-embedding-3-small';

interface EmbedRequest {
  texts: string[];
  model?: string;
}

function err(status: number, message: string): Response {
  return Response.json({ error: message }, { status });
}

export default async function handler(req: Request): Promise<Response> {
  if (req.method !== 'POST') return err(405, 'Method not allowed');

  let body: EmbedRequest;
  try {
    body = (await req.json()) as EmbedRequest;
  } catch {
    return err(400, 'Invalid JSON body');
  }

  if (!Array.isArray(body.texts) || body.texts.some((t) => typeof t !== 'string')) {
    return err(400, 'texts must be an array of strings');
  }
  if (body.texts.length === 0) return err(400, 'texts is empty');
  if (body.texts.length > MAX_TEXTS_PER_CALL) {
    return err(413, `max ${MAX_TEXTS_PER_CALL} texts per call`);
  }
  const totalChars = body.texts.reduce((a, t) => a + t.length, 0);
  if (totalChars > MAX_TOTAL_CHARS) {
    return err(413, `combined texts exceed ${MAX_TOTAL_CHARS} chars`);
  }

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    return err(503, 'Server is not configured: OPENAI_API_KEY missing');
  }

  const client = new OpenAI({ apiKey });

  try {
    const resp = await client.embeddings.create({
      model: body.model ?? DEFAULT_MODEL,
      input: body.texts,
    });

    const vectors = resp.data
      .sort((a, b) => a.index - b.index)
      .map((d) => d.embedding);

    return Response.json({
      model: resp.model,
      dim: vectors[0]?.length ?? 0,
      vectors,
      usage: { prompt_tokens: resp.usage.prompt_tokens, total_tokens: resp.usage.total_tokens },
    });
  } catch (e) {
    const status =
      typeof e === 'object' && e !== null && 'status' in e
        ? (e as { status: number }).status
        : 500;
    const message = e instanceof Error ? e.message : 'Unknown embeddings error';
    return Response.json({ error: message }, { status });
  }
}
