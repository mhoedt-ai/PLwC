import { readdir, rm } from "node:fs/promises";
import { dirname, relative, resolve, sep } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputDirectory = resolve(projectRoot, ".test-dist");

async function findTests(directory) {
  let entries;
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error && typeof error === "object" && error.code === "ENOENT") return [];
    throw error;
  }
  const files = await Promise.all(
    entries.map(async (entry) => {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) {
        return findTests(path);
      }
      return entry.name.endsWith(".test.ts") ? [path] : [];
    }),
  );
  return files.flat();
}

await rm(outputDirectory, { force: true, recursive: true });
const tests = (
  await Promise.all([findTests(resolve(projectRoot, "src")), findTests(resolve(projectRoot, "tests"))])
).flat();
const compiledTests = [];

for (const test of tests) {
  const outputName = relative(projectRoot, test)
    .split(sep)
    .join("-")
    .replace(/\.ts$/, ".cjs");
  const outputPath = resolve(outputDirectory, outputName);
  await build({
    bundle: true,
    entryPoints: [test],
    format: "cjs",
    outfile: outputPath,
    platform: "node",
    sourcemap: "inline",
    target: "node24",
  });
  compiledTests.push(outputPath);
}

if (compiledTests.length === 0) {
  throw new Error("No PLwC Chat Bridge extension tests were found.");
}

const result = spawnSync(process.execPath, ["--test", ...compiledTests], {
  cwd: projectRoot,
  stdio: "inherit",
});

process.exit(result.status ?? 1);
