import { useEffect, useState, useMemo } from "react";

const LOW_BASELINE_THRESHOLD = 5000;

function UpliftBadge({ uplift, measurable, reason }) {
  if (!measurable) {
    return (
      <div className="flex flex-col items-end gap-0.5">
        <span
          title={reason}
          className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-500 cursor-help"
        >
          N/A
          <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
              clipRule="evenodd"
            />
          </svg>
        </span>
        <span className="text-[10px] text-gray-400 max-w-[120px] text-right leading-tight">
          {reason}
        </span>
      </div>
    );
  }
  const positive = uplift >= 0;
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        positive ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-600"
      }`}
    >
      {positive ? "+" : ""}
      {uplift.toFixed(1)}%
    </span>
  );
}

function LowBaselineWarning() {
  return (
    <span
      title="Baseline below €5,000 — this uplift % may not be statistically meaningful"
      className="ml-1 inline-flex items-center text-amber-500 cursor-help"
    >
      <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
        <path
          fillRule="evenodd"
          d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
          clipRule="evenodd"
        />
      </svg>
    </span>
  );
}

function ColHeader({ label, sortKey, currentKey, currentDir, onSort, tooltip }) {
  const active = currentKey === sortKey;
  return (
    <th
      className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700 whitespace-nowrap"
      onClick={() => onSort(sortKey)}
      title={tooltip}
    >
      {label}
      <span className={`ml-1 ${active ? "" : "text-gray-300"}`}>
        {active ? (currentDir === "asc" ? "↑" : "↓") : "↕"}
      </span>
    </th>
  );
}

function fmt(n) {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function duration(startDate, endDate) {
  const s = new Date(startDate);
  const e = new Date(endDate);
  if (isNaN(s) || isNaN(e) || e < s) return null;
  return Math.round((e - s) / 86400000) + 1;
}

export default function App() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [search, setSearch] = useState("");
  const [siteFilter, setSiteFilter] = useState("");
  const [gameFilter, setGameFilter] = useState("");
  const [upliftFilter, setUpliftFilter] = useState("all"); // "all" | "positive" | "negative"
  const [showUnmeasurable, setShowUnmeasurable] = useState(false);
  const [sortKey, setSortKey] = useState("uplift");
  const [sortDir, setSortDir] = useState("desc");

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/results", { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const sites = useMemo(
    () => [...new Map(data.map((r) => [r.site_id, r.site_name])).entries()]
      .sort((a, b) => a[1].localeCompare(b[1])),
    [data]
  );

  const games = useMemo(() => {
    const set = new Set();
    data.forEach((r) => {
      if (r.games && r.games !== "ALL") {
        r.games.split(";").forEach((g) => set.add(g.trim()));
      }
    });
    return [...set].sort();
  }, [data]);

  const filtered = useMemo(() => {
    let rows = data;
    if (!showUnmeasurable) rows = rows.filter((r) => r.measurable);
    if (siteFilter) rows = rows.filter((r) => r.site_id === siteFilter);
    if (gameFilter) rows = rows.filter((r) =>
      r.games === "ALL" || r.games.split(";").map((g) => g.trim()).includes(gameFilter)
    );
    if (upliftFilter === "positive") rows = rows.filter((r) => r.uplift !== null && r.uplift > 0);
    if (upliftFilter === "negative") rows = rows.filter((r) => r.uplift !== null && r.uplift < 0);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter((r) => r.promo_id.toLowerCase().includes(q));
    }
    return [...rows].sort((a, b) => {
      let av = sortKey === "_duration"
        ? duration(a.start_date, a.end_date)
        : sortKey === "_impact"
        ? (a.before !== null && a.during !== null ? a.during - a.before : null)
        : a[sortKey];
      let bv = sortKey === "_duration"
        ? duration(b.start_date, b.end_date)
        : sortKey === "_impact"
        ? (b.before !== null && b.during !== null ? b.during - b.before : null)
        : b[sortKey];
      const nullVal = sortDir === "asc" ? Infinity : -Infinity;
      if (av === null || av === undefined) av = nullVal;
      if (bv === null || bv === undefined) bv = nullVal;
      if (typeof av === "string") av = av.toLowerCase();
      if (typeof bv === "string") bv = bv.toLowerCase();
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
  }, [data, search, siteFilter, gameFilter, upliftFilter, showUnmeasurable, sortKey, sortDir]);

  function handleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "uplift" ? "desc" : "asc");
    }
  }

  function clearFilters() {
    setSearch("");
    setSiteFilter("");
    setGameFilter("");
    setUpliftFilter("all");
    setShowUnmeasurable(false);
  }

  const isFiltered = search || siteFilter || gameFilter || upliftFilter !== "all" || showUnmeasurable;

  const measurableCount = data.filter((r) => r.measurable).length;
  const positiveCount = data.filter((r) => r.uplift !== null && r.uplift > 0).length;
  const hiddenCount = data.filter((r) => !r.measurable).length;
  const avgUplift =
    measurableCount > 0
      ? data.filter((r) => r.measurable && r.uplift !== null).reduce((s, r) => s + r.uplift, 0) /
        measurableCount
      : null;

  const sortProps = { currentKey: sortKey, currentDir: sortDir, onSort: handleSort };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold text-gray-900">Promo Uplift Dashboard</h1>
              <p className="text-sm text-gray-400 mt-0.5">
                Uplift = (stakes during promo − same number of days before) ÷ before
              </p>
            </div>
            {!loading && !error && (
              <div className="flex gap-6 text-sm">
                <Stat label="Total promos" value={data.length} />
                <Stat label="Measurable" value={measurableCount} />
                <Stat label="Positive uplift" value={positiveCount} color="text-emerald-600" />
                <Stat
                  label="Avg uplift"
                  value={avgUplift !== null ? `${avgUplift > 0 ? "+" : ""}${avgUplift.toFixed(1)}%` : "—"}
                  color={avgUplift > 0 ? "text-emerald-600" : avgUplift < 0 ? "text-red-500" : "text-gray-400"}
                />
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {/* Filters */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm px-5 py-4 mb-5">
          <div className="flex flex-wrap items-end gap-4">
            {/* Promo ID search */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Promo ID</label>
              <input
                type="search"
                placeholder="e.g. P01"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-36 rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
              />
            </div>

            {/* Site dropdown */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Site</label>
              <select
                value={siteFilter}
                onChange={(e) => setSiteFilter(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-white"
              >
                <option value="">All sites</option>
                {sites.map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </select>
            </div>

            {/* Game dropdown */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Game</label>
              <select
                value={gameFilter}
                onChange={(e) => setGameFilter(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-white"
              >
                <option value="">All games</option>
                {games.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>

            {/* Uplift direction segmented control */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Uplift direction</label>
              <div className="inline-flex rounded-lg border border-gray-300 overflow-hidden text-sm shadow-sm">
                {[
                  { value: "all", label: "All" },
                  { value: "positive", label: "▲ Positive" },
                  { value: "negative", label: "▼ Negative" },
                ].map(({ value, label }) => (
                  <button
                    key={value}
                    onClick={() => setUpliftFilter(value)}
                    className={`px-3 py-2 border-r last:border-r-0 border-gray-300 transition-colors ${
                      upliftFilter === value
                        ? value === "positive"
                          ? "bg-emerald-500 text-white font-medium"
                          : value === "negative"
                          ? "bg-red-500 text-white font-medium"
                          : "bg-gray-700 text-white font-medium"
                        : "bg-white text-gray-600 hover:bg-gray-50"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Measurable toggle */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Measurability</label>
              <button
                onClick={() => setShowUnmeasurable((v) => !v)}
                className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm shadow-sm transition-colors ${
                  showUnmeasurable
                    ? "border-gray-400 bg-gray-100 text-gray-700 font-medium"
                    : "border-gray-300 bg-white text-gray-500 hover:bg-gray-50"
                }`}
              >
                <span className={`w-8 h-4 rounded-full relative transition-colors ${showUnmeasurable ? "bg-gray-500" : "bg-gray-200"}`}>
                  <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform ${showUnmeasurable ? "translate-x-4" : "translate-x-0.5"}`} />
                </span>
                Include N/A
              </button>
            </div>

            {/* Clear filters */}
            {isFiltered && (
              <button
                onClick={clearFilters}
                className="self-end mb-0.5 text-sm text-gray-400 hover:text-gray-600 underline whitespace-nowrap"
              >
                Clear all
              </button>
            )}
          </div>

          <div className="mt-3 text-xs text-gray-400">
            {filtered.length} of {data.length} promos shown
            {hiddenCount > 0 && !showUnmeasurable && (
              <span> · {hiddenCount} unmeasurable hidden</span>
            )}
          </div>
        </div>

        {loading && (
          <div className="py-20 text-center text-gray-400">Loading…</div>
        )}
        {error && (
          <div className="py-20 text-center text-red-500">
            Failed to load results: {error}
          </div>
        )}
        {!loading && !error && (
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  <ColHeader label="Promo" sortKey="promo_id" {...sortProps} />
                  <ColHeader label="Site" sortKey="site_name" {...sortProps} />
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Games
                  </th>
                  <ColHeader label="Days" sortKey="_duration" {...sortProps} tooltip="Number of days the promo ran" />
                  <ColHeader
                    label="Stakes Before (€)"
                    sortKey="before"
                    {...sortProps}
                    tooltip="Total stakes wagered in the same number of days immediately before the promo started"
                  />
                  <ColHeader
                    label="Stakes During (€)"
                    sortKey="during"
                    {...sortProps}
                    tooltip="Total stakes wagered during the promotion period"
                  />
                  <ColHeader
                    label="Impact (€)"
                    sortKey="_impact"
                    {...sortProps}
                    tooltip="Absolute change in stakes: During − Before"
                  />
                  <ColHeader
                    label="Uplift"
                    sortKey="uplift"
                    {...sortProps}
                    tooltip="(During − Before) ÷ Before × 100"
                  />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map((r) => {
                  const days = duration(r.start_date, r.end_date);
                  const impact =
                    r.before !== null && r.during !== null ? r.during - r.before : null;
                  const lowBaseline = r.measurable && r.before !== null && r.before < LOW_BASELINE_THRESHOLD;

                  return (
                    <tr
                      key={`${r.promo_id}-${r.site_id}`}
                      className="hover:bg-gray-50 transition-colors"
                    >
                      <td className="px-4 py-3 text-sm font-mono font-medium text-gray-900">
                        {r.promo_id}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700 whitespace-nowrap">
                        {r.site_name}
                      </td>
                      <td
                        className="px-4 py-3 text-sm text-gray-500 max-w-[160px] truncate"
                        title={r.games}
                      >
                        {r.games === "ALL" ? (
                          <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs font-medium text-blue-600">
                            ALL games
                          </span>
                        ) : (
                          r.games.split(";").join(", ")
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-center text-gray-500">
                        {days ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-sm text-right tabular-nums text-gray-700">
                        <span className="inline-flex items-center justify-end">
                          {fmt(r.before)}
                          {lowBaseline && <LowBaselineWarning />}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-right tabular-nums text-gray-700">
                        {fmt(r.during)}
                      </td>
                      <td className={`px-4 py-3 text-sm text-right tabular-nums font-medium ${
                        impact === null ? "text-gray-400" :
                        impact > 0 ? "text-emerald-600" : "text-red-500"
                      }`}>
                        {impact !== null
                          ? `${impact > 0 ? "+" : ""}${fmt(impact)}`
                          : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <UpliftBadge
                          uplift={r.uplift}
                          measurable={r.measurable}
                          reason={r.reason}
                        />
                      </td>
                    </tr>
                  );
                })}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-sm text-gray-400">
                      No promos match your filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value, color = "text-gray-900" }) {
  return (
    <div className="text-right">
      <div className={`text-lg font-bold ${color}`}>{value}</div>
      <div className="text-gray-400 text-xs">{label}</div>
    </div>
  );
}
