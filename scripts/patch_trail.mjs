#!/usr/bin/env node
/** Restore local Trail patches after npm ci.
 *
 * Idempotent by construction, and fail-loud when the installed trail-code no
 * longer matches the anchored source, so a dependency upgrade can never
 * silently drop GDScript indexing. npm runs this with the package root as
 * the working directory; an explicit root path is accepted as the first
 * argument for tests and manual reapplication.
 */
import { copyFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(process.argv[2] ?? process.cwd());
const packageDir = join(root, "node_modules", "@trailhq", "trail-code");
const genericPath = join(packageDir, "dist", "graph", "generic.js");
const queryPath = join(packageDir, "dist", "graph", "queries", "gdscript.scm");
const ROW = '    { name: "gdscript", exts: [".gd"], wasm: "gdscript" }, // local: upstream #299';
const ANCHOR = '{ name: "glsl", exts: [".glsl"], wasm: "glsl" },';

if (!existsSync(genericPath)) {
    console.error(`patch_trail: no trail-code install under ${root}; nothing to patch`);
    process.exit(1);
}
const version = JSON.parse(readFileSync(join(packageDir, "package.json"), "utf8")).version;
const source = readFileSync(genericPath, "utf8");
if (!source.includes('{ name: "gdscript"')) {
    const at = source.indexOf(ANCHOR);
    if (at < 0) {
        console.error(`patch_trail: trail-code ${version} lost the anchored glsl row; update patches/trail before installing`);
        process.exit(1);
    }
    const lineEnd = source.indexOf("\n", at);
    writeFileSync(genericPath, source.slice(0, lineEnd + 1) + ROW + "\n" + source.slice(lineEnd + 1));
    console.log(`patch_trail: added gdscript row to trail-code ${version}`);
} else {
    console.log("patch_trail: gdscript row already present");
}
copyFileSync(join(here, "..", "patches", "trail", "gdscript.scm"), queryPath);
console.log(`patch_trail: installed gdscript.scm into trail-code ${version}`);
