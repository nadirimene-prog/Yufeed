import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const UI_DIR = path.resolve(process.cwd(), "src/components/ui");
const FILE_EXTENSIONS = new Set([".ts", ".tsx", ".js", ".jsx", ".css"]);
const HEX_RE = /#(?:[0-9a-fA-F]{3,8})\b/g;

async function* walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      yield* walk(fullPath);
      continue;
    }
    if (entry.isFile() && FILE_EXTENSIONS.has(path.extname(entry.name))) {
      yield fullPath;
    }
  }
}

function collectMatches(source) {
  const matches = [];
  const lines = source.split(/\r?\n/);
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i] ?? "";
    const found = line.match(HEX_RE);
    if (!found) continue;
    matches.push({
      line: i + 1,
      lineText: line.trim(),
      values: [...new Set(found)],
    });
  }
  return matches;
}

async function main() {
  const failures = [];

  for await (const filePath of walk(UI_DIR)) {
    const source = await readFile(filePath, "utf8");
    const matches = collectMatches(source);
    if (matches.length > 0) {
      failures.push({ filePath, matches });
    }
  }

  if (failures.length === 0) {
    console.log(
      "UI hex color check passed: no hex colors found in src/components/ui",
    );
    return;
  }

  console.error(
    "UI hex color check failed. Use design tokens/classes instead of hex literals.",
  );
  for (const failure of failures) {
    const relative = path.relative(process.cwd(), failure.filePath);
    console.error(`\n${relative}`);
    for (const match of failure.matches) {
      console.error(
        `  ${match.line}: ${match.values.join(", ")}  ${match.lineText}`,
      );
    }
  }
  process.exitCode = 1;
}

main().catch((error) => {
  console.error("UI hex color check crashed:", error);
  process.exitCode = 1;
});
