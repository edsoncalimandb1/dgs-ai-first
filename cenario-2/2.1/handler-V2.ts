import {
  app,
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { z } from "zod";
import { buildHealthOutput, loadPackageVersion } from "./validator.js";
import { ConfigurationError } from "../../shared/errors";
import { logger } from "../../shared/logger";

export async function healthHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  const log = logger.child({
    invocationId: context.invocationId,
    operation: "health",
  });

  // No external calls - retry not applicable
  try {
    const version: string = await loadPackageVersion();
    const response = buildHealthOutput(version);

    log.info({ method: request.method }, "Health check successful");
    return { status: 200, jsonBody: response };
  } catch (error: unknown) {
    if (error instanceof ConfigurationError || error instanceof z.ZodError) {
      log.error({ err: error }, "Health endpoint configuration failure");
      return {
        status: 500,
        jsonBody: { error: "Service configuration error" },
      };
    }

    throw error;
  }
}

app.http("health", {
  methods: ["GET"],
  authLevel: "anonymous",
  route: "health",
  handler: healthHandler,
});
