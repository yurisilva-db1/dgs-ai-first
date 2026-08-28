import { z } from "zod";
import { ValidationError } from "../../shared/errors.js";

// TODO(revisão T1): 500 é um palpite do dev, não um número validado pelo Product Specialist.
// plan.md/ADR-0002 definem budget de tokens para system+chunks, não um limite para a pergunta em si.
// Confirmar com o Product Specialist antes de tratar este valor como definitivo.
const MAX_QUESTION_LENGTH = 500;

export const queryRequestSchema = z.object({
  question: z
    .string({ required_error: "question é obrigatório" })
    .trim()
    .min(1, "question não pode ser vazio")
    .max(MAX_QUESTION_LENGTH, `question excede o limite de ${MAX_QUESTION_LENGTH} caracteres`),
  conversationId: z.string().min(1).optional(),
});

export type QueryRequest = z.infer<typeof queryRequestSchema>;

/**
 * Valida o corpo da requisição de POST /api/query.
 * Lança ValidationError (mapeada para HTTP 400 no handler) quando o shape não bate.
 */
export function parseQueryRequest(body: unknown): QueryRequest {
  const result = queryRequestSchema.safeParse(body);

  if (!result.success) {
    throw new ValidationError("Corpo da requisição inválido", result.error.issues);
  }

  return result.data;
}
