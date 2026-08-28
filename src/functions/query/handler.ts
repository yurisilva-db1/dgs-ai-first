import { app, type HttpRequest, type HttpResponseInit, type InvocationContext } from "@azure/functions";
import { parseQueryRequest } from "./validator.js";
import { ValidationError } from "../../shared/errors.js";
import { logger } from "../../shared/logger.js";

/**
 * POST /api/query — recebe a pergunta do atendente e valida o input.
 *
 * Escopo desta implementação (task T1 de specs/query-endpoint/tasks.md): apenas parsing + validação.
 * O restante do pipeline (embedding, busca, prompt, geração — tasks T3–T8) ainda não existe, então uma
 * requisição válida retorna 501 em vez de travar o cliente com um 500/erro genérico.
 */
export async function queryHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  const requestId = context.invocationId;

  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    logger.warn({ requestId }, "query.malformed_json");
    return {
      status: 400,
      jsonBody: {
        error: "invalid_request",
        message: "Corpo da requisição não é um JSON válido",
        requestId,
      },
    };
  }

  try {
    const query = parseQueryRequest(rawBody);
    logger.info({ requestId, questionLength: query.question.length }, "query.validated");

    return {
      status: 501,
      jsonBody: {
        error: "not_implemented",
        message: "Validação concluída. Pipeline de busca e geração ainda não implementado.",
        requestId,
      },
    };
  } catch (err) {
    if (err instanceof ValidationError) {
      logger.warn({ requestId, issues: err.issues }, "query.validation_failed");
      return {
        status: 400,
        jsonBody: {
          error: "invalid_request",
          message: err.message,
          issues: err.issues.map((issue) => ({ path: issue.path, message: issue.message })),
          requestId,
        },
      };
    }

    logger.error({ requestId, err }, "query.unhandled_error");
    return {
      status: 500,
      jsonBody: { error: "internal_error", requestId },
    };
  }
}

app.http("query", {
  methods: ["POST"],
  authLevel: "function",
  route: "query",
  handler: queryHandler,
});
