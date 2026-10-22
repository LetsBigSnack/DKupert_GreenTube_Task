# Promo Uplift Dashboard — KAM Guide

This guide explains how to read and use the Promo Uplift Dashboard. No technical knowledge needed.

---

## What does this tool do?

When you run a promotion on a casino site, you want to know: **did it actually move stakes?**

This dashboard answers that question for every promotion in one place. It compares how much players staked *during* the promotion against the same number of days *immediately before* it started — at the same site, for the same games. The difference is the **uplift**.

---

## Understanding uplift

**Uplift** is expressed as a percentage and tells you whether the promotion increased or decreased stakes relative to the baseline.

| Uplift | What it means |
|---|---|
| **+25.0%** | Stakes were 25% higher during the promo than in the comparison period |
| **−10.0%** | Stakes were 10% lower — the promo may not have helped |
| **N/A** | The result cannot be reliably calculated (see below) |

The **Impact (€)** column shows the same thing in euros — the raw difference between during and before. This is the number to use when reporting business impact to management.

---

## Reading the columns

| Column | What it shows |
|---|---|
| **Promo** | The promo ID from your records |
| **Site** | The casino site where the promo ran |
| **Games** | Which games were included. **ALL games** means every game at that site was part of the promo |
| **Days** | How many days the promo ran |
| **Before (€)** | Total stakes in the same number of days *immediately before* the promo started |
| **During (€)** | Total stakes during the promo itself |
| **Impact (€)** | The euro difference: During minus Before. Green = gain, red = loss |
| **Uplift** | The percentage change. Green = positive, red = negative |

---

## The ⚠ warning icon

If you see a small warning icon (⚠) next to a Before (€) value, it means the baseline is very low (under €5,000). A large uplift percentage on a tiny baseline can be misleading — for example, going from €500 to €5,000 is a +900% uplift, but it may just be normal day-to-day variation rather than a real promo effect. Treat these results with caution before including them in a report.

---

## What does N/A mean?

Some promos cannot be fairly measured. When you see **N/A** in the Uplift column, hover over it (or read the text below the badge) to see why.

Common reasons:
- **"Date entry error — end date is before start date"** — the promo end date appears to be before the start date in the system. The data team needs to correct the entry.
- **"No stakes in the baseline period"** — there were no recorded stakes for those games at that site in the comparison window, so there is nothing to compare against.

Unmeasurable promos are hidden by default so they don't clutter your view. You can show them using the **"show N unmeasurable"** link at the top of the table.

---

## Filtering and sorting

- **Search box** — type any part of a promo ID, site name, or game name to filter the table instantly.
- **Column headers** — click any column header to sort by that column. Click again to reverse the order. The table opens sorted by Uplift (highest first) so your best-performing promos are always at the top.
- **Show/hide unmeasurable** — use the link above the table to toggle promos that cannot be measured.

---

## Things to keep in mind

- The baseline is always the **same number of days as the promo**, taken from immediately before it started. A 7-day promo is compared to the 7 days before it; a 14-day promo to the 14 days before it.
- The comparison is at the **site and game level** — a promo on Golden Fox at Casino Alpha is only compared to Golden Fox at Casino Alpha, not to other games or sites.
- **Seasonality is not adjusted for.** If the promo happened to run over a public holiday weekend and the baseline was all weekdays, the comparison may overstate the effect. Use your judgement when the timing looks unusual.
- **Overlapping promos** at the same site are not flagged automatically in the current version. If two promos ran close together, the baseline of the second one may include activity from the first.
