# Household Spending Tool — Requirements Specification

**Status:** Draft v1
**Date:** 7 September 2026

---

## 1. Purpose

A shared ledger for a household that pools money into a single joint bank
account. Members contribute an amount each month and pay for household costs
out of their own pocket, reimbursing themselves by depositing only the net
difference.

The tool exists to answer two questions:

1. **What does each member owe (or get back) this month?**
2. **How much is in the joint account?**

Accuracy is required *eventually*, not continuously. Members may fall months
behind on data entry. When everyone is caught up, the tool's balance equals the
real bank balance.

---

## 2. Money model

The joint account is a savings pot. It normally has no regular outgoings; it
accumulates and absorbs occasional large or unexpected costs.

### 2.1 How a month works

1. Each member declares a **contribution** for the month. It is their own
   choice and may differ every month and between members. There is no fairness
   rule, no income split, no enforcement.
2. During the month, members pay for household things with their own money and
   log each purchase as an **expense**.
3. At settlement, each member moves a single net amount:

   ```
   transfer = contribution − their expenses for that month
   ```

   - **Positive** → the member deposits that amount into the joint account.
   - **Negative** → the joint account pays that amount out to the member.

4. The account may also be debited directly for a **pot expense** (a large or
   unexpected cost paid straight from the joint account, with no member to
   reimburse), and credited with **interest**.

### 2.2 The balance

```
balance = Σ contributions
        + Σ interest
        − Σ member expenses
        − Σ pot expenses
```

This is always recomputed from the full set of entries. It is never stored as a
running total and never carried forward.

### 2.3 Worked example

Household of two, March:

| Entry | Member | Amount |
|---|---|---|
| Contribution | Alice | 2,000 |
| Contribution | Bob | 1,500 |
| Expense — Groceries | Alice | 400 |
| Expense — Dining | Alice | 200 |
| Expense — Utilities | Bob | 1,700 |
| Pot expense — Others (car repair) | — | 800 |
| Interest | — | 12 |

**Transfers:** Alice deposits 1,400 (2,000 − 600). Bob receives 200
(1,500 − 1,700). 

**Balance change for March:**
`(2,000 + 1,500) + 12 − (600 + 1,700) − 800 = +412`

Cross-check via actual account movements:
`+1,400 (Alice) − 200 (Bob) + 12 (interest) − 800 (car repair) = +412` ✓

---

## 3. Data model

### 3.1 Member

| Field | Notes |
|---|---|
| `id` | |
| `name` | Display name |
| `login credentials` | Each member has their own account |

A small, fixed set of people. All members have equal permissions.

### 3.2 Entry

A single unified ledger table. `entry_type` determines direction and whether a
member is attached.

| Field | Notes |
|---|---|
| `id` | |
| `entry_type` | `contribution` \| `expense` \| `pot_expense` \| `interest` |
| `member_id` | Required for `contribution` and `expense`; null otherwise |
| `date` | The date the money was actually spent or earned |
| `amount` | Always stored positive; direction comes from `entry_type` |
| `category_id` | See §4 |
| `purpose` | Free text. Absorbs anything unusual — e.g. a foreign-currency note like "EUR 84 @ 1.58" |
| `created_by`, `created_at` | |
| `last_edited_by`, `last_edited_at` | Shown on the entry |
| `deleted_at`, `deleted_by` | Soft delete only |

**Direction by type:**

| `entry_type` | Effect on balance | Member attached |
|---|---|---|
| `contribution` | `+` | Yes |
| `interest` | `+` | No |
| `expense` | `−` | Yes |
| `pot_expense` | `−` | No |

The month an entry belongs to is derived from `date`. There is no second
"settlement month" field — an entry always counts in the month it happened,
regardless of when it was typed in.

### 3.3 Month lock

| Field | Notes |
|---|---|
| `member_id` | |
| `month` | |
| `locked_at` | |

