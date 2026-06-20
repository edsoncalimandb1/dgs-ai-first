import {
  app,
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { readFileSync } from "node:fs";
import { z } from "zod";
import { logger } from "../../shared/logger";

const PackageVersionSchema = z.object({
  version: z.string().min(1),
});

const HealthResponseSchema = z.object({
  status: z.literal("ok"),
  timestamp: z.string().datetime(),
  version: z.string().min(1),
});

type HealthResponse = z.infer<typeof HealthResponseSchema>;

function loadPackageVersion(): string | null {
  const packageJsonUrl: URL = new URL("../../../package.json", import.meta.url);
  const packageJsonContent: string = readFileSync(packageJsonUrl, "utf-8");
  const packageJsonUnknown: unknown = JSON.parse(packageJsonContent) as unknown;
  const parsedPackage = PackageVersionSchema.safeParse(packageJsonUnknown);

  if (!parsedPackage.success) {
    return null;
  }

  return parsedPackage.data.version;
}

const APP_VERSION: string | null = loadPackageVersion();

export async function healthHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  const log = logger.child({
    invocationId: context.invocationId,
    operation: "health",
  });

  log.info(
    { method: request.method, url: request.url },
    "Health check requested",
  );

  if (APP_VERSION === null) {
    log.error("Package version could not be loaded from package.json");
    return {
      status: 500,
      jsonBody: { error: "Application version unavailable" },
    };
  }

  const responseCandidate: HealthResponse = {
    status: "ok",
    timestamp: new Date().toISOString(),
    version: APP_VERSION,
  };

  const parsedResponse = HealthResponseSchema.safeParse(responseCandidate);

  if (!parsedResponse.success) {
    log.error(
      { issues: parsedResponse.error.issues },
      "Health response schema validation failed",
    );

    return {
      status: 500,
      jsonBody: { error: "Health response validation failed" },
    };
  }

  log.info({ version: APP_VERSION }, "Health check completed successfully");

  return {
    status: 200,
    jsonBody: parsedResponse.data,
  };
}

app.http("health", {
  methods: ["GET"],
  authLevel: "anonymous",
  handler: healthHandler,
});
