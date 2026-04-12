// API Configuration
const IS_LOCAL_FRONTEND = window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost";
const API_ORIGIN = IS_LOCAL_FRONTEND ? "http://127.0.0.1:8000" : window.location.origin;
const API_BASE = `${API_ORIGIN}/weather/final`;
const TRENDS_BASE = `${API_ORIGIN}/weather/trends`;
const TRENDS_MODEL_BASE = `${API_ORIGIN}/weather/trends/model`;
const OPENWEATHER_TODAY_BASE = `${API_ORIGIN}/weather/openweather/today`;
const URL_PARAMS = new URLSearchParams(window.location.search);
const SELECTED_LONG_MODEL = (
  window.__LONG_MODEL || URL_PARAMS.get("long_model") || "b"
).toLowerCase();
const SELECTED_TRENDS_MODE = (
  window.__TRENDS_MODE || URL_PARAMS.get("trends_mode") || "historical"
).toLowerCase();

// DOM Elements
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

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp) {
  if (!timestamp) return "—";
  try {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return "—";
  }
}

/**
 * Get day label for forecast
 */
function getDayLabel(offset) {
  if (offset === 0) return "TODAY";
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return d.toLocaleDateString("en-US", { weekday: "short" }).toUpperCase();
}

function normalizeHourlySeries(hourlyData, target = 24) {
  if (!Array.isArray(hourlyData) || hourlyData.length === 0) {
    return [];
  }

  if (hourlyData.length >= target) {
    return hourlyData.slice(0, target);
  }

  const srcTemps = hourlyData
    .map((entry) => Number(entry?.temp))
    .filter((v) => Number.isFinite(v));
  if (srcTemps.length === 0) {
    return [];
  }

  let startHour = new Date().getHours();
  const firstHourText = String(hourlyData[0]?.hour || "").slice(0, 2);
  const parsed = Number(firstHourText);
  if (Number.isFinite(parsed) && parsed >= 0 && parsed <= 23) {
    startHour = parsed;
  }

  const out = [];
  for (let i = 0; i < target; i += 1) {
    const pos = (i * (srcTemps.length - 1)) / (target - 1);
    const lo = Math.floor(pos);
    const hi = Math.min(srcTemps.length - 1, lo + 1);
    const w = pos - lo;
    const temp = (1 - w) * srcTemps[lo] + w * srcTemps[hi];
    out.push({
      hour: `${String((startHour + i) % 24).padStart(2, "0")}:00`,
      temp: Number(temp.toFixed(2)),
    });
  }
  return out;
}

function normalizeDailySeries(daily, target = 7) {
  const mean = Array.isArray(daily?.mean) ? daily.mean.map((v) => Number(v)) : [];
  const upper = Array.isArray(daily?.upper) ? daily.upper.map((v) => Number(v)) : [];
  const lower = Array.isArray(daily?.lower) ? daily.lower.map((v) => Number(v)) : [];

  if (mean.length === 0) {
    return { mean: [], upper: [], lower: [] };
  }

  while (mean.length < target) {
    const step = mean.length >= 2 ? (mean[mean.length - 1] - mean[mean.length - 2]) * 0.7 : 0;
    mean.push(Number((mean[mean.length - 1] + step).toFixed(2)));
  }

  while (upper.length < target) {
    upper.push(Number((mean[upper.length] + 1.5).toFixed(2)));
  }

  while (lower.length < target) {
    lower.push(Number((mean[lower.length] - 1.5).toFixed(2)));
  }

  return {
    mean: mean.slice(0, target),
    upper: upper.slice(0, target),
    lower: lower.slice(0, target),
  };
}

async function fetchTodayOpenWeatherSummary(city) {
  try {
    const url = `${OPENWEATHER_TODAY_BASE}/${encodeURIComponent(city)}`;
    const response = await fetch(url);
    if (!response.ok) {
      return null;
    }

    const payload = await response.json();
    const mean = Number(payload.mean);
    const upper = Number(payload.upper);
    const lower = Number(payload.lower);
    if (!Number.isFinite(mean) || !Number.isFinite(upper) || !Number.isFinite(lower)) {
      return null;
    }

    return {
      mean,
      upper,
      lower
    };
  } catch (error) {
    console.warn("OpenWeather today summary unavailable:", error);
    return null;
  }
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

function showComingSoonState(city, reason = "") {
  cityNameEl.textContent = city;
  timestampEl.textContent = "City forecast support is coming soon.";
  currentTempEl.textContent = "—";

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

/**
 * Load weather data for a city
 */
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
    
    // Update Meta Information
    cityNameEl.textContent = data.meta?.city || city;
    timestampEl.textContent = formatTimestamp(data.meta?.timestamp);
    
    // Update Current Temperature
    if (data.current?.temp !== undefined && data.current?.temp !== null) {
      currentTempEl.textContent = data.current.temp.toFixed(1);
    } else {
      currentTempEl.textContent = "—";
    }
    
    // Render 24-Hour Chart
    renderHourlyChart(data.hourly);

    // Prefer same-response OpenWeather summary for TODAY override; fallback to explicit endpoint.
    let todayOpenWeather = normalizeTodaySummary(data.today_openweather);
    if (!todayOpenWeather) {
      todayOpenWeather = await fetchTodayOpenWeatherSummary(data.meta?.city || city);
    }
    
    // Render 7-Day Forecast
    if (data.daily && data.daily.mean) {
      renderDailyForecast(data.daily, todayOpenWeather);
    }

    // Render Trends (read-only diagnostics)
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
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    renderSameDayHistory(data.same_day || []);
    renderMonthlyChart(data.monthly || []);
    renderYearlyChart(data.yearly || []);
  } catch (error) {
    console.error("Error loading trends data:", error);
  }
}

