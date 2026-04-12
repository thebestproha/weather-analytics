const API_BASE = "/weather/final";
const TRENDS_BASE = "/weather/trends";
const TRENDS_MODEL_BASE = "/weather/trends/model";
const OPENWEATHER_TODAY_BASE = "/weather/openweather/today";

const URL_PARAMS = new URLSearchParams(window.location.search);
const SELECTED_LONG_MODEL = (
  window.__LONG_MODEL || URL_PARAMS.get("long_model") || "b"
).toLowerCase();
const SELECTED_TRENDS_MODE = (
  window.__TRENDS_MODE || URL_PARAMS.get("trends_mode") || "historical"
).toLowerCase();

const citySelect = document.getElementById("citySelect");
const cityNameEl = document.getElementById("cityName");
const timestampEl = document.getElementById("timestamp");
const currentTempEl = document.getElementById("currentTemp");
const dailyGrid = document.getElementById("dailyGrid");
const sameDayListEl = document.getElementById("sameDayList");
const monthlyChartEl = document.getElementById("monthlyChart");
const yearlyChartEl = document.getElementById("yearlyChart");

let chart = null;
let monthlyChart = null;
let yearlyChart = null;

function formatTimestamp(timestamp) {
  if (!timestamp) return "-";
  try {
    const date = new Date(timestamp);
    return date.toLocaleString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch (_e) {
    return "-";
  }
}

function getDayLabel(offset) {
  if (offset === 0) return "TODAY";
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return d.toLocaleDateString("en-US", { weekday: "short" }).toUpperCase();
}

function normalizeTodaySummary(payload) {
  if (!payload) return null;
  const mean = Number(payload.mean);
  const upper = Number(payload.upper);
  const lower = Number(payload.lower);
  if (!Number.isFinite(mean) || !Number.isFinite(upper) || !Number.isFinite(lower)) {
    return null;
  }
  return { mean, upper, lower };
}

async function fetchTodayOpenWeatherSummary(city) {
  try {
    const url = `${OPENWEATHER_TODAY_BASE}/${encodeURIComponent(city)}`;
    const response = await fetch(url);
    if (!response.ok) return null;

    const payload = await response.json();
    return normalizeTodaySummary(payload);
  } catch (_error) {
    return null;
  }
}

function clearCharts() {
  if (chart) {
    chart.destroy();
    chart = null;
  }
  if (monthlyChart) {
    monthlyChart.destroy();
    monthlyChart = null;
  }
  if (yearlyChart) {
    yearlyChart.destroy();
    yearlyChart = null;
  }
}

function showComingSoonState(city, reason = "") {
  cityNameEl.textContent = city;
  timestampEl.textContent = "City forecast support is coming soon.";
  currentTempEl.textContent = "-";

  clearCharts();

  dailyGrid.innerHTML = `
    <div style="grid-column: 1 / -1; border: 1px dashed #cdd6ee; border-radius: 12px; padding: 14px; color: #5b6688; background: #f7f9ff; font-weight: 600;">
      ${city}: forecast models are coming soon.
    </div>
  `;
  sameDayListEl.innerHTML = "<div style=\"color:#777;\">Coming soon</div>";

  if (reason) {
    console.info(`Coming soon for ${city}: ${reason}`);
  }
}

async function loadWeather(city) {
  try {
    const response = await fetch(
      `${API_BASE}/${encodeURIComponent(city)}?long_model=${encodeURIComponent(SELECTED_LONG_MODEL)}`
    );

    if (!response.ok) {
      showComingSoonState(city, `HTTP ${response.status}`);
      return;
    }

    const data = await response.json();

    cityNameEl.textContent = data.meta?.city || city;
    timestampEl.textContent = formatTimestamp(data.meta?.timestamp);

    if (data.current?.temp !== undefined && data.current?.temp !== null) {
      currentTempEl.textContent = Number(data.current.temp).toFixed(1);
    } else {
      currentTempEl.textContent = "-";
    }

    renderHourlyChart(data.hourly);

    let todayOpenWeather = normalizeTodaySummary(data.today_openweather);
    if (!todayOpenWeather) {
      todayOpenWeather = await fetchTodayOpenWeatherSummary(data.meta?.city || city);
    }

    if (data.daily && data.daily.mean) {
      renderDailyForecast(data.daily, todayOpenWeather);
    }

    loadTrends(city);
  } catch (error) {
    console.error("Error loading weather data:", error);
    showComingSoonState(city, error?.message || "request_failed");
  }
}

async function loadTrends(city) {
  try {
    const trendsUrl = SELECTED_TRENDS_MODE === "model"
      ? `${TRENDS_MODEL_BASE}/${encodeURIComponent(city)}?long_model=${encodeURIComponent(SELECTED_LONG_MODEL)}`
      : `${TRENDS_BASE}/${encodeURIComponent(city)}`;

    const response = await fetch(trendsUrl);
    if (!response.ok) {
      return;
    }

    const data = await response.json();
    renderSameDayHistory(data.same_day || []);
    renderMonthlyChart(data.monthly || []);
    renderYearlyChart(data.yearly || []);
  } catch (_error) {
    // Non-blocking trends panel.
  }
}

function renderHourlyChart(hourlyData) {
  if (!hourlyData || !Array.isArray(hourlyData) || hourlyData.length === 0) {
    return;
  }

  const labels = hourlyData.map((entry) => entry.hour || "-");
  const temperatures = hourlyData.map((entry) =>
    entry.temp !== undefined && entry.temp !== null ? entry.temp : null
  );

  if (chart) {
    chart.destroy();
  }

  const ctx = document.getElementById("hourlyChart");
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Temperature",
        data: temperatures,
        borderColor: "#667eea",
        backgroundColor: "rgba(102, 126, 234, 0.1)",
        borderWidth: 3,
        tension: 0.4,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 12,
          },
        },
        y: {
          grid: { color: "rgba(0, 0, 0, 0.05)" },
          ticks: {
            maxTicksLimit: 6,
            callback: function(value) {
              return Number(value).toFixed(1) + "degC";
            },
          },
        },
      },
    },
  });
}

