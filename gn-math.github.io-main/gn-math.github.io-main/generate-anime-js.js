const fs = require('fs');

const rawData = JSON.parse(fs.readFileSync('anime-data.json', 'utf8'));

function formatStatus(status) {
  const map = {
    'FINISHED': 'Finished',
    'RELEASING': 'Airing',
    'NOT_YET_RELEASED': 'Upcoming',
    'CANCELLED': 'Cancelled',
    'HIATUS': 'Hiatus'
  };
  return map[status] || status;
}

function formatType(format) {
  const map = {
    'TV': 'TV',
    'TV_SHORT': 'TV',
    'MOVIE': 'Movie',
    'SPECIAL': 'Special',
    'OVA': 'OVA',
    'ONA': 'ONA',
    'MUSIC': 'Music'
  };
  return map[format] || format;
}

function formatSeason(season) {
  return season ? season.charAt(0) + season.slice(1).toLowerCase() : '';
}

const processed = rawData.map((anime, index) => {
  const title = anime.title.romaji || anime.title.native;
  const english = anime.title.english || anime.title.romaji || title;
  
  return {
    rank: index + 1,
    id: anime.id,
    title: title,
    english: english,
    native: anime.title.native,
    type: formatType(anime.format),
    episodes: anime.episodes || '?',
    duration: anime.duration,
    score: anime.averageScore ? anime.averageScore / 10 : 0,
    year: anime.seasonYear || (anime.startDate?.year || 0),
    season: formatSeason(anime.season),
    status: formatStatus(anime.status),
    genres: anime.genres || [],
    image: anime.coverImage?.large || '',
    popularity: anime.popularity,
    startDate: anime.startDate,
    endDate: anime.endDate,
    nextAiring: anime.nextAiringEpisode
  };
});

// Sort by popularity descending
processed.sort((a, b) => b.popularity - a.popularity);

// Re-rank
processed.forEach((a, i) => a.rank = i + 1);

