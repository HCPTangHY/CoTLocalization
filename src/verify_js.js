#!/usr/bin/env node
/**
 * JS 语法验证 - 用 acorn 解析，精确报告错误位置和上下文
 * 从 TiTsLocalization 的 verify_js.js 移植
 * Usage: node verify_js.js <file.js> [file2.js ...]
 * Exit code: 0 = all pass, 1 = has errors
 */
const fs = require('fs');
const acorn = require('acorn');

let errors = 0;
const files = process.argv.slice(2);

if (files.length === 0) {
  console.log('Usage: node verify_js.js <file.js> [file2.js ...]');
  process.exit(0);
}

for (const file of files) {
  const basename = file.split(/[\\/]/).pop();
  process.stdout.write(`Checking ${basename}... `);

  let src;
  try {
    src = fs.readFileSync(file, 'utf8');
  } catch (e) {
    console.log(`READ ERROR: ${e.message}`);
    errors++;
    continue;
  }

  try {
    acorn.parse(src, {
      ecmaVersion: 'latest',
      sourceType: 'script',
      allowHashBang: true,
    });
    console.log('OK');
  } catch (e) {
    console.log('SYNTAX ERROR');
    const pos = e.pos || 0;
    const line = e.loc ? e.loc.line : '?';
    const col = e.loc ? e.loc.column : '?';
    console.log(`  Error: ${e.message}`);
    console.log(`  Position: offset=${pos}, line=${line}, col=${col}`);

    // Show context around error
    const start = Math.max(0, pos - 60);
    const end = Math.min(src.length, pos + 60);
    const before = src.slice(start, pos);
    const after = src.slice(pos, end);
    console.log(`  Context before: ${JSON.stringify(before)}`);
    console.log(`  >>> Error here <<<`);
    console.log(`  Context after:  ${JSON.stringify(after)}`);

    // Try to identify which translation caused it by searching nearby for CJK
    const nearby = src.slice(Math.max(0, pos - 200), Math.min(src.length, pos + 200));
    const cjkMatch = nearby.match(/[\u4e00-\u9fff\u3400-\u4dbf]{2,}/g);
    if (cjkMatch) {
      console.log(`  Nearby CJK text: ${cjkMatch.slice(0, 3).join(' | ')}`);
    }

    errors++;
  }
}

if (errors > 0) {
  console.log(`\n${errors} file(s) have syntax errors`);
  process.exit(1);
} else {
  console.log(`\nAll ${files.length} file(s) pass syntax check`);
}
