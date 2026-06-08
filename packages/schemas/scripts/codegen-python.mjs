// Generates Pydantic v2 models into gen/python/models.py from the JSON Schemas, using
// datamodel-code-generator. Prefers a local toolchain (uv / python), falls back to Docker.
// Exits non-zero (handled by the caller) if no toolchain is available.

import { existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const here = dirname(fileURLToPath(import.meta.url));
const pkgRoot = join(here, '..');
const outDir = join(pkgRoot, 'gen', 'python');
mkdirSync(outDir, { recursive: true });
const outFile = join(outDir, 'models.py');

// datamodel-codegen args shared across runners.
const dcgArgs = [
  '--input',
  'schemas',
  '--input-file-type',
  'jsonschema',
  '--output',
  'gen/python/models.py',
  '--output-model-type',
  'pydantic_v2.BaseModel',
  '--target-python-version',
  '3.12',
  '--use-standard-collections',
  '--use-union-operator',
  '--use-schema-description',
  '--snake-case-field',
  '--disable-timestamp',
];

function tryRun(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { cwd: pkgRoot, stdio: 'inherit', ...opts });
  return r.status === 0;
}

function which(cmd) {
  const probe = process.platform === 'win32' ? 'where' : 'which';
  return spawnSync(probe, [cmd]).status === 0;
}

let ok = false;

// 1) uv (preferred): runs datamodel-code-generator in an ephemeral env.
if (!ok && which('uv')) {
  ok = tryRun('uv', ['run', '--with', 'datamodel-code-generator', 'datamodel-codegen', ...dcgArgs]);
}

// 2) plain python -m (if datamodel-code-generator is installed).
if (!ok && (which('python') || which('python3'))) {
  const py = which('python') ? 'python' : 'python3';
  ok = tryRun(py, ['-m', 'datamodel_code_generator', ...dcgArgs]);
}

// 3) Docker fallback (no local Python needed).
if (!ok && which('docker')) {
  ok = tryRun('docker', [
    'run',
    '--rm',
    '-v',
    `${pkgRoot}:/work`,
    '-w',
    '/work',
    'python:3.12-slim',
    'sh',
    '-c',
    'pip install --quiet datamodel-code-generator && datamodel-codegen ' + dcgArgs.join(' '),
  ]);
}

if (ok && existsSync(outFile)) {
  console.log('[codegen] wrote gen/python/models.py');
  process.exit(0);
} else {
  console.error('[codegen] could not generate Python models (no uv/python/docker).');
  process.exit(1);
}
