import pino from "pino";

/** Logger estruturado (JSON) — nunca usar console.log diretamente no código de produção. */
export const logger = pino({
  level: process.env.LOG_LEVEL ?? "info",
});
