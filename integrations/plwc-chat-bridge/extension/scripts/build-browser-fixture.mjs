import { copyFile, mkdir, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputDirectory = resolve(projectRoot, ".browser-fixture");

await rm(outputDirectory, { force: true, recursive: true });
await mkdir(resolve(outputDirectory, "icons"), { recursive: true });
await build({
  bundle: true,
  entryPoints: [resolve(projectRoot, "tests/browser/fixture-entry.ts")],
  format: "iife",
  outfile: resolve(outputDirectory, "fixture.js"),
  platform: "browser",
  target: "chrome120",
});
await Promise.all([
  copyFile(resolve(projectRoot, "tests/browser/fixture.html"), resolve(outputDirectory, "index.html")),
  copyFile(
    resolve(projectRoot, "public/icons/plwc-icon-512.png"),
    resolve(outputDirectory, "icons/plwc-icon-512.png"),
  ),
]);

console.log(`Browser fixture built at ${outputDirectory}`);
