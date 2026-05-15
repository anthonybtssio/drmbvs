'use strict';

/* ── Chart.js global defaults ── */
Chart.defaults.color       = '#6060a0';
Chart.defaults.borderColor = '#252538';
Chart.defaults.font.family = 'Inter, Segoe UI, system-ui, sans-serif';
Chart.defaults.font.size   = 12;

const PALETTE = ['#e63946', '#ff6b35', '#f4a261', '#3498db', '#9b59b6', '#2ecc71', '#1abc9c'];

const STYLE_COLORS = {
  'Rock':  { bg: 'rgba(230,57,70,.7)',    border: '#e63946' },
  'Metal': { bg: 'rgba(144,144,192,.65)', border: '#9090c0' },
  'Pop':   { bg: 'rgba(216,112,176,.65)', border: '#d870b0' },
  'Jazz':  { bg: 'rgba(52,152,219,.65)',  border: '#3498db' },
  'Funk':  { bg: 'rgba(255,140,66,.7)',   border: '#ff8c42' },
  'Autre': { bg: 'rgba(26,188,156,.65)',  border: '#1abc9c' },
};

/* ── Statuts (doughnut) ── */
new Chart(document.getElementById('chartStatus'), {
  type: 'doughnut',
  data: {
    labels: typeof DOUGHNUT_LABELS !== 'undefined' ? DOUGHNUT_LABELS : ['Maîtrisés', 'En apprentissage', 'En pause'],
    datasets: [{
      data: [MASTERED, LEARNING, ON_HOLD],
      backgroundColor: ['rgba(46,204,113,.75)', 'rgba(243,156,18,.75)', 'rgba(127,140,141,.5)'],
      borderColor:     ['#2ecc71', '#f39c12', '#7f8c8d'],
      borderWidth: 2,
      hoverOffset: 8,
    }],
  },
  options: {
    plugins: {
      legend: { position: 'bottom', labels: { padding: 16, font: { size: 12 } } },
    },
    cutout: '68%',
  },
});

/* ── Styles (bar) ── */
(function () {
  const colors = STYLE_DATA.map(d => (STYLE_COLORS[d.label] || { bg: 'rgba(255,107,53,.7)', border: '#ff6b35' }));
  new Chart(document.getElementById('chartStyle'), {
    type: 'bar',
    data: {
      labels: STYLE_DATA.map(d => d.label),
      datasets: [{
        label: 'Morceaux',
        data:  STYLE_DATA.map(d => d.value),
        backgroundColor: colors.map(c => c.bg),
        borderColor:     colors.map(c => c.border),
        borderWidth: 2,
        borderRadius: 7,
        borderSkipped: false,
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 } },
        x: { grid: { display: false } },
      },
    },
  });
})();

/* ── Sessions journalières (line) ── */
(function () {
  const labels = [], values = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    labels.push(i === 0 ? 'Auj.' : (i % 7 === 0 ? key.slice(5).replace('-', '/') : key.slice(8)));
    values.push(DAILY_DATA[key] || 0);
  }

  new Chart(document.getElementById('chartDaily'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Sessions',
        data: values,
        borderColor: '#e63946',
        backgroundColor: function(ctx) {
          const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, 200);
          g.addColorStop(0, 'rgba(230,57,70,.3)');
          g.addColorStop(1, 'rgba(230,57,70,0)');
          return g;
        },
        fill: true,
        tension: 0.42,
        pointRadius: 3,
        pointHoverRadius: 6,
        pointBackgroundColor: '#e63946',
        pointBorderColor: 'rgba(0,0,0,.5)',
        pointBorderWidth: 1,
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 } },
        x: {
          grid: { display: false },
          ticks: { maxTicksLimit: 10, maxRotation: 0 },
        },
      },
    },
  });
})();

/* ── Difficulté (bar) ── */
new Chart(document.getElementById('chartDiff'), {
  type: 'bar',
  data: {
    labels: DIFF_DATA.map(d => '★'.repeat(parseInt(d.label))),
    datasets: [{
      label: 'Morceaux',
      data:  DIFF_DATA.map(d => d.value),
      backgroundColor: [
        'rgba(46,204,113,.7)',
        'rgba(244,162,97,.7)',
        'rgba(243,156,18,.7)',
        'rgba(230,126,34,.7)',
        'rgba(230,57,70,.7)',
      ],
      borderColor: ['#2ecc71', '#f4a261', '#f39c12', '#e67e22', '#e63946'],
      borderWidth: 2,
      borderRadius: 7,
      borderSkipped: false,
    }],
  },
  options: {
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 } },
      x: { grid: { display: false } },
    },
  },
});

/* ── Animated counters on stat cards ── */
document.querySelectorAll('.stat-value[data-count]').forEach(el => {
  const target = parseInt(el.dataset.count);
  if (!target || target === 0) return;
  let current = 0;
  const step  = Math.max(1, Math.ceil(target / 40));
  const timer = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = current;
    if (current >= target) clearInterval(timer);
  }, 30);
});
