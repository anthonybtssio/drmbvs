'use strict';

(function () {
  // Rating picker
  const stars    = document.querySelectorAll('.rating-star');
  const ratingEl = document.getElementById('logRating');

  stars.forEach(star => {
    star.addEventListener('click', () => {
      const val = parseInt(star.dataset.val);
      ratingEl.value = val;
      stars.forEach(s => s.classList.toggle('active', parseInt(s.dataset.val) <= val));
    });
  });

  // Quick log button (pre-fills song select)
  const quickBtn = document.getElementById('quickLogBtn');
  if (quickBtn) {
    quickBtn.addEventListener('click', () => {
      const songId = quickBtn.dataset.songId;
      const select = document.getElementById('logSongId');
      if (select) select.value = songId;
      document.getElementById('logForm')?.scrollIntoView({ behavior: 'smooth' });
    });
  }

  // Log form submission
  const form       = document.getElementById('logForm');
  const successMsg = document.getElementById('logSuccess');

  form?.addEventListener('submit', async e => {
    e.preventDefault();

    const songId = parseInt(document.getElementById('logSongId').value);
    if (!songId) return;

    const payload = {
      song_id:          songId,
      duration_minutes: parseInt(document.getElementById('logDuration').value) || null,
      rating:           parseInt(ratingEl.value) || null,
      notes:            document.getElementById('logNotes').value.trim() || null,
    };

    try {
      const res = await fetch('/api/practice/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        form.classList.add('hidden');
        successMsg.classList.remove('hidden');
        setTimeout(() => location.reload(), 1800);
      }
    } catch (err) {
      console.error(err);
    }
  });
})();
