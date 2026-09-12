import {existsSync, readFileSync} from 'node:fs';
import {spawn, spawnSync} from 'node:child_process';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const serverDir = join(root, 'server');
const frontendDir = join(root, 'examguard-pro');
const isWindows = process.platform === 'win32';
const python = isWindows
  ? join(serverDir, '.venv', 'Scripts', 'python.exe')
  : join(serverDir, '.venv', 'bin', 'python');
const pythonCommand = existsSync(python) ? python : 'python';
const npmCommand = isWindows ? 'npm.cmd' : 'npm';
const children = [];

function loadEnvFile() {
  const env = {...process.env};
  const envPath = join(serverDir, '.env');

  if (!existsSync(envPath)) {
    return env;
  }

  for (const line of readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const match = line.trim().match(/^([^#=\s]+)\s*=\s*(.*)$/);
    if (!match) continue;
    const [, name, rawValue] = match;
    const value = rawValue.trim().replace(/^(['"])(.*)\1$/, '$2');
    if (env[name] === undefined) env[name] = value;
  }
  return env;
}

const env = loadEnvFile();
let redisUrl =
  env.CELERY_BROKER_URL || env.REDIS_URL || 'redis://localhost:6379/0';
if (env.REDIS_PASSWORD) {
  const parsed = new URL(redisUrl);
  parsed.username = env.REDIS_USERNAME || 'default';
  parsed.password = env.REDIS_PASSWORD;
  redisUrl = parsed.toString();
  env.REDIS_URL = redisUrl;
  env.CELERY_BROKER_URL = redisUrl;
  env.CELERY_RESULT_BACKEND = redisUrl;
}
env.REDIS_URL ??= redisUrl;
env.CELERY_BROKER_URL ??= redisUrl;
env.CELERY_RESULT_BACKEND ??= redisUrl;

function displayRedisUrl(url) {
  try {
    const parsed = new URL(url);
    if (parsed.password) parsed.password = '***';
    return parsed.toString();
  } catch {
    return '<invalid Redis URL>';
  }
}

function run(command, args, options = {}) {
  return spawn(command, args, {
    cwd: options.cwd || root,
    env,
    stdio: 'inherit',
    windowsVerbatimArguments: false,
  });
}

function checkRedis() {
  const script = [
    'import os, redis',
    'url = os.environ["EXAMGUARD_REDIS_URL"]',
    'try:',
    '    redis.from_url(url, decode_responses=True).ping()',
    '    print("REDIS_CONNECTED " + url)',
    'except Exception as exc:',
    '    print("REDIS_DISCONNECTED " + type(exc).__name__ + ": " + str(exc))',
    '    raise SystemExit(1)',
  ].join('\n');

  const result = spawnSync(
    pythonCommand,
    ['-c', script],
    {
      cwd: serverDir,
      env: {...env, EXAMGUARD_REDIS_URL: redisUrl},
      encoding: 'utf8',
    },
  );

  const output = `${result.stdout || ''}${result.stderr || ''}`;
  process.stdout.write(output);
  return {ok: result.status === 0, output};
}

function startLocalRedisIfPossible() {
  let isLocal = false;
  try {
    const parsed = new URL(redisUrl);
    isLocal = parsed.protocol === 'redis:' &&
      (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1');
  } catch {
    console.warn('Redis URL is invalid; skipping automatic local Redis startup.');
  }
  if (!isLocal) {
    return;
  }

  const docker = spawnSync(
    'docker',
    ['compose', 'up', '-d', 'redis'],
    {cwd: root, env, stdio: 'inherit'},
  );
  if (docker.error) {
    console.warn('Docker is unavailable; checking an already-running local Redis.');
  }
}

function stopAll(code = 0) {
  for (const child of children) {
    if (!child.killed) child.kill('SIGTERM');
  }
  process.exitCode = code;
}

console.log('=== ExamGuard Pro development stack ===');
console.log(`Redis: ${displayRedisUrl(redisUrl)}`);

let redisCheck = checkRedis();
if (
  !redisCheck.ok &&
  !/Authentication|authentication|required|WRONG_VERSION/.test(redisCheck.output)
) {
  startLocalRedisIfPossible();
  redisCheck = checkRedis();
}
if (!redisCheck.ok) {
  console.error(
    '\nRedis is not reachable. Start Redis or fix REDIS_URL/CELERY_BROKER_URL in server/.env, then run npm run dev again.',
  );
  process.exit(1);
}

const api = run(
  pythonCommand,
  ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000', '--reload'],
  {cwd: serverDir},
);
const workerArgs = [
  '-m',
  'celery',
  '-A',
  'workers.celery_app',
  'worker',
  '--loglevel=info',
  '-Q',
  'face,object,gaze,ocr,nlp,report,default',
  ...(isWindows ? ['--pool=solo'] : ['-c', '2']),
];
const worker = run(pythonCommand, workerArgs, {cwd: serverDir});
const frontend = run(npmCommand, ['run', 'dev'], {cwd: frontendDir});
children.push(api, worker, frontend);

for (const child of children) {
  child.on('exit', (code, signal) => {
    if (code !== 0 && code !== null) {
      console.error(`A development service stopped with exit code ${code}.`);
      stopAll(code);
    } else if (signal) {
      stopAll(0);
    }
  });
}

process.on('SIGINT', () => stopAll(0));
process.on('SIGTERM', () => stopAll(0));
