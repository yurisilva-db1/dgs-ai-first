import { describe, expect, it } from "vitest";
import { parseQueryRequest } from "../../src/functions/query/validator.js";
import { ValidationError } from "../../src/shared/errors.js";

describe("parseQueryRequest", () => {
  it("aceita um payload válido", () => {
    const result = parseQueryRequest({ question: "Qual o prazo de devolução?" });
    expect(result.question).toBe("Qual o prazo de devolução?");
  });

  it("aceita conversationId opcional", () => {
    const result = parseQueryRequest({ question: "Qual o SLA?", conversationId: "conv-123" });
    expect(result.conversationId).toBe("conv-123");
  });

  it("rejeita payload sem question", () => {
    expect(() => parseQueryRequest({})).toThrow(ValidationError);
  });

  it("inclui o path do campo ausente nos issues", () => {
    try {
      parseQueryRequest({});
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(ValidationError);
      expect((err as ValidationError).issues[0]?.path).toEqual(["question"]);
    }
  });

  it("rejeita question vazia", () => {
    expect(() => parseQueryRequest({ question: "" })).toThrow(ValidationError);
  });

  it("rejeita question apenas com espaços", () => {
    expect(() => parseQueryRequest({ question: "   " })).toThrow(ValidationError);
  });

  it("rejeita question acima do limite de 500 caracteres", () => {
    const question = "a".repeat(501);
    expect(() => parseQueryRequest({ question })).toThrow(ValidationError);
  });

  it("aceita question exatamente no limite de 500 caracteres", () => {
    const question = "a".repeat(500);
    expect(() => parseQueryRequest({ question })).not.toThrow();
  });

  it("rejeita body que não é um objeto", () => {
    expect(() => parseQueryRequest("string qualquer")).toThrow(ValidationError);
    expect(() => parseQueryRequest(null)).toThrow(ValidationError);
  });
});
