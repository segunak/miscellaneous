#!/usr/bin/env node
const path = require("path");

const modules = ["pptxgenjs", "react", "react-dom/server", "react-icons/fa", "sharp"];

const results = modules.map((name) => {
  try {
    const resolved = require.resolve(name, { paths: [path.resolve(__dirname, ".."), process.cwd()] });
    return { name, ok: true, resolved };
  } catch (error) {
    return { name, ok: false, error: error.message };
  }
});

const ok = results.every((item) => item.ok);
console.log(JSON.stringify({ ok, modules: results }, null, 2));
process.exit(ok ? 0 : 1);