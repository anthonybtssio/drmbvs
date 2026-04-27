'use strict';

(function () {
  const grid       = document.getElementById('songGrid');
  const emptyState = document.getElementById('emptyState');
  const searchEl   = document.getElementById('search');
  const bpmMin     = document.getElementById('bpmMin');
  const bpmMax     = document.getElementById('bpmMax');

  let activeStyle  = '';
  let activeDiff   = '';
  let activeStatus = '';

  // Chip groups
  function setupChips(groupId, onSelect) {
    const group = document.getElementById(groupId);
    if (!group) return;
    group.querySelectorAll('.chip').forEach(chip => {
      chip.addEventListener('click', () => {
        group.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        onSelect(chip.dataset[groupId === 'styleChips' ? 'style' :
                              groupId === 'diffChips'  ? 'diff'  : 'status']);
        filterSongs();
      });
    });
  }

  setupChips('styleChips',  v => { activeStyle  = v; });
  setupChips('diffChips',   v => { activeDiff   = v; });
  setupChips('statusChips', v => { activeStatus = v; });

  searchEl.addEventListener('input', filterSongs);
  bpmMin.addEventListener('input', filterSongs);
  bpmMax.addEventListener('input', filterSongs);

  function filterSongs() {
    const q    = searchEl.value.toLowerCase().trim();
    const bMin = parseInt(bpmMin.value) || 0;
    const bMax = parseInt(bpmMax.value) || 9999;
    let visible = 0;

    grid.querySelectorAll('.song-card').forEach(card => {
      const matchQ      = !q || card.dataset.title.includes(q) || card.dataset.artist.includes(q);
      const matchStyle  = !activeStyle  || card.dataset.style  === activeStyle;
      const matchDiff   = !activeDiff   || card.dataset.diff   === activeDiff;
      const matchStatus = !activeStatus || card.dataset.status === activeStatus;
      const bpm         = parseInt(card.dataset.bpm) || 0;
      const matchBpm    = bpm === 0 || (bpm >= bMin && bpm <= bMax);
      const show        = matchQ && matchStyle && matchDiff && matchStatus && matchBpm;

      card.classList.toggle('hidden', !show);
      if (show) visible++;
    });

    emptyState.classList.toggle('hidden', visible > 0);
  }

  // Reset buttons
  function resetAll() {
    searchEl.value = '';
    bpmMin.value   = '';
    bpmMax.value   = '';
    activeStyle = activeDiff = activeStatus = '';
    document.querySelectorAll('.chip-group .chip').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.chip-group .chip[data-style=""],' +
                               '.chip-group .chip[data-diff=""],' +
                               '.chip-group .chip[data-status=""]').forEach(c => c.classList.add('active'));
    filterSongs();
  }

  document.getElementById('resetFilters')?.addEventListener('click', resetAll);
  document.getElementById('resetFilters2')?.addEventListener('click', resetAll);
})();
