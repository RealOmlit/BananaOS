class UnifiedGames {
    constructor() {
        this.games = [];
        this.filteredGames = [];
        this.selectedCategories = new Set();
        this.searchQuery = '';
        this.sortMode = 'name-asc';
        this.viewMode = 'grid';
        this.currentPage = 1;
        this.gamesPerPage = 100;
        this.debounceTimer = null;
        
        this.elements = {
            gameGrid: document.getElementById('gameGrid'),
            searchInput: document.getElementById('searchInput'),
            autocomplete: document.getElementById('autocomplete'),
            sortSelect: document.getElementById('sort-select'),
            categoryToggle: document.getElementById('category-toggle'),
            categoryDropdown: document.getElementById('category-dropdown'),
            categoryList: document.getElementById('category-list'),
            categorySearch: document.getElementById('category-search'),
            categoryFilterBar: document.getElementById('category-filter-bar'),
            gameCount: document.getElementById('game-count'),
            resultsCount: document.getElementById('results-count'),
            emptyState: document.getElementById('empty-state'),
            clearFilters: document.getElementById('clear-filters'),
            viewBtns: document.querySelectorAll('.view-btn'),
            gameModal: document.getElementById('game-modal'),
            modalTitle: document.getElementById('modal-title'),
            modalThumbnail: document.getElementById('modal-thumbnail'),
            modalCategories: document.getElementById('modal-categories'),
            modalDescription: document.getElementById('modal-description'),
            modalPlayBtn: document.getElementById('modal-play-btn'),
            modalFullscreenBtn: document.getElementById('modal-fullscreen-btn'),
            modalNewtabBtn: document.getElementById('modal-newtab-btn'),
            modalClose: document.querySelector('.modal-close'),
            loadingScreen: document.getElementById('loading-screen')
        };
        
        this.init();
    }
    
    async init() {
        await this.loadGames();
        this.setupEventListeners();
        this.renderCategories();
        this.applyFilters();
        this.hideLoading();
    }
    
    async loadGames() {
        try {
            const response = await fetch('/js/json/unified_games.json?t=' + Date.now());
            if (!response.ok) throw new Error('Failed to load games');
            const data = await response.json();
            this.games = data.games || [];
            this.allCategories = data.categories || [];
            console.log(`Loaded ${this.games.length} games with ${this.allCategories.length} categories`);
        } catch (error) {
            console.error('Error loading games:', error);
            this.games = [];
            this.allCategories = [];
        }
    }
    
    hideLoading() {
        if (this.elements.loadingScreen) {
            this.elements.loadingScreen.classList.add('hidden');
            setTimeout(() => {
                this.elements.loadingScreen.style.display = 'none';
            }, 500);
        }
    }
    
    setupEventListeners() {
        this.elements.searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));
        this.elements.searchInput.addEventListener('focus', () => this.showAutocomplete());
        this.elements.searchInput.addEventListener('keydown', (e) => this.handleAutocompleteKeydown(e));
        
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-wrapper')) {
                this.hideAutocomplete();
            }
            if (!e.target.closest('.category-btn') && !e.target.closest('.category-dropdown')) {
                this.closeCategoryDropdown();
            }
        });
        
        this.elements.sortSelect.addEventListener('change', (e) => {
            this.sortMode = e.target.value;
            this.applyFilters();
        });
        
        this.elements.categoryToggle.addEventListener('click', () => this.toggleCategoryDropdown());
        this.elements.categorySearch.addEventListener('input', (e) => this.filterCategories(e.target.value));
        this.elements.clearFilters.addEventListener('click', () => this.clearAllFilters());
        
        this.elements.viewBtns.forEach(btn => {
            btn.addEventListener('click', () => this.setViewMode(btn.dataset.view));
        });
        
        this.elements.modalClose.addEventListener('click', () => this.closeModal());
        this.elements.gameModal.querySelector('.modal-backdrop').addEventListener('click', () => this.closeModal());
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.elements.gameModal.classList.contains('show')) {
                this.closeModal();
            }
        });
        
        this.elements.modalPlayBtn.addEventListener('click', (e) => this.handleModalAction(e, 'play'));
        this.elements.modalFullscreenBtn.addEventListener('click', (e) => this.handleModalAction(e, 'fullscreen'));
        this.elements.modalNewtabBtn.addEventListener('click', (e) => this.handleModalAction(e, 'newtab'));
    }
    
    handleSearch(query) {
        this.searchQuery = query.toLowerCase().trim();
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.applyFilters();
            this.updateAutocomplete();
        }, 100);
    }
    
    updateAutocomplete() {
        if (!this.searchQuery) {
            this.hideAutocomplete();
            return;
        }
        
        const matches = this.games
            .filter(game => this.matchesSearch(game, this.searchQuery))
            .slice(0, 8);
        
        if (matches.length === 0) {
            this.hideAutocomplete();
            return;
        }
        
        this.elements.autocomplete.innerHTML = matches.map(game => `
            <div class="autocomplete-item" data-game-id="${game.id || game.name}">
                <img src="${game.thumbnail || '/png/logo.png'}" alt="${this.escapeHtml(game.name)}" loading="lazy"
                     onerror="this.src='/png/logo.png'">
                <span>${this.escapeHtml(game.name)}</span>
            </div>
        `).join('');
        
        this.elements.autocomplete.classList.add('show');
        
        this.elements.autocomplete.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => {
                const game = this.games.find(g => (g.id || g.name) == item.dataset.gameId);
                if (game) this.openGameModal(game);
            });
        });
    }
    
    showAutocomplete() {
        if (this.searchQuery) this.updateAutocomplete();
    }
    
    hideAutocomplete() {
        this.elements.autocomplete.classList.remove('show');
    }
    
    handleAutocompleteKeydown(e) {
        const items = this.elements.autocomplete.querySelectorAll('.autocomplete-item');
        const highlighted = this.elements.autocomplete.querySelector('.autocomplete-item.highlighted');
        let index = highlighted ? Array.from(items).indexOf(highlighted) : -1;
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            index = Math.min(index + 1, items.length - 1);
            this.highlightAutocompleteItem(items, index);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            index = Math.max(index - 1, 0);
            this.highlightAutocompleteItem(items, index);
        } else if (e.key === 'Enter' && highlighted) {
            e.preventDefault();
            highlighted.click();
        }
    }
    
    highlightAutocompleteItem(items, index) {
        items.forEach((item, i) => {
            item.classList.toggle('highlighted', i === index);
        });
        if (items[index]) {
            items[index].scrollIntoView({ block: 'nearest' });
        }
    }
    
    matchesSearch(game, query) {
        const searchableText = [
            game.name,
            ...(game.alt_names || []),
            ...(game.categories || [])
        ].join(' ').toLowerCase();
        
        return searchableText.includes(query);
    }
    
    matchesCategory(game) {
        if (this.selectedCategories.size === 0) return true;
        const gameCategories = new Set((game.categories || []).map(c => c.toLowerCase()));
        for (const cat of this.selectedCategories) {
            if (gameCategories.has(cat.toLowerCase())) return true;
        }
        return false;
    }
    
    applyFilters() {
        this.filteredGames = this.games.filter(game => {
            return this.matchesSearch(game, this.searchQuery) && this.matchesCategory(game);
        });
        
        this.sortGames();
        this.renderGames();
        this.updateCounts();
    }
    
    sortGames() {
        switch (this.sortMode) {
            case 'name-asc':
                this.filteredGames.sort((a, b) => a.name.localeCompare(b.name));
                break;
            case 'name-desc':
                this.filteredGames.sort((a, b) => b.name.localeCompare(a.name));
                break;
            case 'category':
                this.filteredGames.sort((a, b) => {
                    const aCat = (a.categories?.[0] || 'zzz').toLowerCase();
                    const bCat = (b.categories?.[0] || 'zzz').toLowerCase();
                    return aCat.localeCompare(bCat) || a.name.localeCompare(b.name);
                });
                break;
        }
    }
    
    renderGames() {
        const grid = this.elements.gameGrid;
        const emptyState = this.elements.emptyState;
        
        if (this.filteredGames.length === 0) {
            grid.innerHTML = '';
            emptyState.style.display = 'flex';
            return;
        }
        
        emptyState.style.display = 'none';
        
        grid.classList.toggle('list-view', this.viewMode === 'list');
        
        const fragment = document.createDocumentFragment();
        
        this.filteredGames.forEach((game, index) => {
            const card = this.createGameCard(game, index);
            fragment.appendChild(card);
        });
        
        grid.innerHTML = '';
        grid.appendChild(fragment);
        
        this.observeImages();
    }
    
    createGameCard(game, index) {
        const card = document.createElement('article');
        card.className = 'game-card';
        card.style.animationDelay = `${Math.min(index * 0.02, 0.3)}s`;
        card.setAttribute('role', 'listitem');
        card.setAttribute('tabindex', '0');
        card.dataset.gameId = game.id || game.name;
        
        const categories = game.categories || ['Other'];
        const primaryCategory = categories[0];
        
        card.innerHTML = `
            <img class="card-thumbnail" 
                 src="${game.thumbnail || '/png/logo.png'}" 
                 alt="${this.escapeHtml(game.name)}"
                 loading="lazy"
                 onerror="this.src='/png/logo.png'">
            <div class="card-overlay">
                <div class="card-info">
                    <h3 class="card-title">${this.escapeHtml(game.name)}</h3>
                    <div class="card-categories">
                        ${categories.slice(0, 3).map((cat, i) => `
                            <span class="category-tag ${i === 0 ? 'primary' : ''}">${this.escapeHtml(cat)}</span>
                        `).join('')}
                        ${categories.length > 3 ? `<span class="category-tag">+${categories.length - 3}</span>` : ''}
                    </div>
                </div>
                <button class="card-play-btn" aria-label="Play ${this.escapeHtml(game.name)}">
                    <svg viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                </button>
            </div>
        `;
        
        card.addEventListener('click', (e) => {
            if (!e.target.closest('.card-play-btn')) {
                this.openGameModal(game);
            }
        });
        
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.openGameModal(game);
            }
        });
        
        card.querySelector('.card-play-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.playGame(game);
        });
        
        return card;
    }
    
    renderSkeletons(count = 12) {
        const grid = this.elements.gameGrid;
        grid.classList.remove('list-view');
        grid.innerHTML = Array(count).fill(0).map(() => `
            <article class="game-card skeleton">
                <div class="card-thumbnail skeleton" style="aspect-ratio: 16/10;"></div>
                <div class="card-overlay">
                    <div class="card-info">
                        <div class="card-title skeleton" style="height: 1.2rem; width: 70%; margin-top: 12px;"></div>
                        <div class="card-categories skeleton" style="height: 0.8rem; width: 40%;"></div>
                    </div>
                </div>
            </article>
        `).join('');
    }
    
    observeImages() {
        const images = this.elements.gameGrid.querySelectorAll('img[loading="lazy"]');
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src || img.src;
                        img.classList.remove('skeleton');
                        observer.unobserve(img);
                    }
                });
            }, { rootMargin: '100px' });
            images.forEach(img => observer.observe(img));
        }
    }
    
    renderCategories() {
        const list = this.elements.categoryList;
        const categoryCounts = {};
        
        this.games.forEach(game => {
            (game.categories || ['Other']).forEach(cat => {
                categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
            });
        });
        
        const sortedCategories = this.allCategories
            .filter(c => categoryCounts[c])
            .sort((a, b) => (categoryCounts[b] || 0) - (categoryCounts[a] || 0));
        
        list.innerHTML = sortedCategories.map(cat => `
            <label class="category-option">
                <input type="checkbox" value="${this.escapeHtml(cat)}" ${this.selectedCategories.has(cat) ? 'checked' : ''}>
                <span>${this.escapeHtml(cat)}</span>
                <span class="count">${categoryCounts[cat] || 0}</span>
            </label>
        `).join('');
        
        list.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => this.toggleCategory(e.target.value, e.target.checked));
        });
        
        this.renderCategoryChips();
    }
    
    filterCategories(query) {
        const items = this.elements.categoryList.querySelectorAll('.category-option');
        const q = query.toLowerCase();
        items.forEach(item => {
            const text = item.querySelector('span').textContent.toLowerCase();
            item.style.display = text.includes(q) ? 'flex' : 'none';
        });
    }
    
    toggleCategory(category, checked) {
        if (checked) {
            this.selectedCategories.add(category);
        } else {
            this.selectedCategories.delete(category);
        }
        this.renderCategoryChips();
        this.applyFilters();
    }
    
    renderCategoryChips() {
        const bar = this.elements.categoryFilterBar;
        if (this.selectedCategories.size === 0) {
            bar.innerHTML = '';
            return;
        }
        
        bar.innerHTML = Array.from(this.selectedCategories).map(cat => `
            <span class="category-chip active">
                ${this.escapeHtml(cat)}
                <span class="remove" data-category="${this.escapeHtml(cat)}">&times;</span>
            </span>
        `).join('');
        
        bar.querySelectorAll('.remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleCategory(btn.dataset.category, false);
                const checkbox = this.elements.categoryList.querySelector(`input[value="${btn.dataset.category}"]`);
                if (checkbox) checkbox.checked = false;
            });
        });
    }
    
    toggleCategoryDropdown() {
        const isOpen = this.elements.categoryDropdown.classList.toggle('show');
        this.elements.categoryToggle.classList.toggle('open', isOpen);
        if (isOpen) {
            this.elements.categorySearch.focus();
        }
    }
    
    closeCategoryDropdown() {
        this.elements.categoryDropdown.classList.remove('show');
        this.elements.categoryToggle.classList.remove('open');
    }
    
    clearAllFilters() {
        this.searchQuery = '';
        this.elements.searchInput.value = '';
        this.selectedCategories.clear();
        this.sortMode = 'name-asc';
        this.elements.sortSelect.value = 'name-asc';
        
        this.elements.categoryList.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        
        this.applyFilters();
        this.renderCategoryChips();
        this.hideAutocomplete();
    }
    
    setViewMode(mode) {
        this.viewMode = mode;
        this.elements.viewBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === mode);
        });
        this.elements.gameGrid.classList.toggle('list-view', mode === 'list');
    }
    
    updateCounts() {
        const total = this.games.length;
        const filtered = this.filteredGames.length;
        
        this.elements.gameCount.textContent = `${filtered} of ${total} games`;
        this.elements.resultsCount.textContent = `${filtered} game${filtered !== 1 ? 's' : ''}`;
    }
    
    openGameModal(game) {
        const modal = this.elements.gameModal;
        
        this.elements.modalTitle.textContent = game.name;
        this.elements.modalThumbnail.src = game.thumbnail || '/png/logo.png';
        this.elements.modalThumbnail.alt = game.name;
        
        const categories = game.categories || ['Other'];
        this.elements.modalCategories.innerHTML = categories.map((cat, i) => `
            <span class="category-tag ${i === 0 ? 'primary' : ''}">${this.escapeHtml(cat)}</span>
        `).join('');
        
        this.elements.modalDescription.textContent = game.description || `Play ${game.name} - an awesome unblocked game!`;
        
        const gameUrl = this.getGameUrl(game);
        this.elements.modalPlayBtn.href = gameUrl;
        this.elements.modalFullscreenBtn.onclick = () => this.openFullscreen(gameUrl);
        this.elements.modalNewtabBtn.onclick = () => window.open(gameUrl, '_blank');
        
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
        this.elements.modalClose.focus();
    }
    
    closeModal() {
        this.elements.gameModal.classList.remove('show');
        document.body.style.overflow = '';
    }
    
    handleModalAction(e, action) {
        e.preventDefault();
        const gameId = this.elements.modalTitle.textContent;
        const game = this.games.find(g => g.name === gameId);
        if (!game) return;
        
        const url = this.getGameUrl(game);
        
        switch (action) {
            case 'play':
                window.location.href = url;
                break;
            case 'fullscreen':
                this.openFullscreen(url);
                break;
            case 'newtab':
                window.open(url, '_blank');
                break;
        }
        this.closeModal();
    }
    
    playGame(game) {
        const url = this.getGameUrl(game);
        window.location.href = url;
    }
    
    openFullscreen(url) {
        const newWindow = window.open(url, '_blank', 'fullscreen=yes');
        if (newWindow) {
            newWindow.moveTo(0, 0);
            newWindow.resizeTo(screen.width, screen.height);
        }
    }
    
    getGameUrl(game) {
        let url = game.url;
        if (game.requiresPrefix) {
            const prefix = sessionStorage.getItem("prefix") || '';
            url = url.replace('{prefix}', prefix);
        }
        if (typeof transformGameUrl === 'function') {
            url = transformGameUrl(url);
        }
        
        const frameType = game.frameType || 'iframe';
        const directUrls = ['/games/amaze/index.html'];
        const shouldOpenDirectly = directUrls.some(d => url.includes(d));
        
        if (shouldOpenDirectly) {
            return url;
        }
        
        return frameType === 'unity' 
            ? `/unityframe.html?url=${encodeURIComponent(url)}`
            : `/iframe.html?url=${encodeURIComponent(url)}`;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showDMCA() {
        this.showPopup('DMCA', `
            <p>If you own or developed a game that is on <strong>UBG Ultra</strong> and would like it removed:</p>
            <ol style="margin: 16px 0; padding-left: 20px;">
                <li>Join our <a href="https://discord.gg/vVqY36mzvj" target="_blank">Discord</a> and DM the admins <strong>[INSTANT RESPONSE]</strong></li>
                <li>Email us with subject <code>!DMCA</code> <strong>[DELAYED RESPONSE]</strong></li>
            </ol>
            <p>Please show proof of ownership.</p>
        `);
    }
    
    showContact() {
        this.showPopup('Contact', `
            <p>Discord: <a href="https://discord.gg/vVqY36mzvj" target="_blank">discord.gg/vVqY36mzvj</a></p>
            <p>Email: support@ubg-ultra.com</p>
        `);
    }
    
    showPrivacy() {
        this.showPopup('Privacy Policy', `
            <div style="max-height: 60vh; overflow-y: auto;">
                <h4>Privacy Policy</h4>
                <p>Last updated: 2025</p>
                <p>We respect your privacy. This site uses minimal analytics and no tracking cookies.</p>
                <p>Games are loaded from third-party sources. We are not responsible for their privacy practices.</p>
            </div>
        `);
    }
    
    showPopup(title, body) {
        const overlay = document.getElementById('popup-overlay');
        document.getElementById('popup-title').textContent = title;
        document.getElementById('popup-body').innerHTML = body;
        overlay.classList.add('show');
    }
    
    closePopup() {
        document.getElementById('popup-overlay').classList.remove('show');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.unifiedGames = new UnifiedGames();
    window.showDMCA = () => window.unifiedGames.showDMCA();
    window.showContact = () => window.unifiedGames.showContact();
    window.showPrivacy = () => window.unifiedGames.showPrivacy();
    window.closePopup = () => window.unifiedGames.closePopup();
});