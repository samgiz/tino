import { HighlightStyle, syntaxHighlighting, tags, yaml } from './vendor/codemirror.js'

/**
 * YAML support for data files such as CV content. Reuses the Typst token
 * classes so the palette and theming stay in one place (styles.css).
 */

const yamlHighlight = HighlightStyle.define([
  { class: 'cm-typst-comment', tag: tags.lineComment },
  { class: 'cm-typst-string', tag: tags.string },
  { class: 'cm-typst-string', tag: tags.content },
  { class: 'cm-typst-function', tag: tags.definition(tags.propertyName) },
  { class: 'cm-typst-number', tag: tags.number },
  { class: 'cm-typst-keyword', tag: tags.bool },
  { class: 'cm-typst-keyword', tag: tags.null },
  { class: 'cm-typst-label', tag: tags.labelName },
  { class: 'cm-typst-keyword', tag: tags.typeName },
  { class: 'cm-typst-meta', tag: tags.meta },
  { class: 'cm-typst-punct', tag: tags.punctuation },
  { class: 'cm-typst-punct', tag: tags.separator },
])

/** Build the YAML language support extension. */

export const yamlSupport = () => [yaml(), syntaxHighlighting(yamlHighlight)]
