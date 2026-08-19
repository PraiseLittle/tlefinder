import fs from "node:fs";
import path from "node:path";

import { expect, it } from "vitest";


const guiRoot = path.resolve(__dirname, "..");
const sourceRoot = path.join(guiRoot, "src");


function filesBelow(directory: string): string[] {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const child = path.join(directory, entry.name);
    return entry.isDirectory() ? filesBelow(child) : [child];
  });
}


it("contains no copied Python search implementation", () => {
  const files = filesBelow(guiRoot).filter(
    (file) => !file.includes(`${path.sep}node_modules${path.sep}`),
  );
  expect(files.filter((file) => file.endsWith(".py"))).toEqual([]);
  const source = filesBelow(sourceRoot)
    .filter((file) => /\.(ts|tsx)$/.test(file))
    .map((file) => fs.readFileSync(file, "utf8"))
    .join("\n");
  expect(source).not.toContain("tlefinder.core");
  expect(source).not.toContain("skyfield");
});


it("reaches search behavior only through the typed HTTP client", () => {
  const appSource = fs.readFileSync(path.join(sourceRoot, "App.tsx"), "utf8");
  const clientSource = fs.readFileSync(path.join(sourceRoot, "api", "client.ts"), "utf8");
  expect(appSource).toContain("api.simpleSearch");
  expect(appSource).toContain("api.advancedSearch");
  expect(clientSource).toContain("fetch(`${BASE_URL}${path}`");
  expect(clientSource).toContain('"/search/simple"');
  expect(clientSource).toContain('"/search/advanced"');
});

