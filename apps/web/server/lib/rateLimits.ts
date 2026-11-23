import { createHash } from 'node:crypto';
import type { NextFunction, Request, Response } from 'express';
import { supabase } from './supabase';

type RateLimitPolicy = 'contact' | 'booking' | 'walkthrough';

type RateLimitConfig = {
  max: number;
  windowSeconds: number;
};

type RateLimitSupabase = {
  rpc: (
    fn: string,
    args: Record<string, unknown>,
  ) => Promise<{
    data: unknown;
    error: {
      message?: string;
      code?: string;
      details?: string;
      hint?: string;
    } | null;
  }>;
};

type RateLimitDeps = {
  supabase?: RateLimitSupabase | null;
  salt?: string;
  config?: RateLimitConfig;
};

const positiveInteger = (value: string | undefined, fallback: number) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

const getConfig = (policy: RateLimitPolicy): RateLimitConfig => {
  const isProduction = process.env.NODE_ENV === 'production';
  const windowMs = positiveInteger(process.env.RATE_LIMIT_WINDOW_MS, 15 * 60 * 1000);

  const max =
    policy === 'contact'
      ? positiveInteger(
          process.env.RATE_LIMIT_CONTACT_MAX,
          isProduction ? 10 : 20,
        )
      : policy === 'booking'
        ? positiveInteger(
            process.env.RATE_LIMIT_BOOKING_MAX,
            isProduction ? 5 : 10,
          )
        : positiveInteger(
            process.env.RATE_LIMIT_WALKTHROUGH_MAX,
            isProduction ? 5 : 10,
          );

  return {
    max,
    windowSeconds: Math.max(1, Math.ceil(windowMs / 1000)),
  };
};

const getSalt = () => process.env.RATE_LIMIT_HASH_SALT?.trim() || 'otheryn-rate-limit';

const getClientIp = (req: Request) =>
  req.ip || req.socket.remoteAddress || 'unknown';

export const createRateLimitMiddleware = (
  policy: RateLimitPolicy,
  deps: RateLimitDeps = {},
) => {
  const config = deps.config ?? getConfig(policy);
  const client = deps.supabase === undefined
    ? (supabase as unknown as RateLimitSupabase | null)
    : deps.supabase;
  const salt = deps.salt ?? getSalt();

      return async (req: Request, res: Response, next: NextFunction) => {
        if (!client) {
          return res.status(503).json({
            ok: false,
            error: 'Rate limit service unavailable.',
          });
        }

        const ip = getClientIp(req);
        const hash = createHash('sha256')
          .update(`${salt}:${policy}:${ip}`)
          .digest('hex');
        const bucketKey = `${policy}:${hash}`;

        try {
          const { data, error } = await client.rpc('increment_rate_limit', {
            p_bucket_key: bucketKey,
            p_window_seconds: config.windowSeconds,
            p_max_requests: config.max,
          });

          if (error) {
            console.error('Rate limit RPC failed', {
              policy,
              code: error.code,
              message: error.message,
              details: error.details,
              hint: error.hint,
            });
            return res.status(503).json({
              ok: false,
              error: 'Rate limit service unavailable.',
            });
          }

          const row = (Array.isArray(data) ? data[0] : data) as
            | { allowed?: boolean; retry_after?: number }
            | undefined;

          if (!row || typeof row.allowed !== 'boolean') {
            return res.status(503).json({
              ok: false,
              error: 'Rate limit service unavailable.',
            });
          }

          if (!row.allowed) {
            const retryAfter = Math.max(
              1,
              Math.ceil(Number(row.retry_after) || config.windowSeconds),
            );
            res.setHeader('Retry-After', String(retryAfter));
            return res.status(429).json({
              ok: false,
              error: 'Too many requests. Please try again later.',
            });
          }

          return next();
        } catch (error) {
          console.error('Rate limit RPC threw', {
            policy,
            error: error instanceof Error ? error.message : 'unknown',
          });
          return res.status(503).json({
            ok: false,
            error: 'Rate limit service unavailable.',
          });
        }
      };
};