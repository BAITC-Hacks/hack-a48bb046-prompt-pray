import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { test } from 'node:test'
import { compileScript, parse } from '@vue/compiler-sfc'
import { createSSRApp, h, ref, computed, useTemplateRef } from 'vue'
import { renderToString } from 'vue/server-renderer'
import ts from 'typescript'
import { createAppI18n } from './helpers/i18n.mjs'

const require = createRequire(import.meta.url)

for (const page of ['login', 'signup']) {
  const { descriptor } = parse(readFileSync(new URL(`../app/pages/${page}.vue`, import.meta.url), 'utf8'))
  const compiled = compileScript(descriptor, { id: `${page}-language-test`, inlineTemplate: true })
  const code = ts.transpileModule(compiled.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
  }).outputText

  for (const locale of ['ru', 'kk', 'en']) {
    test(`${page}: ${locale} translates labels and initially missing input errors`, async () => {
      const composer = createAppI18n(locale).global
      const globals = {
        ref, computed, useTemplateRef,
        definePageMeta: () => {},
        useSeoMeta: () => {},
        useAppI18n: () => composer,
        useApi: () => ({}),
        useApiMessages: () => ({ errorMessage: () => '' }),
        useRoute: () => ({ query: {} }),
        useLocalizedForm: () => {}
      }
      const exports = {}
      new Function('exports', 'require', ...Object.keys(globals), code)(exports, require, ...Object.values(globals))
      const app = createSSRApp(exports.default)
      let snapshot
      app.component('UAuthForm', {
        props: ['schema', 'fields', 'title'],
        setup(props) {
          snapshot = props
          return () => h('section', props.title)
        }
      })
      app.component('UFormField', { setup: (_, { slots }) => () => h('div', slots.default?.()) })
      for (const name of ['USelect', 'ULink', 'UAlert']) app.component(name, { render: () => null })
      await renderToString(app)

      assert.equal(snapshot.fields.find(field => field.name === 'password').label, composer.t('auth.password'))
      assert.equal(snapshot.fields.find(field => field.name === 'email').label, composer.t(page === 'login' ? 'auth.identifier' : 'auth.email'))
      assert.equal(snapshot.schema.safeParse({ username: 'demo_business', email: 'demo_business', password: 'Example-only-123' }).success, page === 'login')
      const result = snapshot.schema.safeParse({})
      assert.equal(result.success, false)
      for (const issue of result.error.issues) {
        assert.equal(issue.message, composer.t(issue.path[0] === 'email' ? (page === 'login' ? 'validation.identifier' : 'validation.email') : 'validation.required'))
      }
    })
  }
}
