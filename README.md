# expense-app

Tracking household expenses and deposits.

Requirements are in [`_doc/plan.md`](_doc/plan.md); the build order is in
[`backlog.md`](backlog.md).

## Setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/). It reads
`pyproject.toml`, installs the exact versions in `uv.lock`, and creates `.venv`
for you — there is no separate virtualenv or `pip install` step.

```sh
uv sync                          # create .venv and install dependencies
uv run manage.py migrate
uv run manage.py createsuperuser
uv run manage.py runserver
```

`uv run` executes inside the project environment, so activating `.venv` is
optional.

## Tests

```sh
uv run manage.py test
```

## Dependencies

```sh
uv add <package>                 # add a runtime dependency
uv add --dev <package>           # add a development-only dependency
uv sync --frozen                 # install exactly the lockfile, changing nothing
```

`pyproject.toml` and `uv.lock` are both committed; `uv.lock` is what pins the
versions, so commit it whenever dependencies change.