/**
 * Render 24-hour temperature chart using Chart.js
 */
function renderHourlyChart(hourlyData) {
  const normalizedHourly = normalizeHourlySeries(hourlyData, 24);

  if (!normalizedHourly || normalizedHourly.length === 0) {
    console.warn("No hourly data available");
    return;
  }
  
  // Extract labels and temperatures from API response
  const labels = normalizedHourly.map(entry => entry.hour || "—");
  const temperatures = normalizedHourly.map(entry => 
    entry.temp !== undefined && entry.temp !== null ? entry.temp : null
  );
  
  // Destroy existing chart if it exists
  if (chart) {
    chart.destroy();
  }
  
  // Create new chart
  const ctx = document.getElementById("hourlyChart");
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
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
        pointHoverBackgroundColor: "#667eea",
        pointHoverBorderColor: "white",
        pointHoverBorderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: function(context) {
              return `${context.parsed.y.toFixed(1)}°C`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            display: false
          },
          ticks: {
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 12
          }
        },
        y: {
          grid: {
            color: 'rgba(0, 0, 0, 0.05)'
          },
          ticks: {
            stepSize: 0.5,
            maxTicksLimit: 6,
            callback: function(value) {
              return value.toFixed(1) + "°C";
            }
          }
        }
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false
      }
    }
  });
}

/**
 * Render 7-day forecast cards
 */
function renderDailyForecast(daily, todayOverride = null) {
  const normalizedDaily = normalizeDailySeries(daily, 7);
  if (!normalizedDaily.mean.length) {
    dailyGrid.innerHTML = "";
    return;
  }

  dailyGrid.innerHTML = "";
  for (let i = 0; i < normalizedDaily.mean.length; i++) {
    const meanValue = (i === 0 && todayOverride && Number.isFinite(todayOverride.mean))
      ? Number(todayOverride.mean)
      : Number(normalizedDaily.mean[i]);
    const upperValue = (i === 0 && todayOverride && Number.isFinite(todayOverride.upper))
      ? Number(todayOverride.upper)
      : Number(normalizedDaily.upper[i]);
    const lowerValue = (i === 0 && todayOverride && Number.isFinite(todayOverride.lower))
      ? Number(todayOverride.lower)
      : Number(normalizedDaily.lower[i]);

    const card = document.createElement("div");
    card.className = "day-card";
    card.innerHTML = `
      <div class="day-name">${getDayLabel(i)}</div>
      <div class="day-temp">${meanValue.toFixed(1)}°C</div>
      <div class="day-range">
        H: ${upperValue.toFixed(1)}°<br>
        L: ${lowerValue.toFixed(1)}°
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
    const year = item.year ?? "—";
    const temp = item.avg_temp !== undefined && item.avg_temp !== null
      ? Number(item.avg_temp).toFixed(1)
      : "—";
    card.innerHTML = `
      <div class="same-day-year">${year}</div>
      <div class="same-day-temp">${temp}°C</div>
    `;
    sameDayListEl.appendChild(card);
  });
}

function renderMonthlyChart(items) {
  const labels = items.map((item) => item.month);
  const temps = items.map((item) => Number(item.avg_temp));

  if (monthlyChart) {
    monthlyChart.destroy();
  }

  monthlyChart = new Chart(monthlyChartEl, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Monthly Avg",
        data: temps,
        borderColor: "#667eea",
        backgroundColor: "rgba(102, 126, 234, 0.1)",
        borderWidth: 2,
        tension: 0.3,
        fill: true,
        pointRadius: 2,
        pointHoverRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            callback: (value, index) => {
              const monthIndex = Number(labels[index]);
              return Number.isFinite(monthIndex)
                ? new Date(2000, monthIndex - 1, 1).toLocaleString("en-US", { month: "short" })
                : labels[index];
            }
          }
        },
        y: {
          grid: { color: "rgba(0, 0, 0, 0.05)" },
          ticks: {
            callback: (value) => `${Number(value).toFixed(1)}°C`
          }
        }
      }
    }
  });
}

function renderYearlyChart(items) {
  const labels = items.map((item) => item.year);
  const temps = items.map((item) => Number(item.avg_temp));

  if (yearlyChart) {
    yearlyChart.destroy();
  }

  yearlyChart = new Chart(yearlyChartEl, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Yearly Avg",
        data: temps,
        borderColor: "#4b5bd4",
        backgroundColor: "rgba(75, 91, 212, 0.1)",
        borderWidth: 2,
        tension: 0.3,
        fill: true,
        pointRadius: 2,
        pointHoverRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { grid: { display: false } },
        y: {
          grid: { color: "rgba(0, 0, 0, 0.05)" },
          ticks: {
            callback: (value) => `${Number(value).toFixed(1)}°C`
          }
        }
      }
    }
  });
}

/**
 * Initialize the app
 */
function init() {
  // Load initial city
  loadWeather(citySelect.value);
  
  // City selector change handler
  citySelect.addEventListener("change", () => {
    loadWeather(citySelect.value);
  });
}

// Start the app when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
