import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import { join } from 'node:path';

const root = new URL('../', import.meta.url).pathname;

test('production build is independently installable and emits JS/CSS assets', async () => {
  const html = await readFile(join(root, 'dist/index.html'), 'utf8');
  assert.match(html, /<div id=\"root\"><\/div>/);
  const files = await readdir(join(root, 'dist/assets'));
  assert.ok(files.some(file => file.endsWith('.js')), 'bundled JavaScript is present');
  assert.ok(files.some(file => file.endsWith('.css')), 'bundled styles are present');
});

test('route manifest includes public auth, workspace, upload, floor plan, 3D and admin routes', async () => {
  const manifest = JSON.parse(await readFile(join(root, 'public/manus-routes.json'), 'utf8'));
  const paths = new Set(manifest.routes.map(route => route.path));
  for (const route of ['/', '/login', '/dashboard', '/projects', '/projects/new', '/projects/:id/upload', '/projects/:id/floor-plan', '/projects/:id/3d', '/admin']) assert.ok(paths.has(route), `missing ${route}`);
});

test('README and proposed backend integration guide are included', async () => {
  const readme = await readFile(join(root, 'README.md'), 'utf8');
  const guide = await readFile(join(root, 'docs/backend-integration.md'), 'utf8');
  assert.match(readme, /npm run build/);
  assert.match(guide, /proposed/i);
  assert.match(guide, /not claims that those routes exist/i);
});

test('homepage visual assets are present and non-empty', async () => {
  for (const name of ['hero-architecture.webp', 'floorplan-detail.webp', 'cta-corridor.webp', 'mapora-interior.webp']) {
    const info = await stat(join(root, 'public/images', name));
    assert.ok(info.isFile() && info.size > 10_000, `${name} is present and non-empty`);
  }
});
