const WIDTH = 640;

function seriesOf(el) {
  try {
    return JSON.parse(el.dataset.series || "[]");
  } catch (error) {
    return [];
  }
}

function empty(el, message) {
  el.innerHTML = `<p class="muted">${message}</p>`;
}

function frame(el, height, margin, label) {
  el.innerHTML = "";
  const svg = d3
    .select(el)
    .append("svg")
    .attr("viewBox", `0 0 ${WIDTH} ${height}`)
    .attr("class", "chart-svg")
    .attr("role", "img")
    .attr("aria-label", label);
  return {
    svg,
    g: svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`),
    innerW: WIDTH - margin.left - margin.right,
    innerH: height - margin.top - margin.bottom,
  };
}

function drawHorizontalGrid(g, scale, width, tickCount) {
  const grid = g
    .append("g")
    .attr("class", "grid")
    .call(d3.axisLeft(scale).ticks(tickCount).tickSize(-width).tickFormat(""));
  grid.select(".domain").remove();
  grid
    .selectAll(".tick line")
    .attr("stroke-dasharray", "3 4")
    .attr("stroke-opacity", 0.4)
    .attr("stroke-width", 0.6);
}

function thinAxes(g) {
  g.selectAll(".axis path, .axis line").attr("stroke-width", 0.6);
}

function displayDate(isoDate, includeYear = true) {
  const [year, month, day] = isoDate.split("-").map(Number);
  const options = { day: "2-digit", month: "2-digit", timeZone: "UTC" };
  if (includeYear) options.year = "numeric";
  return new Intl.DateTimeFormat(document.documentElement.lang || "en-AU", options)
    .formatToParts(new Date(Date.UTC(year, month - 1, day)))
    .filter((part) => ["day", "month", "year"].includes(part.type))
    .map((part) => part.value)
    .join("-");
}

function drawWeeklyRowSeparators(g, series, scale, width) {
  const gap = (scale.step() - scale.bandwidth()) / 2;
  g.append("g")
    .attr("class", "grid row-grid")
    .selectAll("line")
    .data(series.slice(0, -1))
    .enter()
    .append("line")
    .attr("x1", 0)
    .attr("x2", width)
    .attr("y1", (d) => scale(d.label) + scale.bandwidth() + gap)
    .attr("y2", (d) => scale(d.label) + scale.bandwidth() + gap)
    .attr("stroke-dasharray", "3 4")
    .attr("stroke-opacity", 0.4)
    .attr("stroke-width", 0.6);
}

function renderDaily(el) {
  const series = seriesOf(el);
  if (!series.some((d) => d.value !== null)) {
    return empty(el, "No weighings in the last 7 days.");
  }

  const margin = { top: 24, right: 16, bottom: 36, left: 48 };
  const { g, innerW, innerH } = frame(el, 260, margin, "Weight by day, last 7 days");

  const values = series.filter((d) => d.value !== null).map((d) => d.value);
  const x = d3.scaleBand().domain(series.map((d) => d.date)).range([0, innerW]).padding(0.25);
  const y = d3.scaleLinear().domain([Math.min(...values) - 1, Math.max(...values) + 1]).range([innerH, 0]).nice();

  drawHorizontalGrid(g, y, innerW, 5);
  g.append("g").attr("class", "axis").attr("transform", `translate(0,${innerH})`)
    .call(d3.axisBottom(x).tickFormat((d) => displayDate(d, false)));
  g.append("g").attr("class", "axis").call(d3.axisLeft(y));
  thinAxes(g);
  g.append("text").attr("class", "axis-label").attr("x", 0).attr("y", -12).text("kg");

  const bar = g.selectAll(".bar").data(series).enter().append("g");

  bar.append("rect")
    .attr("class", "bar")
    .attr("x", (d) => x(d.date))
    .attr("y", (d) => (d.value === null ? innerH - 2 : y(d.value)))
    .attr("width", x.bandwidth())
    .attr("height", (d) => (d.value === null ? 2 : innerH - y(d.value)))
    .classed("missing", (d) => d.value === null)
    .append("title")
    .text((d) => `${displayDate(d.date)}: ${d.value === null ? "no measurement" : `${d.value} kg (${d.count} measurement${d.count > 1 ? "s" : ""})`}`);

  bar.append("text")
    .attr("class", "value")
    .attr("x", (d) => x(d.date) + x.bandwidth() / 2)
    .attr("y", (d) => (d.value === null ? innerH - 8 : y(d.value) - 8))
    .attr("text-anchor", "middle")
    .text((d) => (d.value === null ? "-" : d.value.toFixed(1)));
}

function renderWeekly(el) {
  const series = seriesOf(el);
  if (!series.some((d) => d.mean !== null)) {
    return empty(el, "No weighings in the last 8 weeks.");
  }

  const margin = { top: 24, right: 28, bottom: 40, left: 84 };
  const { g, innerW, innerH } = frame(el, 320, margin, "Weekly mean weight, last 8 weeks");

  const present = series.filter((d) => d.mean !== null);
  const low = Math.min(...present.map((d) => d.mean - (d.std || 0)));
  const high = Math.max(...present.map((d) => d.mean + (d.std || 0)));

  const y = d3.scaleBand().domain(series.map((d) => d.label)).range([0, innerH]).padding(0.35);
  const x = d3.scaleLinear().domain([low - 0.5, high + 0.5]).range([0, innerW]).nice();

  g.append("g").attr("class", "axis").call(d3.axisBottom(x));
  g.append("g").attr("class", "axis").call(d3.axisLeft(y));
  thinAxes(g);
  drawWeeklyRowSeparators(g, series, y, innerW);
  g.append("text").attr("class", "axis-label").attr("x", 0).attr("y", -12).text("kg");

  const bar = g.selectAll(".week").data(series).enter().append("g");

  bar.append("rect")
    .attr("class", "bar")
    .attr("x", 0)
    .attr("y", (d) => y(d.label))
    .attr("width", (d) => (d.mean === null ? 0 : x(d.mean)))
    .attr("height", y.bandwidth())
    .classed("missing", (d) => d.mean === null)
    .append("title")
    .text((d) => `${d.label}: mean ${d.mean ?? "-"} kg, std ${d.std ?? "-"} kg, ${d.count} measurement(s)`);

  const err = bar.filter((d) => d.std !== null);
  const mid = (d) => y(d.label) + y.bandwidth() / 2;

  err.append("line")
    .attr("class", "error-bar")
    .attr("x1", (d) => x(d.mean - d.std))
    .attr("x2", (d) => x(d.mean + d.std))
    .attr("y1", mid)
    .attr("y2", mid);

  [-1, 1].forEach((sign) => {
    err.append("line")
      .attr("class", "error-bar")
      .attr("x1", (d) => x(d.mean + sign * d.std))
      .attr("x2", (d) => x(d.mean + sign * d.std))
      .attr("y1", (d) => mid(d) - y.bandwidth() / 4)
      .attr("y2", (d) => mid(d) + y.bandwidth() / 4);
  });

  bar.append("text")
    .attr("class", "value")
    .attr("x", (d) => (d.mean === null ? 4 : x(d.mean) + 6))
    .attr("y", (d) => y(d.label) + y.bandwidth() / 2 + 4)
    .text((d) => (d.mean === null ? "no data" : d.mean.toFixed(1)));
}

const RENDERERS = { daily: renderDaily, weekly: renderWeekly };

function render(el) {
  const renderer = RENDERERS[el.dataset.chart];
  if (!renderer) return;
  el.dataset.rendered = "1";
  renderer(el);
}

function renderAll(root) {
  (root || document).querySelectorAll("[data-chart]").forEach((el) => {
    if (el.dataset.rendered !== "1") render(el);
  });
}

document.addEventListener("DOMContentLoaded", () => renderAll(document));
document.addEventListener("htmx:afterSettle", (event) => {
  const target = event.detail.target;
  if (target && target.querySelectorAll) renderAll(target);
  if (target && target.dataset && target.dataset.chart) render(target);
});
