import { HttpResponseInit } from "@azure/functions";
import { randomUUID } from "node:crypto";
import {
  FeedbackOutput,
  FeedbackOutputSchema,
  FeedbackInput,
} from "./validator";

export function createFeedbackOutput(_: FeedbackInput): FeedbackOutput {
  return FeedbackOutputSchema.parse({
    feedbackId: randomUUID(),
    status: "recorded",
    recordedAt: new Date().toISOString(),
  });
}

export function buildFeedbackResponse(data: FeedbackOutput): HttpResponseInit {
  const parsed = FeedbackOutputSchema.safeParse(data);

  if (!parsed.success) {
    return {
      status: 500,
      jsonBody: { error: "Response validation failed" },
    };
  }

  return {
    status: 201,
    jsonBody: parsed.data,
  };
}