function renderDailyForecast(daily, todayOverride = null) {
  dailyGrid.innerHTML = "";
  for (let i = 0; i < daily.mean.length; i += 1) {
    const meanValue = (i === 0 && todayOverride && Number.isFinite(todayOverride.mean))
      ? Number(todayOverride.mean)
      : Number(daily.mean[i]);
    const upperValue = (i === 0 && todayOverride && Number.isFinite(todayOverride.upper))
      ? Number(todayOverride.upper)
      : Number(daily.upper[i]);
    const lowerValue = (i === 0 && todayOverride && Number.isFinite(todayOverride.lower))
      ? Number(todayOverride.lower)
      : Number(daily.lower[i]);

    const card = document.createElement("div");
    card.className = "day-card";
    card.innerHTML = `
      <div class="day-name">${getDayLabel(i)}</div>
      <div class="day-temp">${meanValue.toFixed(1)}degC</div>
      <div class="day-range">
        H: ${upperValue.toFixed(1)}deg<br>
        L: ${lowerValue.toFixed(1)}deg
      </div>
    `;
    dailyGrid.appendChild(card);
  }
}

function renderSameDayHistory(items) {
  sameDayListEl.innerHTML = "";
  if (!Array.isArray(items) || items.length === 0) {
    sameDayListEl.innerHTML = "<div style=\"color:#777;\">No history available</div>";
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "same-day-item";
    const year = item.year ?? "-";
    const temp = item.avg_temp !== undefined && item.avg_temp !== null
      ? Number(item.avg_temp).toFixed(1)
      : "-";
    card.innerHTML = `
      <div class="same-day-year">${year}</div>
      <div class="same-day-temp">${temp}degC</div>
    `;
    sameDayListEl.appendChild(card);
  });
}

function renderMonthlyChart(items) {
  if (!monthlyChartEl) return;

  const labels = items.map((item) => item.month);
  const temps = items.map((item) => Number(item.avg_temp));

  if (monthlyChart) {
    monthlyChart.destroy();
  }

  monthlyChart = new Chart(monthlyChartEl, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Monthly Avg",
        data: temps,
        borderColor: "#667eea",
        backgroundColor: "rgba(102, 126, 234, 0.1)",
        borderWidth: 2,
        tension: 0.3,
        fill: true,
        pointRadius: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
    },
  });
}

function renderYearlyChart(items) {
  if (!yearlyChartEl) return;

  const labels = items.map((item) => item.year);
  const temps = items.map((item) => Number(item.avg_temp));

  if (yearlyChart) {
    yearlyChart.destroy();
  }

  yearlyChart = new Chart(yearlyChartEl, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Yearly Avg",
        data: temps,
        borderColor: "#4b5bd4",
        backgroundColor: "rgba(75, 91, 212, 0.1)",
        borderWidth: 2,
        tension: 0.3,
        fill: true,
        pointRadius: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
    },
  });
}

function init() {
  loadWeather(citySelect.value);
  citySelect.addEventListener("change", () => {
    loadWeather(citySelect.value);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
