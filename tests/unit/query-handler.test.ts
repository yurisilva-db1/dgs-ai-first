import { describe, expect, it } from "vitest";
import type { HttpRequest, InvocationContext } from "@azure/functions";
import { queryHandler } from "../../src/functions/query/handler.js";

function fakeRequest(body: unknown, { malformed = false }: { malformed?: boolean } = {}): HttpRequest {
  return {
    json: async () => {
      if (malformed) {
        throw new SyntaxError("Unexpected token in JSON");
      }
      return body;
    },
  } as unknown as HttpRequest;
}

function fakeContext(): InvocationContext {
  return { invocationId: "test-invocation-id" } as unknown as InvocationContext;
}

describe("queryHandler", () => {
  it("retorna 501 quando a validação passa (pipeline ainda não implementado)", async () => {
    const response = await queryHandler(
      fakeRequest({ question: "Qual o prazo de devolução?" }),
      fakeContext(),
    );

    expect(response.status).toBe(501);
    expect((response.jsonBody as { error: string }).error).toBe("not_implemented");
  });

  it("retorna 400 quando question está ausente", async () => {
    const response = await queryHandler(fakeRequest({}), fakeContext());

    expect(response.status).toBe(400);
    expect((response.jsonBody as { error: string }).error).toBe("invalid_request");
  });

  it("retorna 400 com os issues do Zod quando question está ausente", async () => {
    const response = await queryHandler(fakeRequest({}), fakeContext());
    const body = response.jsonBody as { issues: Array<{ path: string[] }> };

    expect(body.issues[0]?.path).toEqual(["question"]);
  });

  it("retorna 400 quando o corpo não é JSON válido", async () => {
    const response = await queryHandler(fakeRequest(undefined, { malformed: true }), fakeContext());

    expect(response.status).toBe(400);
    expect((response.jsonBody as { error: string }).error).toBe("invalid_request");
  });

  it("inclui o requestId (invocationId) na resposta", async () => {
    const response = await queryHandler(
      fakeRequest({ question: "Qual o SLA?" }),
      fakeContext(),
    );

    expect((response.jsonBody as { requestId: string }).requestId).toBe("test-invocation-id");
  });
});
