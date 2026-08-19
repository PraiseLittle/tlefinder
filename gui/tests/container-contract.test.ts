import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";


const guiRoot = path.resolve(import.meta.dirname, "..");
const repositoryRoot = path.resolve(guiRoot, "..");


function read(relativePath: string): string {
  return fs.readFileSync(path.join(repositoryRoot, relativePath), "utf8");
}


describe("production container contract", () => {
  it("keeps the browser-visible API base relative", () => {
    const client = read("gui/src/api/client.ts");

    expect(client).toContain('?? "/api/v1"');
    expect(client).not.toContain("http://api:2626");
  });

  it("builds and serves the GUI from separate locked stages", () => {
    const dockerfile = read("gui/Dockerfile");

    expect(dockerfile.match(/^FROM /gm)).toHaveLength(2);
    expect(dockerfile).toContain("npm ci");
    expect(dockerfile).toContain("npm test");
    expect(dockerfile).toContain("npm run typecheck");
    expect(dockerfile).toContain("npm run build");
    expect(dockerfile).toContain("COPY --from=build /build/gui/dist");
    expect(dockerfile).toContain("USER nginx");
  });

  it("preserves API paths and provides a safe SPA fallback", () => {
    const nginx = read("gui/nginx.conf");

    expect(nginx).toContain("location /api/");
    expect(nginx).toContain("proxy_pass http://api:2626;");
    expect(nginx).not.toContain("proxy_pass http://api:2626/;");
    expect(nginx).toContain("proxy_intercept_errors off;");
    expect(nginx).toContain("try_files $uri $uri/ /index.html;");
    expect(nginx).toContain("location /assets/");
    expect(nginx).toContain("try_files $uri =404;");
  });
});
