// Vercel serverless function — LLM proxy.
// Phase 1: stub. Returns canned JSON so the frontend deploy works end-to-end.
// Phase 4: will route to Anthropic / OpenAI / Gemini SDKs using server-held API keys,
// add IP rate-limiting (Vercel KV), and enforce prompt-size caps.

export const config = { runtime: 'nodejs' };

interface LlmRequest {
  provider?: 'anthropic' | 'openai' | 'gemini';
  model?: string;
  system?: string;
  prompt: string;
  json_mode?: boolean;
}

export default async function handler(req: Request): Promise<Response> {
  if (req.method !== 'POST') {
    return Response.json({ error: 'Method not allowed' }, { status: 405 });
  }

  let body: LlmRequest;
  try {
    body = (await req.json()) as LlmRequest;
  } catch {
    return Response.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!body.prompt || typeof body.prompt !== 'string') {
    return Response.json({ error: 'Missing required field: prompt' }, { status: 400 });
  }

  return Response.json({
    stub: true,
    text: '[stub] LLM not wired up yet — Phase 4 will replace this.',
    received: {
      provider: body.provider ?? 'anthropic',
      model: body.model ?? 'claude-sonnet-4-6',
      prompt_chars: body.prompt.length,
      system_chars: body.system?.length ?? 0,
      json_mode: !!body.json_mode,
    },
  });
}
