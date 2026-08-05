# Finances Tracker

A local monthly finance tracker built in Python. It replaces a long spreadsheet with a SQLite database, simple terminal commands, finance calculations, and a dark Streamlit dashboard with manual entry, editing, and deletion screens.

The tracker is designed for **monthly summaries**, not every individual card transaction.

## Quick Start

```zsh
git clone https://github.com/DevrajK721/Financial_Tracker.git
cd Financial_Tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
.venv/bin/python finance.py init
```

After setup, use the single command entrypoint:

```zsh
.venv/bin/python finance.py <command>
```

You do **not** need to run a long block every time.

If you prefer not to use terminal prompts for everyday tracking, start the dashboard and use the `Entries` page:

```zsh
.venv/bin/python finance.py dashboard
```

Streamlit runs in headless mode, so it should not automatically open a browser. Copy the printed local URL into your browser. By default this is:

```text
http://127.0.0.1:8501
```

If port `8501` is already in use, the launcher automatically tries the next free port and prints the URL to use, such as `http://127.0.0.1:8502`.

If you want to access the dashboard from another device on the same Wi-Fi/network, use:

```zsh
.venv/bin/python finance.py dashboard --network
```

## Everyday Commands

Add data:

```zsh
.venv/bin/python finance.py add account
.venv/bin/python finance.py add snapshot
.venv/bin/python finance.py add salary
.venv/bin/python finance.py add income
.venv/bin/python finance.py add expense
.venv/bin/python finance.py add transfer
.venv/bin/python finance.py add debt
.venv/bin/python finance.py add goal
.venv/bin/python finance.py add goal-allocation
.venv/bin/python finance.py add subscription
```

View data:

```zsh
.venv/bin/python finance.py list accounts
.venv/bin/python finance.py list month
.venv/bin/python finance.py summary
```

Fix mistakes:

```zsh
.venv/bin/python finance.py edit-account
.venv/bin/python finance.py delete
```

Guided month-end entry:

```zsh
.venv/bin/python finance.py month-end
```

PAYE-only calculator:

```zsh
.venv/bin/python finance.py paye
```

Start the dashboard:

```zsh
.venv/bin/python finance.py dashboard
```

The dashboard is launched in headless mode, so it should **not automatically open a browser**. Streamlit prints a local URL in the terminal. Copy it into your browser manually.

If the default port is busy, the app will choose the next free port and print the correct URL.

The dashboard disables Streamlit's file watcher for normal use and uses button-based navigation. The active page button is disabled, which avoids accidental duplicate clicks on the current page.

## What To Track First

1. Add accounts.
2. Add month-end account snapshots.
3. Add salary or other income.
4. Add expense category totals.
5. Add transfers.
6. Add debts, goals, subscriptions, and goal allocations as needed.
7. Run the dashboard.

## Accounts

Accounts are real places where money sits or debt exists.

```zsh
.venv/bin/python finance.py add account
```

Supported account types:

```text
Bank Account
High-Interest Savings Account
Cash ISA
Lifetime ISA
Stocks & Shares ISA
Trading Account
Pension
Debt Account
```

Examples:

```text
Monzo -> Bank Account
Marcus Saver -> High-Interest Savings Account
Cash ISA -> Cash ISA
Moneybox LISA -> Lifetime ISA
Stocks ISA -> Stocks & Shares ISA
Pension -> Pension
Student Loan -> Debt Account
```

High-interest savings accounts, Cash ISAs, Lifetime ISAs, Stocks & Shares ISAs, trading accounts, and pensions can all use start/end monthly snapshots to estimate growth after transfers. For savings-style accounts, this usually means interest or bonuses. For investment-style accounts, this usually means market performance.

View accounts:

```zsh
.venv/bin/python finance.py list accounts
```

Edit an account:

```zsh
.venv/bin/python finance.py edit-account
```

## Monthly Snapshots

Snapshots store what an account was worth at the start or end of a month.

```zsh
.venv/bin/python finance.py add snapshot
```

Example:

```text
Month [YYYY-MM]: 2026-08
Snapshot type [end/start]: end
Balance: 1250.75
```

For each account and month, the app uses the `end` snapshot when one exists. If there is no `end` snapshot yet, it falls back to the `start` snapshot so balances and net worth do not disappear while you are still entering the month.

Add both `start` and `end` snapshots for savings and investment accounts if you want growth estimates after adjusting for transfers.

## Salary And PAYE

Use this for salary where you want tax estimates:

```zsh
.venv/bin/python finance.py add salary
```

It asks for:

- gross monthly salary
- one-off bonus in this payroll
- pension salary sacrifice
- taxable benefits
- student loan plan
- postgraduate loan flag
- target account

The PAYE estimate handles income tax, employee NI estimate, pension salary sacrifice, taxable benefits, one-off cash bonus, student loan plans, and postgraduate loan.

It also supports an extra voluntary SFE/student-loan payment. This is treated as an additional cash repayment: it reduces take-home pay, but it does not change the automatic PAYE student-loan deduction, income tax, or NI estimate.

Important: PAYE is an estimate, not full payroll software. Scottish tax bands, tax codes, complex payroll timing, and all benefit-specific NI rules are not fully implemented yet.

Run a calculation without saving:

```zsh
.venv/bin/python finance.py paye
```

## Other Income

Use this for family support, manual bonus entries, or other non-salary income:

```zsh
.venv/bin/python finance.py add income
```

Income types:

```text
Salary
Bonus
Family Support
Other Income
```

## Expenses

Use monthly category totals, not every individual purchase:

```zsh
.venv/bin/python finance.py add expense
```

