# Classical Line Text Sources

The 384 line statements and their 小象 commentaries are maintained separately
from the spatial, temporal, and interpretive layers. Classical wording is an
input to interpretation; it never overrides the mechanically calculated
single-line change target.

## Sources

- Primary display edition: `@freizl/yijing` 2.1.0, `zh-CN/64gua.json`, MIT
  package; classical Chinese text is public domain. SHA-256:
  `5720ef8ff7428a487b87dabcb7f6952020312a10349b0bb763f44e8b026b4c7d`.
- Independent check edition: `@pro-vi/iching` 0.5.0, classical Chinese data
  extracted from `iching.js`; the package identifies the Zhouyi text as public
  domain. Upstream bundle SHA-256:
  `bc90928fb8b13acbf3e8edba5809a0d212c21e1a0d500515106b38721f3eead7`.

The check snapshot stores both the original traditional text and an OpenCC
1.0.5 `tw -> cn` comparison rendering. The comparison rendering is not used as
the display text.

## Reconciliation Policy

After simplification and punctuation normalization, 364 of 384 line statements
agree. Twenty lines differ. Eighteen are retained from the primary edition as
edition variants. Two demonstrable copy defects are corrected:

- 大有九二: the primary file duplicated 同人六二. It is restored to
  `大车以载，有攸往，无咎。`
- 姤九五: the primary file duplicated the complete line in place. One copy is
  retained.

Run `ruby bin/reconcile_classical_line_texts.rb` to regenerate the canonical
corpus, then `ruby bin/generate_spacetime_basis.rb` to rebuild the 384 structural
records.
