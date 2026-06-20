import {
  app,
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { logger } from "../../shared/logger";
import {
  buildFeedbackResponse,
  createFeedbackOutput,
} from "./response-builder";
import { FeedbackInputSchema } from "./validator";

export async function feedbackHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  const log = logger.child({
    invocationId: context.invocationId,
    operation: "feedback",
  });

  const body: unknown = await request.json().catch(() => null);
  const parsed = FeedbackInputSchema.safeParse(body);
  if (!parsed.success) {
    log.warn({ issues: parsed.error.issues }, "Invalid feedback input");
    return {
      status: 400,
      jsonBody: { error: "Invalid input", details: parsed.error.issues },
    };
  }

  log.info({ queryId: parsed.data.queryId }, "Processing feedback");

  // No external calls - retry not applicable
  const responsePayload = createFeedbackOutput(parsed.data);
  log.info({ feedbackId: responsePayload.feedbackId }, "Feedback recorded");
  return buildFeedbackResponse(responsePayload);
}

app.http("feedback", {
  methods: ["POST"],
  authLevel: "function",
  handler: feedbackHandler,
});
