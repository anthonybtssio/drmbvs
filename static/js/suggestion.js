/* ── suggestion.js ── likes + wishlist via localStorage ── */

const LIKES_KEY    = 'drmbvs_likes';
const WISHLIST_KEY = 'drmbvs_wishlist';

/* ── helpers ── */
function getLikes()    { return JSON.parse(localStorage.getItem(LIKES_KEY)    || '{}'); }
function getWishlist() { return JSON.parse(localStorage.getItem(WISHLIST_KEY) || '[]'); }
function saveLikes(d)  { localStorage.setItem(LIKES_KEY,    JSON.stringify(d)); }
function saveWishlist(d){ localStorage.setItem(WISHLIST_KEY, JSON.stringify(d)); }

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add('hidden'), 2400);
}

/* ── restore likes on load ── */
function restoreLikes() {
  const likes = getLikes();
  document.querySelectorAll('.like-btn').forEach(btn => {
    const id = btn.dataset.id;
    const count = likes[id] || 0;
    const icon  = btn.querySelector('.like-icon');
    const cntEl = btn.querySelector('.like-count');
    cntEl.textContent = count;
    if (count > 0) { icon.textContent = '❤️'; btn.classList.add('liked'); }
    else           { icon.textContent = '🤍'; btn.classList.remove('liked'); }
  });
}

/* ── like toggle ── */
document.querySelectorAll('.like-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const id    = btn.dataset.id;
    const likes = getLikes();
    const icon  = btn.querySelector('.like-icon');
    const cntEl = btn.querySelector('.like-count');

    if (likes[id]) {
      delete likes[id];
      icon.textContent = '🤍';
      btn.classList.remove('liked');
      cntEl.textContent = 0;
    } else {
      likes[id] = 1;
      icon.textContent = '❤️';
      btn.classList.add('liked');
      cntEl.textContent = 1;
      /* small bounce */
      btn.style.transform = 'scale(1.25)';
      setTimeout(() => btn.style.transform = '', 180);
    }
    saveLikes(likes);
  });
});

/* ── wishlist: add/remove ── */
function renderWishlist() {
  const list    = getWishlist();
  const panel   = document.getElementById('wishlistItems');
  const countEl = document.getElementById('wishlistCount');
  const clearBtn= document.getElementById('clearWishlist');

  countEl.textContent = list.length;
  clearBtn.classList.toggle('hidden', list.length === 0);

  if (list.length === 0) {
    panel.innerHTML = '<p class="text-muted fs-xs" style="padding:.5rem 0;">Aucun morceau choisi.<br>Clique sur <strong>Apprendre</strong>.</p>';
    return;
  }

  panel.innerHTML = list.map(song => `
    <div class="wishlist-item" data-id="${song.id}">
      <div>
        <div class="wishlist-item-title">${song.title}</div>
        <div class="wishlist-item-artist">${song.artist}</div>
      </div>
      <button class="wishlist-item-remove" title="Retirer" data-id="${song.id}">✕</button>
    </div>
  `).join('');

  panel.querySelectorAll('.wishlist-item-remove').forEach(btn => {
    btn.addEventListener('click', () => removeFromWishlist(btn.dataset.id));
  });
}

function addToWishlist(id, title, artist, style) {
  const list = getWishlist();
  if (list.find(s => s.id === id)) return;
  list.push({ id, title, artist, style });
  saveWishlist(list);
  renderWishlist();
}

function removeFromWishlist(id) {
  const list = getWishlist().filter(s => s.id !== id);
  saveWishlist(list);
  renderWishlist();
  /* reset learn btn */
  const btn = document.querySelector(`.learn-btn[data-id="${id}"]`);
  if (btn) {
    btn.classList.remove('learning');
    btn.querySelector('.learn-icon').textContent = '🎯';
    btn.querySelector('.action-label').textContent = 'Apprendre';
  }
  showToast('Morceau retiré de ta liste.');
}

/* ── learn toggle ── */
function restoreLearnButtons() {
  const list = getWishlist();
  const inList = new Set(list.map(s => s.id));
  document.querySelectorAll('.learn-btn').forEach(btn => {
    if (inList.has(btn.dataset.id)) {
      btn.classList.add('learning');
      btn.querySelector('.learn-icon').textContent = '✅';
      btn.querySelector('.action-label').textContent = 'Dans ma liste';
    }
  });
}

document.querySelectorAll('.learn-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const { id, title, artist, style } = btn.dataset;
    const list = getWishlist();
    const already = list.find(s => s.id === id);

    if (already) {
      removeFromWishlist(id);
    } else {
      addToWishlist(id, title, artist, style);
      btn.classList.add('learning');
      btn.querySelector('.learn-icon').textContent = '✅';
      btn.querySelector('.action-label').textContent = 'Dans ma liste';
      /* bounce */
      btn.style.transform = 'scale(1.18)';
      setTimeout(() => btn.style.transform = '', 180);
      showToast(`"${title}" ajouté à ta liste !`);
    }
  });
});

/* ── clear wishlist ── */
document.getElementById('clearWishlist').addEventListener('click', () => {
  saveWishlist([]);
  renderWishlist();
  /* reset all learn btns */
  document.querySelectorAll('.learn-btn').forEach(btn => {
    btn.classList.remove('learning');
    btn.querySelector('.learn-icon').textContent = '🎯';
    btn.querySelector('.action-label').textContent = 'Apprendre';
  });
  showToast('Liste vidée.');
});

/* ── init ── */
restoreLikes();
restoreLearnButtons();
renderWishlist();
