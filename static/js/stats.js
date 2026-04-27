'use strict';

Chart.defaults.color          = '#7070a0';
Chart.defaults.borderColor    = '#2a2a40';
Chart.defaults.font.family    = 'Segoe UI, system-ui, sans-serif';
Chart.defaults.font.size      = 12;

const PALETTE = ['#e63946', '#ff6b35', '#f4a261', '#3498db', '#9b59b6', '#2ecc71', '#1abc9c'];

// Statuts
new Chart(document.getElementById('chartStatus'), {
  type: 'doughnut',
  data: {
    labels: ['Maîtrisés', 'En apprentissage', 'En pause'],
    datasets: [{
      data: [MASTERED, LEARNING, ON_HOLD],
      backgroundColor: ['#2ecc71cc', '#f39c12cc', '#7f8c8dcc'],
      borderColor:     ['#2ecc71',   '#f39c12',   '#7f8c8d'],
      borderWidth: 2,
    }],
  },
  options: {
    plugins: { legend: { position: 'bottom' } },
    cutout: '65%',
  },
});

// Styles
new Chart(document.getElementById('chartStyle'), {
  type: 'bar',
  data: {
    labels:   STYLE_DATA.map(d => d.label),
    datasets: [{
      label: 'Morceaux',
      data:  STYLE_DATA.map(d => d.value),
      backgroundColor: PALETTE,
      borderRadius: 6,
    }],
  },
  options: {
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, ticks: { stepSize: 1 } },
      x: { grid: { display: false } },
    },
  },
});

// Sessions journalières (30 jours)
(function () {
  // Build last-30-days labels
  const labels = [], values = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    labels.push(i === 0 ? "Auj." : key.slice(5).replace('-', '/'));
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
        backgroundColor: 'rgba(230,57,70,.12)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor: '#e63946',
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
        x: {
          grid: { display: false },
          ticks: {
            maxTicksLimit: 10,
            maxRotation: 0,
          },
        },
      },
    },
  });
})();

// Difficulté
new Chart(document.getElementById('chartDiff'), {
  type: 'bar',
  data: {
    labels: DIFF_DATA.map(d => '★'.repeat(parseInt(d.label))),
    datasets: [{
      label: 'Morceaux',
      data:  DIFF_DATA.map(d => d.value),
      backgroundColor: ['#2ecc71cc', '#f4a261cc', '#f39c12cc', '#e67e22cc', '#e63946cc'],
      borderRadius: 6,
    }],
  },
  options: {
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, ticks: { stepSize: 1 } },
      x: { grid: { display: false } },
    },
  },
});
