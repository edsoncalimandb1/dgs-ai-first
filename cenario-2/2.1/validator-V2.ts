import { z } from "zod";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { ConfigurationError } from "../../shared/errors";

export const HealthOutputSchema = z.object({
  status: z.literal("ok"),
  timestamp: z.string().datetime({ offset: true }),
  version: z.string().min(1),
});

export type HealthOutput = z.infer<typeof HealthOutputSchema>;

type PackageJson = {
  version?: unknown;
};

export async function loadPackageVersion(): Promise<string> {
  const packageJsonPath: string = resolve(process.cwd(), "package.json");
  const packageJsonRaw: string = await readFile(packageJsonPath, "utf-8");
  const packageJson: PackageJson = JSON.parse(packageJsonRaw) as PackageJson;

  if (
    typeof packageJson.version !== "string" ||
    packageJson.version.length === 0
  ) {
    throw new ConfigurationError(
      "Package version could not be loaded from package.json",
    );
  }

  return packageJson.version;
}

export function buildHealthOutput(version: string): HealthOutput {
  return HealthOutputSchema.parse({
    status: "ok",
    timestamp: new Date().toISOString(),
    version,
  });
}