Expense categories:

```text
rent
transport
food
gym
clothing
phone
subscriptions
other
```

## Transfers

Transfers are movements between your own accounts. They do not count as income or expenses.

```zsh
.venv/bin/python finance.py add transfer
```

Example:

```text
Monzo -> Cash ISA
Amount: 500
Label: Cash ISA contribution
```

## Debts

Create a debt account first:

```zsh
.venv/bin/python finance.py add account
```

Use account type:

```text
debt
```

Then add debt metadata:

```zsh
.venv/bin/python finance.py add debt
```

The debt form asks for:

```text
Debt account
Balance month
Current outstanding debt balance
Annual interest rate
Minimum monthly payment / expected repayment
Notes
```

Behind the scenes, the current outstanding balance is saved as an end-of-month account snapshot. That means the dashboard can show debt history and debt projections over time.

You can also update a debt balance directly through snapshots:

```zsh
.venv/bin/python finance.py add snapshot
```

Debt insights include total debt, debt change, current balances, minimum/expected payments, and simple payoff estimates.

## Goals

Create a goal:

```zsh
.venv/bin/python finance.py add goal
```

Then allocate part of a real account balance to that goal:

```zsh
.venv/bin/python finance.py add goal-allocation
```

This lets you say something like “800 of Cash ISA is allocated to Holiday” without creating fake accounts.

## Subscriptions

Add recurring payments:

```zsh
.venv/bin/python finance.py add subscription
```

Examples:

```text
Phone contract
Gym
Netflix
Spotify
```

## Viewing, Editing, And Removing Entries

The easiest option is now the dashboard:

```zsh
.venv/bin/python finance.py dashboard
```

Open the printed URL, then use the `Entries` page in the top menu.

The `Entries` page has:

- `Add`: add accounts, monthly snapshots, salary with PAYE/SFE deductions, other income, expenses, transfers, debt profiles, goals, goal allocations, and subscriptions.
- `Edit`: defaults to monthly records with existing records shown first; use `Accounts` inside Edit when you specifically want to change account details.
- `Delete`: select one or more records in a table, confirm the action, and delete them together.

The `Add`, `Edit`, and `Delete` areas use their own mini-navigation, so saving a change keeps you in the same area instead of jumping back to another section.

After a successful add, edit, or delete, the dashboard automatically refreshes itself so charts and tables show the latest data without a manual browser refresh.

The terminal commands are still available if you want a faster keyboard-only workflow.

View accounts:

```zsh
.venv/bin/python finance.py list accounts
```

View raw entries for one month:

```zsh
.venv/bin/python finance.py list month
```

View calculated monthly summary:

```zsh
.venv/bin/python finance.py summary
```

Edit account details:

```zsh
.venv/bin/python finance.py edit-account
```

Delete a mistaken record:

```zsh
.venv/bin/python finance.py delete
```

Delete supports:

```text
Accounts
Account Balance Snapshots
Income Entries
Expense Entries
Transfers
Debt Profiles
Savings Goals
Goal Allocations
Subscriptions
```

Be careful deleting accounts because other records can point to them.

## Dashboard

Start it with:

```zsh
.venv/bin/python finance.py dashboard
```

Streamlit prints the local URL in the terminal. Copy it into your browser manually.

The dashboard is organised with a modern top menu:

- `✍️ Entries`: add, edit, and delete finance records directly in the app.
- `🏦 Balances`: account balances and balance mix.
- `📈 Statistics`: net worth growth, assets, debts, and projected net worth.
- `🥧 Spending`: spending pie chart, previous-month comparison, total spending, and category trends.
- `📉 Debts`: debt totals, actual debt growth, projected debt growth, debt mix, and payoff estimates.
- `🎯 Goals`: goal funding and subscriptions.
- `🧾 Records`: readable records and summary JSON.

Navigation uses button-style page controls rather than browser links. The page you are already on is disabled, so clicking the active page again should not trigger another dashboard rerun.

The app uses a dark theme with red accents configured in `.streamlit/config.toml`.

## Local Data Storage

Yes, the data is local.

The app stores your finance data in a SQLite database file:

```text
data/processed/finances.db
```

Nothing is uploaded to a cloud database by this project. The Streamlit dashboard reads from and writes to that local SQLite file on your machine.

The main pieces are:

- `src/db.py`: defines the database path and opens safe SQLAlchemy sessions.
- `src/models/`: defines the database tables, such as accounts, snapshots, expenses, debts, goals, and subscriptions.
- `app/dashboard.py`: provides the visual UI and writes entries into the same local database.
- `finance.py`: starts the dashboard or terminal workflows.

Because it is local, you should back up `data/processed/finances.db` if you care about preserving the records.

For GitHub/public sharing, the real database and raw data folders are ignored by `.gitignore`. The repository keeps only empty `.gitkeep` files inside `data/raw/` and `data/processed/` so the folder structure exists for new users without publishing private finance data.

## Tests

```zsh
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src cli scripts tests app finance.py
```

## Project Structure

```text
finance.py        Single command entrypoint
cli/              Individual terminal workflows
scripts/          Database setup
src/db.py         SQLite and SQLAlchemy setup
src/models/       Database table definitions
src/services/     Finance calculations and dashboard queries
src/reports/      Summary builders
app/dashboard.py  Streamlit dashboard
tests/            Automated tests
data/processed/   Local SQLite database folder
data/raw/         Optional local import folder
```

## Current Limitations

- PAYE is an estimate, not a payroll replacement.
- Scottish tax bands and tax codes are not implemented yet.
- There is no migration system yet, so schema changes during development may require recreating the local database.
