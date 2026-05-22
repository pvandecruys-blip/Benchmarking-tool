// Vercel serverless function — LLM proxy.
// Holds the Anthropic API key server-side so the browser never sees it.
//
// Limits enforced here are the only thing standing between the public demo
// and a drained API key — they are intentionally conservative. Set a hard
// $/day spend cap in https://console.anthropic.com/settings/limits as well.
//
// Future work: multi-provider switch (OpenAI/Gemini), Vercel KV rate limiting.

import Anthropic from '@anthropic-ai/sdk';

export const config = { runtime: 'nodejs' };

const MAX_PROMPT_CHARS = 100_000;
const MAX_SYSTEM_CHARS = 20_000;
const DEFAULT_MODEL = 'claude-sonnet-4-6';
const DEFAULT_MAX_TOKENS = 4096;
const DEFAULT_TEMPERATURE = 0.2;

interface LlmRequest {
  provider?: 'anthropic';
  model?: string;
  system?: string;
  prompt: string;
  json_mode?: boolean;
  max_tokens?: number;
  temperature?: number;
}

function err(status: number, message: string): Response {
  return Response.json({ error: message }, { status });
}

export default async function handler(req: Request): Promise<Response> {
  if (req.method !== 'POST') return err(405, 'Method not allowed');

  let body: LlmRequest;
  try {
    body = (await req.json()) as LlmRequest;
  } catch {
    return err(400, 'Invalid JSON body');
  }

  if (!body.prompt || typeof body.prompt !== 'string') {
    return err(400, 'Missing required field: prompt');
  }
  if (body.prompt.length > MAX_PROMPT_CHARS) {
    return err(413, `prompt exceeds ${MAX_PROMPT_CHARS} chars`);
  }
  if (body.system && body.system.length > MAX_SYSTEM_CHARS) {
    return err(413, `system exceeds ${MAX_SYSTEM_CHARS} chars`);
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return err(503, 'Server is not configured: ANTHROPIC_API_KEY missing');
  }

  const client = new Anthropic({ apiKey });

  try {
    const msg = await client.messages.create({
      model: body.model ?? DEFAULT_MODEL,
      max_tokens: Math.min(body.max_tokens ?? DEFAULT_MAX_TOKENS, 8192),
      temperature: body.temperature ?? DEFAULT_TEMPERATURE,
      system: body.system,
      messages: [{ role: 'user', content: body.prompt }],
    });

    const text = msg.content
      .filter((b) => b.type === 'text')
      .map((b) => (b as { type: 'text'; text: string }).text)
      .join('');

    return Response.json({
      text,
      model: msg.model,
      stop_reason: msg.stop_reason,
      usage: {
        input_tokens: msg.usage.input_tokens,
        output_tokens: msg.usage.output_tokens,
      },
    });
  } catch (e) {
    const status =
      typeof e === 'object' && e !== null && 'status' in e
        ? (e as { status: number }).status
        : 500;
    const message = e instanceof Error ? e.message : 'Unknown LLM error';
    return Response.json({ error: message }, { status });
  }
}
