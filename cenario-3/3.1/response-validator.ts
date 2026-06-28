import pino from "pino";
import { z } from "zod";

const logger = pino({ name: "response-validator" });

export const AssistantResponseSchema = z
  .object({
    answer: z.string().min(1),
    source_document: z.string().min(1),
    confidence_score: z.number().min(0).max(1),
  })
  .strict();

export type AssistantResponse = z.infer<typeof AssistantResponseSchema>;

const VALID_SOURCE_DOCUMENTS: Set<string> = new Set<string>([
  "POL-001",
  "PROC-042",
  "PROC-042-v2",
  "SLA-2024",
  "FAQ-Atendimento",
]);

export interface ValidationResult {
  valid: boolean;
  response: AssistantResponse;
  rejectionReason?: string;
  requiresHumanReview?: boolean;
}

export const FALLBACK_RESPONSE: AssistantResponse = Object.freeze({
  answer:
    "Não foi possível processar esta resposta com segurança. Por favor, escale para o supervisor.",
  source_document: "N/A",
  confidence_score: 0,
});

const EMAIL_PATTERN = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi;
const SENSITIVE_KEY_PATTERN =
  /^(email|e[-_]?mail|nome|atendente|attendant.*|.*[Ee]mail.*|.*[Nn]ome.*)$/i;

function sanitizeForLog(value: unknown): unknown {
  if (typeof value === "string") {
    return value.replace(EMAIL_PATTERN, "[REDACTED_EMAIL]");
  }

  if (Array.isArray(value)) {
    return value.map((item: unknown) => sanitizeForLog(item));
  }

  if (value !== null && typeof value === "object") {
    const source = value as Record<string, unknown>;
    const sanitized: Record<string, unknown> = {};

    for (const [key, nestedValue] of Object.entries(source)) {
      if (SENSITIVE_KEY_PATTERN.test(key)) {
        sanitized[key] = "[REDACTED]";
        continue;
      }

      sanitized[key] = sanitizeForLog(nestedValue);
    }

    return sanitized;
  }

  return value;
}

function detectDangerousCargoReturnClaim(answer: string): boolean {
  const normalized = answer
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

  const cargoPattern = /\b(cargas? perigosas?|produtos? perigosos?)\b/;
  const returnPattern =
    /\b(devolucao|devolver|devolvida|devolvido|retorno|retornar)\b/;
  const negativePattern =
    /\b(nao\s+pode|nao\s+e\s+possivel|nao\s+sera\s+possivel|nao\s+(e\s+)?permitid[ao]|nao\s+ser[aá]\s+devolvid[ao]|impossivel|vedado|proibido)\b/;

  const mentionsDangerousCargo = cargoPattern.test(normalized);
  const mentionsReturn = returnPattern.test(normalized);
  const hasExplicitNegative = negativePattern.test(normalized);

  return mentionsDangerousCargo && mentionsReturn && !hasExplicitNegative;
}

export function validateResponse(rawResponse: unknown): ValidationResult {
  const parseResult = AssistantResponseSchema.safeParse(rawResponse);

  if (!parseResult.success) {
    logger.warn(
      {
        reason: parseResult.error.issues,
        rawResponse: sanitizeForLog(rawResponse),
      },
      "Response rejected: schema validation failed",
    );

    return {
      valid: false,
      response: FALLBACK_RESPONSE,
      rejectionReason: "schema_validation_failed",
    };
  }

  const response = parseResult.data;

  if (!VALID_SOURCE_DOCUMENTS.has(response.source_document)) {
    logger.warn(
      {
        source_document: response.source_document,
      },
      "Response rejected: invalid source document",
    );

    return {
      valid: false,
      response: FALLBACK_RESPONSE,
      rejectionReason: "invalid_source_document",
    };
  }

  if (detectDangerousCargoReturnClaim(response.answer)) {
    logger.warn(
      {
        source_document: response.source_document,
      },
      "Response rejected: risky dangerous cargo return claim",
    );

    return {
      valid: false,
      response: FALLBACK_RESPONSE,
      rejectionReason: "dangerous_cargo_return_claim",
      requiresHumanReview: true,
    };
  }

  return {
    valid: true,
    response,
  };
}
