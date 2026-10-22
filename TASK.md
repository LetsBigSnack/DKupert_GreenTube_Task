Instructions:

Time: 2.5 hours

Our Key Account Managers run promotions on Greentube games at casino sites and need to know whether a promotion moved stakes. Both files contain invented data:
- stakes_delivery.csv: daily stakes per site and game, April to September 2026 (about 80,000 rows), as exported from our data warehouse
- promos.csv: promotions with site, games (semicolon-separated, ALL means every game at the site), start and end dates.

Your task:
1. Load the data. The data export might have some problems, as real ones often do. If you notice any, please fix and note them. Use any language, tools or storage you like.
2. For each promo, compare total stakes during the promo with the same number of days immediately before it, for the promo's games at that site: uplift = (during - before) / before. Please note that some promotions can't be measured fairly.
3. Show the results on a simple web page a KAM could use. Python and React use is expected, but any additional languages are welcome. Feel free to use any AI tools you want to complete the task.

Please send:
- Your code (GitHub link or zip) with a few lines on how to run it
- results.csv with one row per promo: promo_id, before, during, uplift (as a percentage with one decimal, e.g. 12.3)

NOTES.md, one page at most, in your own words:
  - The data problems you found
  - What you would do if you had more time
  - What AI tools you used