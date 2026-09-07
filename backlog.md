# Backlog — Household Spending Tool

Derived from [`_doc/plan.md`](_doc/plan.md) (Draft v1, 7 Sep 2026).

Current state: Django 6.1.1 project (`config`) + empty `expenses` app, SQLite,
migrations already applied against the default `auth.User`. `db.sqlite3` is
gitignored, so the database can still be thrown away without cost.

Task IDs are stable. Each task lists dependencies and acceptance criteria.
Milestones are ordered so that every one of them ends at a usable app.

---

## Decisions needed before M1

These come from §9 of the spec. Only the first two block code; the rest can be
answered later without rework.

| # | Decision | Blocks | Recommendation |
|---|---|---|---|
| D1 | Member = Django user, or separate `Member` model linked to a user? | E-1, E-2 | **One custom user model** (`expenses.Member` extending `AbstractUser`). The spec says a small fixed set of people, all equal, each with login credentials — a second table buys nothing. |
| D2 | Receipt attachments (§9.1) | E-2 (schema) | **Defer, but reserve.** Not in v1; adding a separate `EntryAttachment` table later needs no change to `Entry`. Recorded as F-1 in Deferred. |
| D3 | More than one contribution per member per month (§9.2) | — | **Permit and sum**, as the spec currently does. §6 already defines the transfer as a sum; no constraint to write. |
| D4 | Deleting a member with entries (§9.3) | C-4 | **Soft delete** (`is_active = False`), history retained, excluded from new entry forms. |
| D5 | Financial-year roll-up (§9.4) | — | Not in v1. The reports screen (D-3) takes an arbitrary date range, which covers a year. |
| D6 | Where it runs (§9.5) | E-1 | Assumed **single self-hosted instance**, one household, SQLite. Revisit only if that changes. |

If D1 is answered differently, A-1 and A-2 change shape and everything
downstream keeps its structure.

---

## M0 — Foundations

Groundwork that is painful to retrofit. Do this before any model work.

### A-1 · Custom user model
Replace `auth.User` with `expenses.Member` (`AbstractUser`, `name` as display
name) and set `AUTH_USER_MODEL`. Delete the local `db.sqlite3` and re-run
migrations from scratch — the DB is gitignored and holds nothing.

- **Depends on:** D1
- **Done when:** `AUTH_USER_MODEL = 'expenses.Member'`; `migrate` succeeds on an
  empty DB; `createsuperuser` works; `Member` is registered in the admin.
- **Note:** this is the last cheap moment to do it. After real data exists the
  swap is a multi-hour migration.

### A-2 · Settings hygiene
Split settings so the app can run outside the dev machine: `SECRET_KEY`,
`DEBUG`, `ALLOWED_HOSTS` and `DATABASES` read from the environment with
dev-friendly defaults. Set `TIME_ZONE` to the household's zone (dates are the
unit of accounting; UTC will shift month boundaries). Add `.env.example`.

- **Depends on:** —
- **Done when:** `runserver` works with no env vars set; `manage.py check
  --deploy` reports no `SECRET_KEY`/`DEBUG` errors when the production env vars
  are supplied.

### A-3 · Base template, static files and layout
One base template with the nav (Ledger · Month · Balance), messages framework
rendering, and a stylesheet. Pick the front-end approach now: **server-rendered
Django templates + HTMX** for the inline edit in §7.1 — no build step, no SPA.

- **Depends on:** —
- **Done when:** a placeholder page renders through `base.html` on all three nav
  routes; static files are served in dev.

### A-4 · Test and quality baseline
`pytest` + `pytest-django` (or plain `manage.py test` — pick one and stay), a
`factory-boy` factory per model as they land, `ruff` for lint/format, and a
`Makefile` or `just` file with `test`/`lint`/`run`. Dev tools go in a uv dev
group (`uv add --dev …`) so they stay out of the production install.

- **Depends on:** —
- **Done when:** `make test` runs green on an empty suite; `make lint` is clean.

---

## M1 — Ledger core

