import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');

test('Tailwind source builds to a standalone offline runtime stylesheet',()=>{
  const result=spawnSync(process.execPath,['scripts/build_tailwind.mjs'],{cwd:root,encoding:'utf8',timeout:5000});
  assert.equal(result.status,0,`build failed: ${result.stderr||result.stdout||result.signal}`);
  const css=fs.readFileSync(path.join(root,'static/styles/tailwind.css'),'utf8');
  assert.match(css,/\.hc-button/);
  assert.match(css,/\.drive-turncard\.alert-far/);
  assert.match(css,/prefers-reduced-motion:\s*reduce/);
  assert.doesNotMatch(css,/@import\s+["']tailwindcss["']/);
  assert.doesNotMatch(css,/@theme\s*\{/);
});
