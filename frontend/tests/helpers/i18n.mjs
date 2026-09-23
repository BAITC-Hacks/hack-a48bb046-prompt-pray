import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import ts from 'typescript'

const require = createRequire(import.meta.url)
// Load actual TS dictionaries on Node 22 without Nuxt's auto-import transform.
function load(url) {
  const source = readFileSync(url, 'utf8')
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
  }).outputText
  const exports = {}
  new Function('exports', 'require', compiled)(exports, name =>
    name.startsWith('.') ? load(new URL(`${name}.ts`, url)) : require(name))
  return exports
}

export const { createAppI18n, normalizeLocale } = load(new URL('../../app/i18n/config.ts', import.meta.url))