The data model and the maths. No screens yet beyond the admin.

### B-1 · Category model + seed data
`Category` with `name`, `is_system`, `deleted_at`. Data migration seeding the 16
categories from §4, with **Deposit** and **Others** flagged `is_system`.

- **Depends on:** A-1
- **Done when:** `migrate` on an empty DB yields exactly the §4 list; `Deposit`
  and `Others` are marked as system; re-running migrations does not duplicate
  rows.

### B-2 · Entry model
Single unified table per §3.2: `entry_type` (TextChoices), nullable `member`,
`date`, `amount` (`DecimalField(max_digits=10, decimal_places=2)`, positive),
`category`, `purpose`, `created_by`/`created_at`,
`last_edited_by`/`last_edited_at`, `deleted_at`/`deleted_by`.

- **Depends on:** A-1, B-1
- **Done when:** migrations apply; `amount` rejects zero and negatives; indexes
  exist on `date` and on `(entry_type, date)`.

### B-3 · Entry invariants
Enforce §3.2's direction table: `member` **required** for `contribution` and
`expense`, **null** for `interest` and `pot_expense`. Contributions are forced
to the Deposit category and Deposit is rejected on expenses (§4). Implement as
DB `CheckConstraint`s plus `clean()` so both the ORM and the forms enforce them.

- **Depends on:** B-2
- **Done when:** each violation raises `IntegrityError` at the DB layer and
  `ValidationError` from `full_clean()`; tests cover all four entry types.

### B-4 · Soft delete manager
Default manager excludes `deleted_at__isnull=False`; `all_objects` sees
everything. A `soft_delete(by=member)` method stamps `deleted_at`/`deleted_by`.
Hard delete is never exposed in the UI.

- **Depends on:** B-2
- **Done when:** a soft-deleted entry vanishes from every query and from all
  balance maths, and is still retrievable via `all_objects`.

### B-5 · Derived-value calculations
A `selectors.py` (or `queries.py`) module implementing every row of §6 as a
single aggregate query each: account balance, per-member transfer for a month,
per-member totals, spend by category over a range, caught-up-to. Nothing stored,
nothing cached.

- **Depends on:** B-3, B-4
- **Done when:** the §2.3 worked example is a test that passes both the balance
  formula and the account-movement cross-check (+412); each function is one
  query (assert with `assertNumQueries`).

### B-6 · MonthLock model
Per §3.3: `member`, `month` (store as a `DateField` pinned to the 1st, or an
integer `YYYYMM` — pick one and document it), `locked_at`. Unique on
`(member, month)`. Purely informational: **no** signal, constraint or check may
consult it.

- **Depends on:** A-1
- **Done when:** locking is idempotent; a test asserts that locking a month does
  not change any value from B-5 and does not block edits in that month.

### B-7 · Admin registration
Register `Entry`, `Category` and `MonthLock` with sensible list displays and
filters. This is the stopgap data-entry UI until M2 lands.

- **Depends on:** B-2, B-1, B-6
- **Done when:** the §2.3 example can be entered end to end through the admin.

---

## M2 — Screens

### C-1 · Auth
Login, logout and password change using Django's built-in views, styled into
`base.html`. Every app view is login-required. No self-registration — members
are created in the admin (D6: one household, fixed set).

- **Depends on:** A-1, A-3
- **Done when:** anonymous access to any app URL redirects to login; a logged-in
  member sees their name in the nav.

### C-2 · Entry form (§7.3)
Create and edit. Type, member (pre-filled with the signed-in user for expenses,
hidden for pot expense/interest), date, amount, category, purpose. Optimised for
repetition: date defaults to the last-used date, save-and-add-another returns a
blank form with the date and type retained, focus lands on amount.

- **Depends on:** B-3, C-1
- **Done when:** a backlog of ten receipts can be entered without touching the
  mouse; validation errors from B-3 render inline; editing stamps
  `last_edited_by`/`last_edited_at`.

### C-3 · Ledger screen (§7.1)
All entries, newest first, all members. Filters for month, member, category and
entry type. Each row: date, member, category, amount, purpose, "last edited by
X". Inline edit and soft delete via HTMX. Pagination.