// Generate JS file
const jsContent = `const animeData = ${JSON.stringify(processed, null, 2)};

let currentSort = 'rank';
let currentFilter = 'all';
let currentSearch = '';

const seriesContainer = document.getElementById('animeSeriesContainer');
const moviesContainer = document.getElementById('animeMoviesContainer');
const ovaContainer = document.getElementById('animeOvaContainer');
const searchBar = document.getElementById('animeSearchBar');
const sortOptions = document.getElementById('animeSortOptions');
const filterOptions = document.getElementById('animeFilterOptions');
const animeCountText = document.getElementById('animeCountText');
const seriesCount = document.getElementById('seriesCount');
const moviesCount = document.getElementById('moviesCount');
const ovaCount = document.getElementById('ovaCount');
const typeFilters = document.getElementById('typeFilters');

function init() {
    createTypeFilters();
    sortAnime();
    renderAll();
}

function createTypeFilters() {
    const types = [...new Set(animeData.map(a => a.type))].sort();
    types.forEach(type => {
        const btn = document.createElement('button');
        btn.textContent = type;
        btn.className = 'type-filter-btn';
        btn.dataset.type = type;
        btn.onclick = () => setTypeFilter(type);
        typeFilters.appendChild(btn);
    });
    updateTypeFilterButtons();
}

function setTypeFilter(type) {
    currentFilter = type;
    filterOptions.value = type;
    updateTypeFilterButtons();
    renderAll();
}

function updateTypeFilterButtons() {
    document.querySelectorAll('.type-filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.type === currentFilter);
    });
}

function filterAnime() {
    currentSearch = searchBar.value.toLowerCase().trim();
    currentFilter = filterOptions.value;
    updateTypeFilterButtons();
    renderAll();
}

function sortAnime() {
    currentSort = sortOptions.value;
    renderAll();
}

function getFilteredAnime() {
    return animeData.filter(anime => {
        const matchesSearch = !currentSearch ||
            anime.title.toLowerCase().includes(currentSearch) ||
            anime.english.toLowerCase().includes(currentSearch) ||
            (anime.native && anime.native.toLowerCase().includes(currentSearch)) ||
            anime.genres.some(g => g.toLowerCase().includes(currentSearch));
        const matchesFilter = currentFilter === 'all' || anime.type === currentFilter;
        return matchesSearch && matchesFilter;
    });
}

function sortAnimeList(list) {
    const sorted = [...list];
    switch (currentSort) {
        case 'rank': return sorted.sort((a, b) => a.rank - b.rank);
        case 'title': return sorted.sort((a, b) => a.title.localeCompare(b.title));
        case 'score': return sorted.sort((a, b) => b.score - a.score);
        case 'year': return sorted.sort((a, b) => b.year - a.year);
        case 'type': return sorted.sort((a, b) => a.type.localeCompare(b.type));
        case 'popularity': return sorted.sort((a, b) => b.popularity - a.popularity);
        default: return sorted;
    }
}

function renderAll() {
    const filtered = getFilteredAnime();
    const sorted = sortAnimeList(filtered);

    const series = sorted.filter(a => a.type === 'TV');
    const movies = sorted.filter(a => a.type === 'Movie');
    const ova = sorted.filter(a => ['OVA', 'ONA', 'Special', 'Music'].includes(a.type));

    seriesCount.textContent = series.length;
    moviesCount.textContent = movies.length;
    ovaCount.textContent = ova.length;
    animeCountText.textContent = \`\${filtered.length} anime total\`;

    seriesContainer.innerHTML = series.map(createAnimeCard).join('');
    moviesContainer.innerHTML = movies.map(createAnimeCard).join('');
    ovaContainer.innerHTML = ova.map(createAnimeCard).join('');
}

function createAnimeCard(anime) {
    const typeClass = anime.type.toLowerCase();
    const statusClass = anime.status.toLowerCase().replace(' ', '-');
    const imgSrc = anime.image || \`https://via.placeholder.com/300x400/1e293b/64748b?text=\${encodeURIComponent(anime.title)}\`;

    const episodeText = anime.episodes === '?' ? '? eps' : \`\${anime.episodes} eps\`;

    return \`
        <div class="anime-item" data-rank="\${anime.rank}" onclick="openModal(\${anime.rank})">
            <div class="anime-image-wrapper">
                <img src="\${imgSrc}" alt="\${anime.title}" loading="lazy"
                     onerror="this.src='https://via.placeholder.com/300x400/1e293b/64748b?text=\${encodeURIComponent(anime.title)}'">
                <div class="anime-rank">#\${anime.rank}</div>
                <div class="anime-type \${typeClass}">\${anime.type}</div>
                <div class="anime-status \${statusClass}">\${anime.status}</div>
            </div>
            <button class="anime-info">
                <div class="anime-title">\${anime.title}</div>
                <div class="anime-english">\${anime.english}</div>
                <div class="anime-meta">
                    <span class="anime-score"><svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg> \${anime.score.toFixed(2)}</span>
                    <span class="anime-year">\${anime.year}</span>
                    <span class="anime-eps">\${episodeText}</span>
                </div>
                <div class="anime-genres">
                    \${anime.genres.slice(0, 4).map(g => \`<span class="genre-tag">\${g}</span>\`).join('')}
                    \${anime.genres.length > 4 ? \`<span class="genre-tag more">+\${anime.genres.length - 4}</span>\` : ''}
                </div>
            </button>
        </div>
    \`;
}

function openModal(rank) {
    const anime = animeData.find(a => a.rank === rank);
    if (!anime) return;

    const modal = document.getElementById('animeModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');

    modalTitle.textContent = anime.title;
    
    const episodeText = anime.episodes === '?' ? 'Unknown' : \`\${anime.episodes} episodes\`;
    const durationText = anime.duration ? \`\${anime.duration} min/ep\` : 'Unknown duration';
    const seasonText = anime.season ? \`\${anime.season} \${anime.year}\` : \`\${anime.year}\`;
    const statusText = anime.status;
    const nextAiringText = anime.nextAiring ? \`Next ep \${anime.nextAiring.episode}: \${new Date(anime.nextAiring.airingAt * 1000).toLocaleDateString()}\` : '';

    modalBody.innerHTML = \`
        <div class="modal-content">
            <img src="\${anime.image}" alt="\${anime.title}" class="modal-image"
                 onerror="this.src='https://via.placeholder.com/400x560/1e293b/64748b?text=\${encodeURIComponent(anime.title)}'">
            <div class="modal-details">
                <h2>\${anime.title}</h2>
                \${anime.native && anime.native !== anime.title ? \`<p class="modal-native">\${anime.native}</p>\` : ''}
                <p class="modal-english">\${anime.english}</p>
                <div class="modal-stats">
                    <div class="stat"><span class="stat-label">Rank</span> #\${anime.rank}</div>
                    <div class="stat"><span class="stat-label">Score</span> \${anime.score.toFixed(2)} <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg></div>
                    <div class="stat"><span class="stat-label">Type</span> \${anime.type}</div>
                    <div class="stat"><span class="stat-label">Episodes</span> \${episodeText}</div>
                    <div class="stat"><span class="stat-label">Duration</span> \${durationText}</div>
                    <div class="stat"><span class="stat-label">Season</span> \${seasonText}</div>
                    <div class="stat"><span class="stat-label">Status</span> \${statusText}</div>
                    <div class="stat"><span class="stat-label">Popularity</span> #\${anime.popularity.toLocaleString()}</div>
                </div>
                \${nextAiringText ? \`<div class="next-airing">\${nextAiringText}</div>\` : ''}
                <div class="modal-genres">
                    \${anime.genres.map(g => \`<span class="genre-tag">\${g}</span>\`).join('')}
                </div>
                <a href="https://anilist.co/anime/\${anime.id}" target="_blank" class="mal-link">
                    View on AniList →
                </a>
            </div>
        </div>
    \`;
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    const modal = document.getElementById('animeModal');
    modal.style.display = 'none';
    document.body.style.overflow = '';
}

document.getElementById('animeModal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeModal();
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

init();
`;

fs.writeFileSync('anime.js', jsContent);
console.log(`Generated anime.js with ${processed.length} anime entries`);

// Stats
const byType = {};
processed.forEach(a => {
  byType[a.type] = (byType[a.type] || 0) + 1;
});
console.log('By type:', byType);

const byStatus = {};
processed.forEach(a => {
  byType[a.status] = (byType[a.status] || 0) + 1;
});
console.log('By status:', byStatus);

const byYear = {};
processed.forEach(a => {
  if (a.year) byYear[a.year] = (byYear[a.year] || 0) + 1;
});
console.log('Top years:', Object.entries(byYear).sort((a,b) => b[1]-a[1]).slice(0,10));