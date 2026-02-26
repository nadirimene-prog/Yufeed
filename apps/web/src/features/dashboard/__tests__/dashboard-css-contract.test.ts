import { readFileSync } from "node:fs";
import { mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { execSync } from "node:child_process";
import { beforeAll, describe, expect, it } from "vitest";

describe("dashboard css contract", () => {
  let cssOutput = "";

  beforeAll(() => {
    const tmpDir = mkdtempSync(join(tmpdir(), "yufeed-dashboard-css-"));
    const outputFile = join(tmpDir, "bundle.css");

    execSync(
      `npx @tailwindcss/cli -i ./src/app/globals.css -o "${outputFile}" --minify`,
      {
        cwd: process.cwd(),
        stdio: "ignore",
      },
    );

    cssOutput = readFileSync(outputFile, "utf8");
  }, 60_000);

  it("includes required semantic utility classes used by dashboard/workbench", () => {
    const requiredClasses = ["animate-status-pulse", "text-label"];

    for (const className of requiredClasses) {
      expect(cssOutput).toContain(`.${className}`);
    }
  });
});