- **Depends on:** C-2, B-4
- **Done when:** filters compose (month + member + category at once); inline
  edit updates the row in place; delete is soft and the row disappears; the page
  holds a constant query count as rows grow (`select_related`).

### C-4 · Month view (§7.2)
For a chosen month: one row per member with contribution, spent, transfer
(rendered as **"deposit 1,400"** / **"receive 200"**, never a bare signed
number), and lock state. Below it, that month's pot expenses and interest, and
the resulting change in balance. Lock/unlock toggle on the signed-in member's
own row only.

- **Depends on:** B-5, B-6, C-1
- **Done when:** the §2.3 month reproduces the spec's table exactly; the toggle
  affects only the current member's row; prev/next month navigation works.

### C-5 · Category management (§4)
List, add, rename. Removing a category reassigns its entries to **Others** in a
transaction before soft-deleting it. **Deposit** and **Others** can be renamed
but not deleted.

- **Depends on:** B-1, C-1
- **Done when:** deleting an in-use category leaves zero orphaned entries and
  the balance is unchanged; deleting Deposit or Others is refused with a clear
  message.

---

## M3 — Reporting and release

### D-1 · Balance screen (§7.4)
Current balance, prominently. Per-member totals contributed and spent. A "who is
caught up to when" panel driven by the caught-up-to selector (latest
*consecutively* locked month per member — note the consecutive rule; a lone
locked month after a gap does not count).

- **Depends on:** B-5, B-6, C-1
- **Done when:** a member locked for Jan, Feb and Apr reads as caught up to Feb.

### D-2 · Spend by category
Grouped over `expense` and `pot_expense` for a chosen date range, with pot
expenses distinguishable from member expenses. Table first; a chart only if it
adds something the table does not.

- **Depends on:** B-5
- **Done when:** category totals sum to total spend for the range.

### D-3 · Seed / demo data command
`manage.py seed_demo` producing a two-member household with a few months of
entries, so the screens can be exercised and reviewed without hand-typing.

- **Depends on:** B-3, B-6
- **Done when:** a fresh clone reaches a populated app in three commands.

### D-4 · Deployment
Per D6: `whitenoise` for static files, `gunicorn`, install with `uv sync
--frozen --no-dev` (or `uv export` to a lockfile-derived `requirements.txt` if
the target cannot run uv), a `Procfile` or compose file,
`DEBUG=False` with a real `SECRET_KEY`, and a documented SQLite backup (a
scheduled file copy is sufficient for one household).

- **Depends on:** A-2, all of M2
- **Done when:** `manage.py check --deploy` is clean and the app serves on the
  target host with static files intact.

### D-5 · README
Setup, running, tests, and a short statement of the money model so a future
reader does not have to reverse-engineer §2.

- **Depends on:** D-4
- **Done when:** a clean clone can be run from the README alone.

---

## Deferred (explicitly not in v1)

Everything in §8, plus:

- **F-1 · Receipt attachments** (D2) — a separate `EntryAttachment` table when
  wanted; needs a storage decision.
- **F-2 · Financial-year roll-up** (D5) — D-2's date range covers it for now.
- **F-3 · Full edit-history audit log** — §8 keeps only "last edited by".

---

## Suggested order

```
A-1 → A-2 → A-3 → A-4          foundations, all cheap, all first
  → B-1 → B-2 → B-3 → B-4 → B-5   model + maths, gated by the §2.3 test
  → B-6, B-7                      lock + admin (usable app: admin data entry)
  → C-1 → C-2 → C-3 → C-4 → C-5   screens (usable app: real UI)
  → D-1 → D-2 → D-3 → D-4 → D-5   reports + ship
```

Two things carry the most risk and should be done exactly once, early: **A-1**
(the user model swap, cheap only until real data exists) and **B-5** (the
balance maths, which every screen reads through). The §2.3 worked example is the
single best test in the suite — write it as soon as B-3 lands.
