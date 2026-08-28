import type { ZodIssue } from "zod";

/** Erro de validação de input do usuário — deve virar HTTP 400, nunca 500. */
export class ValidationError extends Error {
  readonly issues: ZodIssue[];

  constructor(message: string, issues: ZodIssue[]) {
    super(message);
    this.name = "ValidationError";
    this.issues = issues;
  }
}
