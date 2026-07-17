import { copyFile, mkdir, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputDirectory = resolve(projectRoot, "dist");

await rm(outputDirectory, { force: true, recursive: true });
await mkdir(resolve(outputDirectory, "icons"), { recursive: true });

await Promise.all([
  build({
    bundle: true,
    entryPoints: [resolve(projectRoot, "src/background/index.ts")],
    format: "esm",
    outfile: resolve(outputDirectory, "background.js"),
    platform: "browser",
    sourcemap: true,
    target: "chrome120",
  }),
  build({
    bundle: true,
    entryPoints: [resolve(projectRoot, "src/content/index.ts")],
    format: "iife",
    outfile: resolve(outputDirectory, "content.js"),
    platform: "browser",
    sourcemap: true,
    target: "chrome120",
  }),
  copyFile(resolve(projectRoot, "src/manifest.json"), resolve(outputDirectory, "manifest.json")),
  copyFile(
    resolve(projectRoot, "public/icons/plwc-icon-512.png"),
    resolve(outputDirectory, "icons/plwc-icon-512.png"),
  ),
]);

console.log(`PLwC Chat Bridge extension built at ${outputDirectory}`);
