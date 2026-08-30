import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const read = (p) => fs.readFileSync(path.join(root, p), 'utf8');
const exists = (p) => fs.existsSync(path.join(root, p));

test('README exposes polished visual download and verification surfaces', () => {
  const readme = read('README.md');
  assert.match(readme, /docs\/images\/readme-hero\.svg/);
  assert.match(readme, /docs\/images\/download-latest\.svg/);
  assert.match(readme, /releases\/latest\/download\/FH6_Scenic_Navigator_Windows_x64\.exe/);
  assert.match(readme, /<!-- RELEASE_STATUS_START -->/);
  assert.match(readme, /VirusTotal/i);
  assert.match(readme, /SHA-256/i);
  assert.match(readme, /CI/i);
});

test('README visual SVG assets are committed as text assets', () => {
  for (const file of [
    'docs/images/readme-hero.svg',
    'docs/images/download-latest.svg',
    'docs/images/feature-strip.svg',
    'docs/images/security-strip.svg',
  ]) {
    assert.equal(exists(file), true, `${file} should exist`);
    const svg = read(file);
    assert.match(svg, /^<svg[\s>]/);
  }
});

test('CI workflow keeps Python, JavaScript, Go and repository hygiene checks separate', () => {
  const ci = read('.github/workflows/ci.yml');
  assert.match(ci, /python-tests:/);
  assert.match(ci, /javascript-tests:/);
  assert.match(ci, /go-tests:/);
  assert.match(ci, /repository-hygiene:/);
  assert.match(ci, /go test -race \.\/\.\.\./);
  assert.match(ci, /\.nav/);
  assert.match(ci, /\.owt/);
  assert.match(ci, /\.oww/);
  assert.match(ci, /\.owbs/);
});

test('release security workflow publishes stable download, checksum and VirusTotal report', () => {
  const workflow = read('.github/workflows/release-security.yml');
  assert.match(workflow, /types:\s*\[published\]/);
  assert.match(workflow, /FH6_Scenic_Navigator_Windows_x64\.exe/);
  assert.match(workflow, /sha256sum/);
  assert.match(workflow, /VT_API_KEY/);
  assert.match(workflow, /virustotal\.com\/api\/v3\/files/);
  assert.match(workflow, /RELEASE_STATUS_START/);
  assert.match(workflow, /gh release upload/);
});

test('security and release checklist docs explain verification without overclaiming', () => {
  assert.equal(exists('SECURITY.md'), true);
  assert.equal(exists('docs/RELEASE_CHECKLIST.md'), true);
  assert.match(read('SECURITY.md'), /VirusTotal/i);
  assert.match(read('SECURITY.md'), /not a guarantee/i);
  assert.match(read('docs/RELEASE_CHECKLIST.md'), /VT_API_KEY/);
});
