# Contributing

Bug reports and pull requests are welcome. Before you change behavior, read
[CONTEXT.md](CONTEXT.md) for the project's vocabulary and
[docs/adr/](docs/adr/) for the decisions behind the current design.

## Running the tests

The tests are POSIX `sh` scripts in `scripts/test-*`. They need `tmux`. Tests
that talk to tmux use a stub or a separate tmux server, so they don't touch your
sessions.

```sh
for t in scripts/test-*; do sh "$t" || echo "FAILED: $t"; done
```

CI runs the same scripts on every push and pull request.

## Commit messages

Use [conventional commits](https://www.conventionalcommits.org/) (`feat:`,
`fix:`, `docs:`, …). The release notes are generated from them.