A per-member, per-month **"I'm done"** marker. It is purely informational and
has **no effect on the maths or on editability**. It exists so members can see
who has caught up to when.

Members lock independently. Alice may be locked through March while Bob is
locked through August. Any member may lock or unlock their own months.

---

## 4. Categories

Categories are stored in the database and are **editable in the app** — members
can add, rename and remove them.

Initial set:

- Groceries
- Dining
- Household
- Mortgage
- Car loan
- Studies
- Children education
- Children enrichment
- Entertainment
- **Deposit** — used for member contributions
- Insurance
- Parking
- Travel
- Utilities
- Home management fee
- **Others**

**Deposit** is a system category: it is applied automatically to every
`contribution` entry and cannot be deleted or reused for expenses. It may be
renamed.

Removing a category that is already in use should reassign existing entries to
**Others** rather than orphan them.

---

## 5. Rules

1. **Nothing is ever frozen.** Any member may create, edit or soft-delete any
   entry, including another member's, at any time, in any month.
2. **Late entries go in their real month.** A March receipt entered in
   September is dated March and counts in March. March's totals and balance
   change retroactively. This is intended.
3. **No approval workflow.** Any member may log a pot expense or interest with
   no second signature.
4. **No duplicate guard on interest.** Two interest entries in the same month
   are permitted; both count.
5. **Single currency.** One currency for all amounts. Conversions are done by
   the member before entry and noted in `purpose`.
6. **Full transparency.** Every member can see every entry from every member,
   and the full balance.
7. **Ledger is the source of truth.** No reconciliation against bank statement
   lines, no imported transactions, no stored bank balance.

---

## 6. Derived values

Nothing below is stored; all are computed on read.

| Value | Formula |
|---|---|
| Account balance | `Σ contributions + Σ interest − Σ expenses − Σ pot expenses` |
| Member's transfer for a month | `their contributions that month − their expenses that month` |
| Member's total contributed | `Σ their contributions` |
| Member's total spent | `Σ their expenses` |
| Spend by category | Grouped over `expense` and `pot_expense` |
| Caught-up-to | Latest consecutively locked month per member |

---

## 7. Screens

### 7.1 Ledger

The complete log, all members, newest first. Filterable by month, member,
category and entry type. Each row shows date, member, category, amount,
purpose, and "last edited by X". Inline edit and delete.

### 7.2 Month view

For a chosen month, one row per member:

| Member | Contribution | Spent | Transfer | Locked |
|---|---|---|---|---|
| Alice | 2,000 | 600 | **deposit 1,400** | ✓ |
| Bob | 1,500 | 1,700 | **receive 200** | — |

Plus that month's pot expenses and interest, and the resulting change in
balance. A lock/unlock toggle for the signed-in member's own row.

### 7.3 Entry form

Type, member (pre-filled with signed-in user for expenses), date, amount,
category, purpose. Should be fast enough to use repeatedly for a backlog of
receipts.

### 7.4 Balance and reports

Current balance, prominently. Spend by category for a chosen period. Per-member
totals. A "who is caught up to when" indicator.

---

## 8. Out of scope

Explicitly not being built:

- Bank feed, statement import or transaction matching
- Any enforced fairness, income-based split or budget limits
- Approval or sign-off workflows
- Multi-currency handling or exchange rate lookup
- Automatic exchange rate conversion
- Recurring bills paid from the joint account
- Notifications and reminders
- Full edit-history audit log (only "last edited by" is kept)
- Multiple households in one instance

---

## 9. Open decisions

1. **Receipt attachments** — never discussed. Worth deciding before the data
   model is fixed, since it affects storage.
2. **More than one contribution per member per month** — currently permitted
   and simply summed. Confirm that's acceptable, or constrain to one.
3. **Deleting a member** who has entries — soft-delete and keep their history,
   presumably.
4. **Financial year boundary** — is there an annual roll-up or closing report,
   given accuracy is targeted at year's end?
5. **Where it runs** — hosted web app, self-hosted, or local network only.
