# Papershelf

Research papers, explained — served at **https://papershelf.dev**.

Each paper is a page bundle in `content/papers/<slug>/index.md`: the frontmatter
holds the paper's metadata (authors, arXiv id, links), the body is the explanation.
The paper itself is never hosted here; the page links to it.

## Writing flow

The explanation is written in the Obsidian vault and copied in with:

```sh
scripts/from_vault.py "<vault note>.md" <slug>            # update as a draft
scripts/from_vault.py "<vault note>.md" <slug> --publish  # make it live
```

In the note, `(p. 4)` becomes a link that opens the paper at page 4, `![[image.png]]`
is copied into the bundle, a YouTube link on its own line is embedded, `$…$` math and
` ```mermaid ` diagrams render as-is, and `%% … %%` comments are dropped.

## Local preview

```sh
hugo server -D
```

## Deploy

Every push to `main` builds with Hugo 0.167 and deploys via GitHub Actions
(`.github/workflows/deploy.yml`). The custom domain is set in the repo's Pages
settings; DNS is on Cloudflare (proxied).
