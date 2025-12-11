# gittuf/demo

A collection of demos of gittuf.

## Install gittuf

The [gittuf repository](https://github.com/gittuf/gittuf) provides pre-built
binaries that are signed and published using
[GoReleaser](https://goreleaser.com/). The signature for these binaries are
generated using [Sigstore](https://www.sigstore.dev/), using the release
workflow's identity. Please use release v0.1.0 or higher, as prior releases were
created to test the release workflow. Alternatively, gittuf can also be
installed using `go install`.

To build from source, clone the repository and run `make`. This will also run
the test suite prior to installing gittuf. Note that Go 1.24 or higher is
necessary to build gittuf.

```bash
git clone https://github.com/gittuf/gittuf
cd gittuf
make
```

## Demos

This repository contains various demos of gittuf functionality:

1. Basic Functionality ([demo.md](/demo.md))
2. Multi-Repository Functionality ([demo-multi-repo.md](/demo-multi-repo.md))

## gittuf Verification via GitHub Actions

It is possible to use gittuf in your CI workflows using the [gittuf-installer
GitHub Action](https://github.com/gittuf/gittuf-installer). For an example of
gittuf verification in CI, take a look at the official gittuf repository's
[workflow](https://github.com/gittuf/gittuf/actions/workflows/gittuf-verify.yml).
