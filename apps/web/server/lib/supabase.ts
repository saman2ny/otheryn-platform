import { createClient } from '@supabase/supabase-js';

const parseSupabaseUrl = (value: string | undefined) => {
  const trimmed = value?.trim();
  if (!trimmed) return null;

  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null;
    return trimmed;
  } catch {
    return null;
  }
};

const rawUrl = process.env.SUPABASE_URL?.trim();
const url = parseSupabaseUrl(rawUrl);
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY?.trim();

export const supabaseConfigError = !rawUrl
  ? 'SUPABASE_URL is missing.'
  : !url
    ? 'SUPABASE_URL must be a valid HTTP(S) URL.'
    : !serviceRoleKey
      ? 'SUPABASE_SERVICE_ROLE_KEY is missing.'
      : null;

export const supabase =
  url && serviceRoleKey
    ? createClient(url, serviceRoleKey, {
        auth: {
          persistSession: false,
          autoRefreshToken: false,
        },
      })
    : null;

export const supabaseConfigured = Boolean(url && serviceRoleKey);

if (supabaseConfigError) {
  console.warn(`Supabase disabled: ${supabaseConfigError}`);
}