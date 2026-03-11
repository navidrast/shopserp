/* ============================================================
   ShopSerp  --  Complete Application Logic
   Routing, API, Charts, State Management
   ============================================================ */

(function () {
  'use strict';

  // ───────────────────────────────────────────────
  // Constants & Country Data
  // ───────────────────────────────────────────────
  const COUNTRIES = [
    { code: 'us', name: 'United States', flag: '\u{1F1FA}\u{1F1F8}', currency: 'USD', symbol: '$' },
    { code: 'gb', name: 'United Kingdom', flag: '\u{1F1EC}\u{1F1E7}', currency: 'GBP', symbol: '\u00A3' },
    { code: 'au', name: 'Australia', flag: '\u{1F1E6}\u{1F1FA}', currency: 'AUD', symbol: 'A$' },
    { code: 'ca', name: 'Canada', flag: '\u{1F1E8}\u{1F1E6}', currency: 'CAD', symbol: 'C$' },
    { code: 'de', name: 'Germany', flag: '\u{1F1E9}\u{1F1EA}', currency: 'EUR', symbol: '\u20AC' },
    { code: 'fr', name: 'France', flag: '\u{1F1EB}\u{1F1F7}', currency: 'EUR', symbol: '\u20AC' },
    { code: 'jp', name: 'Japan', flag: '\u{1F1EF}\u{1F1F5}', currency: 'JPY', symbol: '\u00A5' },
    { code: 'in', name: 'India', flag: '\u{1F1EE}\u{1F1F3}', currency: 'INR', symbol: '\u20B9' },
    { code: 'br', name: 'Brazil', flag: '\u{1F1E7}\u{1F1F7}', currency: 'BRL', symbol: 'R$' },
    { code: 'it', name: 'Italy', flag: '\u{1F1EE}\u{1F1F9}', currency: 'EUR', symbol: '\u20AC' },
    { code: 'es', name: 'Spain', flag: '\u{1F1EA}\u{1F1F8}', currency: 'EUR', symbol: '\u20AC' },
    { code: 'nl', name: 'Netherlands', flag: '\u{1F1F3}\u{1F1F1}', currency: 'EUR', symbol: '\u20AC' },
    { code: 'kr', name: 'South Korea', flag: '\u{1F1F0}\u{1F1F7}', currency: 'KRW', symbol: '\u20A9' },
    { code: 'mx', name: 'Mexico', flag: '\u{1F1F2}\u{1F1FD}', currency: 'MXN', symbol: 'MX$' },
    { code: 'se', name: 'Sweden', flag: '\u{1F1F8}\u{1F1EA}', currency: 'SEK', symbol: 'kr' },
  ];

  const REPUTABLE_STORES = [
    'amazon', 'walmart', 'target', 'best buy', 'costco', 'newegg', 'b&h photo',
    'adorama', 'apple', 'samsung', 'dell', 'hp', 'lenovo', 'microsoft',
    'home depot', 'lowes', 'ebay', 'google store', 'bhphotovideo',
    'john lewis', 'currys', 'argos', 'jb hi-fi', 'officeworks'
  ];

  // ───────────────────────────────────────────────
  // State
  // ───────────────────────────────────────────────
  const state = {
    currentRoute: '',
    searchResults: null,
    searchQuery: '',
    selectedCountries: ['us'],
    monitors: [],
    settings: {
      activeCountries: ['us', 'gb', 'au'],
      monitorInterval: 60,
      proxyUrl: '',
      webhookUrl: '',
      theme: 'dark',
    },
    sortBy: 'price-asc',
    filterReputable: false,
    filterCondition: 'all',
    filterPriceMin: '',
    filterPriceMax: '',
    chartInstances: {},
  };

  // ───────────────────────────────────────────────
  // DOM References
  // ───────────────────────────────────────────────
  const $app = document.getElementById('app');
  const $loading = document.getElementById('loadingOverlay');
  const $toastContainer = document.getElementById('toastContainer');

  // ───────────────────────────────────────────────
  // Theme
  // ───────────────────────────────────────────────
  function initTheme() {
    const saved = localStorage.getItem('shopserp-theme');
    if (saved) {
      state.settings.theme = saved;
    }
    applyTheme(state.settings.theme);
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    state.settings.theme = theme;
    localStorage.setItem('shopserp-theme', theme);
  }

  function toggleTheme() {
    applyTheme(state.settings.theme === 'dark' ? 'light' : 'dark');
    // Re-render settings if on that page
    if (state.currentRoute === 'settings') renderSettings();
  }

  document.getElementById('themeToggleSidebar').addEventListener('click', toggleTheme);

  // ───────────────────────────────────────────────
  // Toast Notifications
  // ───────────────────────────────────────────────
  function showToast(message, type) {
    type = type || 'info';
    var icons = { success: '\u2705', error: '\u274C', info: '\u2139\uFE0F', warning: '\u26A0\uFE0F' };
    var toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.innerHTML =
      '<span class="toast-icon">' + (icons[type] || '') + '</span>' +
      '<span class="toast-message">' + escapeHtml(message) + '</span>' +
      '<button class="toast-close" aria-label="Close">&times;</button>';
    $toastContainer.appendChild(toast);
    toast.querySelector('.toast-close').addEventListener('click', function () { removeToast(toast); });
    setTimeout(function () { removeToast(toast); }, 4500);
  }

  function removeToast(el) {
    if (!el || !el.parentNode) return;
    el.classList.add('removing');
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 300);
  }

  // ───────────────────────────────────────────────
  // Loading
  // ───────────────────────────────────────────────
  var loadingCount = 0;
  function showLoading() { loadingCount++; $loading.classList.add('visible'); }
  function hideLoading() { loadingCount--; if (loadingCount <= 0) { loadingCount = 0; $loading.classList.remove('visible'); } }

  // ───────────────────────────────────────────────
  // API Helper
  // ───────────────────────────────────────────────
  async function api(method, path, body) {
    showLoading();
    try {
      var opts = {
        method: method,
        headers: { 'Content-Type': 'application/json' },
      };
      if (body) opts.body = JSON.stringify(body);
      var res = await fetch('/api' + path, opts);
      if (!res.ok) {
        var errData;
        try { errData = await res.json(); } catch (_) { errData = {}; }
        throw new Error(errData.error || errData.message || 'Request failed (' + res.status + ')');
      }
      var data = await res.json();
      return data;
    } catch (err) {
      showToast(err.message, 'error');
      throw err;
    } finally {
      hideLoading();
    }
  }

  // ───────────────────────────────────────────────
  // Utility
  // ───────────────────────────────────────────────
  function escapeHtml(str) {
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function formatPrice(amount, currency) {
    if (amount == null) return 'N/A';
    try {
      return new Intl.NumberFormat('en-US', { style: 'currency', currency: currency || 'USD' }).format(amount);
    } catch (_) {
      return currency + ' ' + Number(amount).toFixed(2);
    }
  }

  function relativeTime(dateStr) {
    if (!dateStr) return 'Never';
    var now = Date.now();
    var diff = now - new Date(dateStr).getTime();
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
    if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
    return Math.floor(diff / 86400000) + 'd ago';
  }

  function getCountry(code) {
    return COUNTRIES.find(function (c) { return c.code === code; }) || { code: code, name: code, flag: '\u{1F30D}', currency: 'USD', symbol: '$' };
  }

  function isReputable(store) {
    if (!store) return false;
    var lower = store.toLowerCase();
    return REPUTABLE_STORES.some(function (s) { return lower.includes(s); });
  }

  function destroyCharts() {
    Object.keys(state.chartInstances).forEach(function (k) {
      if (state.chartInstances[k]) {
        state.chartInstances[k].destroy();
        delete state.chartInstances[k];
      }
    });
  }

  // ───────────────────────────────────────────────
  // Router
  // ───────────────────────────────────────────────
  function getRoute() {
    var hash = window.location.hash || '#/search';
    return hash.replace('#/', '').split('?')[0];
  }

  function navigate(route) {
    window.location.hash = '#/' + route;
  }

  function handleRoute() {
    destroyCharts();
    var route = getRoute();
    state.currentRoute = route.split('/')[0];

    // Update nav active states
    document.querySelectorAll('.nav-link, .bottom-nav-link').forEach(function (el) {
      var r = el.getAttribute('data-route');
      if (r && route.startsWith(r)) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });

    if (route === 'search' || route === '') {
      renderSearch();
    } else if (route === 'monitors') {
      renderMonitors();
    } else if (route.startsWith('product/')) {
      var id = route.split('/')[1];
      renderProductDetail(id);
    } else if (route === 'settings') {
      renderSettings();
    } else {
      renderSearch();
    }
  }

  window.addEventListener('hashchange', handleRoute);

  // ───────────────────────────────────────────────
  // Page: Search
  // ───────────────────────────────────────────────
  function renderSearch() {
    var countryCbs = COUNTRIES.map(function (c) {
      var checked = state.selectedCountries.includes(c.code) ? 'checked' : '';
      return '<label class="checkbox-label">' +
        '<input type="checkbox" name="search-country" value="' + c.code + '" ' + checked + '>' +
        '<span class="cb-indicator"></span>' +
        '<span class="cb-text">' + c.flag + ' ' + escapeHtml(c.name) + '</span>' +
        '</label>';
    }).join('');

    var html = '<div class="page-enter">' +
      '<div class="page-header">' +
        '<h1 class="page-title">Search Products</h1>' +
        '<p class="page-subtitle">Search Google Shopping across multiple countries and compare prices</p>' +
      '</div>' +

      '<div class="card mb-20">' +
        '<div class="form-group">' +
          '<label class="form-label">Product Search</label>' +
          '<div class="search-input-wrap">' +
            '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>' +
            '<input type="text" class="form-input" id="searchInput" placeholder="e.g. Sony WH-1000XM5 headphones" value="' + escapeHtml(state.searchQuery) + '">' +
          '</div>' +
        '</div>' +
        '<div class="form-group mb-16">' +
          '<label class="form-label">Countries</label>' +
          '<div class="checkbox-group" id="countryCheckboxes">' + countryCbs + '</div>' +
        '</div>' +
        '<button class="btn btn-primary" id="searchBtn">' +
          '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>' +
          'Search' +
        '</button>' +
      '</div>' +

      '<div id="searchResultsArea"></div>' +
    '</div>';

    $app.innerHTML = html;

    // Bind events
    document.getElementById('searchBtn').addEventListener('click', performSearch);
    document.getElementById('searchInput').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') performSearch();
    });

    // Restore results if available
    if (state.searchResults) {
      renderSearchResults(state.searchResults);
    }
  }

  async function performSearch() {
    var input = document.getElementById('searchInput');
    var query = input.value.trim();
    if (!query) { showToast('Please enter a search query', 'warning'); return; }

    // Gather selected countries
    var checked = document.querySelectorAll('input[name="search-country"]:checked');
    var countries = [];
    checked.forEach(function (cb) { countries.push(cb.value); });
    if (countries.length === 0) { showToast('Select at least one country', 'warning'); return; }

    state.searchQuery = query;
    state.selectedCountries = countries;

    try {
      var data = await api('POST', '/search', { query: query, countries: countries });
      state.searchResults = data;
      renderSearchResults(data);
      showToast('Found results across ' + countries.length + ' countries', 'success');
    } catch (_) {
      // Error already shown by api()
    }
  }

  function renderSearchResults(data) {
    var area = document.getElementById('searchResultsArea');
    if (!area) return;

    var results = data.results || data;
    if (!results || (Array.isArray(results) && results.length === 0)) {
      area.innerHTML = '<div class="empty-state">' +
        '<svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>' +
        '<p class="empty-state-title">No results found</p>' +
        '<p class="empty-state-text">Try adjusting your search query or adding more countries.</p>' +
      '</div>';
      return;
    }

    // Normalize: group by country
    var grouped = {};
    if (Array.isArray(results)) {
      results.forEach(function (r) {
        var cc = r.country || 'us';
        if (!grouped[cc]) grouped[cc] = [];
        grouped[cc].push(r);
      });
    } else if (typeof results === 'object') {
      grouped = results;
    }

    // Filters bar
    var filtersHtml = '<div class="filters-bar">' +
      '<label class="form-label" style="margin-bottom:0">Sort:</label>' +
      '<select class="form-select" id="sortSelect">' +
        '<option value="price-asc"' + (state.sortBy === 'price-asc' ? ' selected' : '') + '>Price: Low to High</option>' +
        '<option value="price-desc"' + (state.sortBy === 'price-desc' ? ' selected' : '') + '>Price: High to Low</option>' +
        '<option value="store"' + (state.sortBy === 'store' ? ' selected' : '') + '>Store Name</option>' +
      '</select>' +
      '<span class="filter-divider"></span>' +
      '<label class="form-label" style="margin-bottom:0">Condition:</label>' +
      '<select class="form-select" id="conditionSelect">' +
        '<option value="all"' + (state.filterCondition === 'all' ? ' selected' : '') + '>All</option>' +
        '<option value="new"' + (state.filterCondition === 'new' ? ' selected' : '') + '>New</option>' +
        '<option value="used"' + (state.filterCondition === 'used' ? ' selected' : '') + '>Used</option>' +
        '<option value="refurbished"' + (state.filterCondition === 'refurbished' ? ' selected' : '') + '>Refurbished</option>' +
      '</select>' +
      '<span class="filter-divider"></span>' +
      '<label class="checkbox-label" style="margin:0">' +
        '<input type="checkbox" id="reputableOnly"' + (state.filterReputable ? ' checked' : '') + '>' +
        '<span class="cb-indicator"></span>' +
        '<span class="cb-text">Reputable only</span>' +
      '</label>' +
      '<span class="filter-divider"></span>' +
      '<div class="range-inputs">' +
        '<input type="number" class="form-input" id="priceMin" placeholder="Min" value="' + (state.filterPriceMin || '') + '">' +
        '<span>&ndash;</span>' +
        '<input type="number" class="form-input" id="priceMax" placeholder="Max" value="' + (state.filterPriceMax || '') + '">' +
      '</div>' +
    '</div>';

    // Render groups
    var groupsHtml = '';
    Object.keys(grouped).forEach(function (cc) {
      var c = getCountry(cc);
      var items = applyFiltersAndSort(grouped[cc], c.currency);

      groupsHtml += '<div class="country-group">' +
        '<div class="country-group-header">' +
          '<div class="country-group-title">' +
            '<span class="country-flag">' + c.flag + '</span> ' + escapeHtml(c.name) +
            ' <span class="badge badge-neutral">' + items.length + ' results</span>' +
          '</div>' +
          '<button class="btn btn-sm btn-success monitor-group-btn" data-country="' + cc + '">Monitor This Product</button>' +
        '</div>' +
        '<div class="country-group-results">' +
        items.map(function (item) { return renderProductCard(item, c); }).join('') +
        '</div>' +
      '</div>';
    });

    area.innerHTML = filtersHtml + groupsHtml;

    // Bind filter events
    ['sortSelect', 'conditionSelect', 'reputableOnly', 'priceMin', 'priceMax'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('change', function () {
        state.sortBy = document.getElementById('sortSelect').value;
        state.filterCondition = document.getElementById('conditionSelect').value;
        state.filterReputable = document.getElementById('reputableOnly').checked;
        state.filterPriceMin = document.getElementById('priceMin').value;
        state.filterPriceMax = document.getElementById('priceMax').value;
        renderSearchResults(data);
      });
    });

    // Monitor group buttons
    document.querySelectorAll('.monitor-group-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        monitorProduct(state.searchQuery, [btn.getAttribute('data-country')]);
      });
    });
  }

  function applyFiltersAndSort(items, currency) {
    var filtered = items.slice();

    if (state.filterReputable) {
      filtered = filtered.filter(function (i) { return isReputable(i.store || i.seller || ''); });
    }

    if (state.filterCondition !== 'all') {
      filtered = filtered.filter(function (i) {
        return (i.condition || 'new').toLowerCase() === state.filterCondition;
      });
    }

    var pmin = parseFloat(state.filterPriceMin);
    var pmax = parseFloat(state.filterPriceMax);
    if (!isNaN(pmin)) {
      filtered = filtered.filter(function (i) { return (i.price || 0) >= pmin; });
    }
    if (!isNaN(pmax)) {
      filtered = filtered.filter(function (i) { return (i.price || 0) <= pmax; });
    }

    filtered.sort(function (a, b) {
      switch (state.sortBy) {
        case 'price-asc': return (a.price || 0) - (b.price || 0);
        case 'price-desc': return (b.price || 0) - (a.price || 0);
        case 'store': return (a.store || '').localeCompare(b.store || '');
        default: return 0;
      }
    });

    return filtered;
  }

  function renderProductCard(item, country) {
    var store = item.store || item.seller || 'Unknown Store';
    var rep = isReputable(store);
    var priceClass = '';
    // No median to compare against here, just show green
    var imgHtml = item.image || item.thumbnail
      ? '<img src="' + escapeHtml(item.image || item.thumbnail) + '" alt="" loading="lazy">'
      : '<div class="img-placeholder">No Image</div>';

    var conditionBadge = '';
    var cond = (item.condition || 'New');
    if (cond.toLowerCase() === 'used') conditionBadge = '<span class="badge badge-yellow">Used</span>';
    else if (cond.toLowerCase() === 'refurbished') conditionBadge = '<span class="badge badge-purple">Refurb</span>';
    else conditionBadge = '<span class="badge badge-green">New</span>';

    var link = item.link || item.url || '#';

    return '<div class="product-card">' +
      '<div class="product-card-img">' + imgHtml + '</div>' +
      '<div class="product-card-body">' +
        '<div class="product-card-title"><a href="' + escapeHtml(link) + '" target="_blank" rel="noopener">' + escapeHtml(item.title || 'Untitled Product') + '</a></div>' +
        '<div class="product-card-store">' +
          escapeHtml(store) +
          (rep ? ' <span class="verified-badge" title="Reputable store">\u2713</span>' : '') +
        '</div>' +
        '<div class="product-card-price ' + priceClass + '">' + formatPrice(item.price, country.currency) + '</div>' +
        '<div class="product-card-meta">' +
          conditionBadge +
          (item.shipping ? '<span>Shipping: ' + escapeHtml(item.shipping) + '</span>' : '') +
          (item.rating ? '<span>\u2605 ' + item.rating + '</span>' : '') +
        '</div>' +
      '</div>' +
      '<div class="product-card-actions">' +
        '<a href="' + escapeHtml(link) + '" target="_blank" rel="noopener" class="btn btn-sm btn-secondary">View</a>' +
      '</div>' +
    '</div>';
  }

  async function monitorProduct(query, countries) {
    try {
      await api('POST', '/monitors', { query: query, countries: countries });
      showToast('Product is now being monitored', 'success');
    } catch (_) { /* handled */ }
  }

  // ───────────────────────────────────────────────
  // Page: Monitors
  // ───────────────────────────────────────────────
  async function renderMonitors() {
    $app.innerHTML = '<div class="page-enter">' +
      '<div class="page-header flex-between">' +
        '<div>' +
          '<h1 class="page-title">Monitors</h1>' +
          '<p class="page-subtitle">Track products and get alerted to price changes</p>' +
        '</div>' +
        '<button class="btn btn-primary" id="addMonitorBtn">' +
          '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
          'Add Monitor' +
        '</button>' +
      '</div>' +
      '<div id="monitorsGrid"><div class="spinner-inline"></div> Loading monitors...</div>' +
    '</div>';

    document.getElementById('addMonitorBtn').addEventListener('click', showAddMonitorModal);

    try {
      var data = await api('GET', '/monitors');
      state.monitors = data.monitors || data || [];
      renderMonitorsList();
    } catch (_) {
      state.monitors = [];
      renderMonitorsList();
    }
  }

  function renderMonitorsList() {
    var grid = document.getElementById('monitorsGrid');
    if (!grid) return;

    if (!state.monitors || state.monitors.length === 0) {
      grid.innerHTML = '<div class="empty-state">' +
        '<svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>' +
        '<p class="empty-state-title">No monitors yet</p>' +
        '<p class="empty-state-text">Start tracking a product by searching and clicking "Monitor This Product", or add one manually.</p>' +
      '</div>';
      return;
    }

    grid.innerHTML = '<div class="grid-auto">' + state.monitors.map(function (m) {
      var statusBadge = m.status === 'active'
        ? '<span class="badge badge-green">Active</span>'
        : '<span class="badge badge-yellow">Paused</span>';

      var countriesHtml = (m.countries || []).map(function (cc) {
        var c = getCountry(cc);
        return '<span class="badge badge-neutral" title="' + escapeHtml(c.name) + '">' + c.flag + '</span>';
      }).join(' ');

      var prices = (m.current_prices || []);
      var statsHtml = '';
      if (prices.length > 0) {
        statsHtml = prices.map(function (p) {
          var c = getCountry(p.country);
          return '<div class="monitor-stat">' +
            '<div class="monitor-stat-label">' + c.flag + ' Lowest</div>' +
            '<div class="monitor-stat-value price-low">' + formatPrice(p.price, c.currency) + '</div>' +
          '</div>';
        }).join('');
      } else {
        statsHtml = '<div class="monitor-stat">' +
          '<div class="monitor-stat-label">Status</div>' +
          '<div class="monitor-stat-value text-secondary text-sm">Awaiting first check</div>' +
        '</div>';
      }

      return '<div class="monitor-card">' +
        '<div class="monitor-card-header">' +
          '<div>' +
            '<div class="monitor-card-title" data-id="' + m.id + '">' + escapeHtml(m.query || m.name || 'Product') + '</div>' +
            '<div class="monitor-card-countries mt-4">' + countriesHtml + '</div>' +
          '</div>' +
          statusBadge +
        '</div>' +
        '<div class="monitor-card-stats">' + statsHtml + '</div>' +
        '<div class="text-xs text-tertiary mb-8">Last checked: ' + relativeTime(m.last_check || m.updated_at) + '</div>' +
        '<div class="monitor-card-actions">' +
          '<button class="btn btn-sm btn-secondary monitor-view-btn" data-id="' + m.id + '">View Details</button>' +
          '<button class="btn btn-sm btn-ghost monitor-toggle-btn" data-id="' + m.id + '" data-status="' + (m.status || 'active') + '">' +
            (m.status === 'active' ? 'Pause' : 'Resume') +
          '</button>' +
          '<button class="btn btn-sm btn-ghost monitor-alert-btn" data-id="' + m.id + '">Add Alert</button>' +
          '<button class="btn btn-sm btn-danger monitor-delete-btn" data-id="' + m.id + '">Delete</button>' +
        '</div>' +
      '</div>';
    }).join('') + '</div>';

    // Bind events
    grid.querySelectorAll('.monitor-card-title').forEach(function (el) {
      el.addEventListener('click', function () { navigate('product/' + el.getAttribute('data-id')); });
    });
    grid.querySelectorAll('.monitor-view-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { navigate('product/' + btn.getAttribute('data-id')); });
    });
    grid.querySelectorAll('.monitor-toggle-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { toggleMonitor(btn.getAttribute('data-id'), btn.getAttribute('data-status')); });
    });
    grid.querySelectorAll('.monitor-delete-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { deleteMonitor(btn.getAttribute('data-id')); });
    });
    grid.querySelectorAll('.monitor-alert-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { showAlertModal(btn.getAttribute('data-id')); });
    });
  }

  async function toggleMonitor(id, currentStatus) {
    var newStatus = currentStatus === 'active' ? 'paused' : 'active';
    try {
      await api('PATCH', '/monitors/' + id, { status: newStatus });
      showToast('Monitor ' + (newStatus === 'active' ? 'resumed' : 'paused'), 'success');
      renderMonitors();
    } catch (_) { /* handled */ }
  }

  async function deleteMonitor(id) {
    if (!confirm('Are you sure you want to delete this monitor?')) return;
    try {
      await api('DELETE', '/monitors/' + id);
      showToast('Monitor deleted', 'success');
      renderMonitors();
    } catch (_) { /* handled */ }
  }

  function showAddMonitorModal() {
    var countryCbs = COUNTRIES.map(function (c) {
      var checked = state.settings.activeCountries.includes(c.code) ? 'checked' : '';
      return '<label class="checkbox-label">' +
        '<input type="checkbox" name="modal-country" value="' + c.code + '" ' + checked + '>' +
        '<span class="cb-indicator"></span>' +
        '<span class="cb-text">' + c.flag + ' ' + escapeHtml(c.name) + '</span>' +
        '</label>';
    }).join('');

    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = '<div class="modal">' +
      '<div class="modal-header">' +
        '<h3 class="modal-title">Add New Monitor</h3>' +
        '<button class="modal-close">&times;</button>' +
      '</div>' +
      '<div class="form-group">' +
        '<label class="form-label">Product Query</label>' +
        '<input type="text" class="form-input" id="modalQuery" placeholder="e.g. iPhone 15 Pro Max 256GB">' +
      '</div>' +
      '<div class="form-group">' +
        '<label class="form-label">Countries</label>' +
        '<div class="checkbox-group">' + countryCbs + '</div>' +
      '</div>' +
      '<div class="modal-footer">' +
        '<button class="btn btn-secondary modal-cancel">Cancel</button>' +
        '<button class="btn btn-primary" id="modalAddBtn">Add Monitor</button>' +
      '</div>' +
    '</div>';

    document.body.appendChild(overlay);
    overlay.querySelector('.modal-close').addEventListener('click', function () { document.body.removeChild(overlay); });
    overlay.querySelector('.modal-cancel').addEventListener('click', function () { document.body.removeChild(overlay); });
    overlay.addEventListener('click', function (e) { if (e.target === overlay) document.body.removeChild(overlay); });

    document.getElementById('modalAddBtn').addEventListener('click', async function () {
      var q = document.getElementById('modalQuery').value.trim();
      if (!q) { showToast('Enter a product query', 'warning'); return; }
      var checked = overlay.querySelectorAll('input[name="modal-country"]:checked');
      var countries = [];
      checked.forEach(function (cb) { countries.push(cb.value); });
      if (countries.length === 0) { showToast('Select at least one country', 'warning'); return; }
      try {
        await api('POST', '/monitors', { query: q, countries: countries });
        showToast('Monitor added successfully', 'success');
        document.body.removeChild(overlay);
        renderMonitors();
      } catch (_) { /* handled */ }
    });
  }

  function showAlertModal(monitorId) {
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = '<div class="modal">' +
      '<div class="modal-header">' +
        '<h3 class="modal-title">Add Price Alert</h3>' +
        '<button class="modal-close">&times;</button>' +
      '</div>' +
      '<div class="form-group">' +
        '<label class="form-label">Alert when price drops below</label>' +
        '<input type="number" class="form-input" id="alertPrice" placeholder="e.g. 299.99" step="0.01">' +
      '</div>' +
      '<div class="form-group">' +
        '<label class="form-label">Notify via</label>' +
        '<select class="form-select" id="alertMethod">' +
          '<option value="webhook">Webhook</option>' +
          '<option value="email">Email</option>' +
        '</select>' +
      '</div>' +
      '<div class="modal-footer">' +
        '<button class="btn btn-secondary modal-cancel">Cancel</button>' +
        '<button class="btn btn-primary" id="modalAlertBtn">Set Alert</button>' +
      '</div>' +
    '</div>';

    document.body.appendChild(overlay);
    overlay.querySelector('.modal-close').addEventListener('click', function () { document.body.removeChild(overlay); });
    overlay.querySelector('.modal-cancel').addEventListener('click', function () { document.body.removeChild(overlay); });
    overlay.addEventListener('click', function (e) { if (e.target === overlay) document.body.removeChild(overlay); });

    document.getElementById('modalAlertBtn').addEventListener('click', async function () {
      var price = parseFloat(document.getElementById('alertPrice').value);
      var method = document.getElementById('alertMethod').value;
      if (isNaN(price) || price <= 0) { showToast('Enter a valid price', 'warning'); return; }
      try {
        await api('POST', '/monitors/' + monitorId + '/alerts', { target_price: price, method: method });
        showToast('Price alert set', 'success');
        document.body.removeChild(overlay);
      } catch (_) { /* handled */ }
    });
  }

  // ───────────────────────────────────────────────
  // Page: Product Detail / Analytics
  // ───────────────────────────────────────────────
  async function renderProductDetail(id) {
    $app.innerHTML = '<div class="page-enter">' +
      '<div class="flex-center mb-20">' +
        '<button class="btn btn-ghost" id="backBtn">' +
          '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>' +
          'Back to Monitors' +
        '</button>' +
      '</div>' +
      '<div id="productDetailContent"><div class="spinner-inline"></div> Loading product data...</div>' +
    '</div>';

    document.getElementById('backBtn').addEventListener('click', function () { navigate('monitors'); });

    try {
      var data = await api('GET', '/monitors/' + id);
      renderProductDetailContent(data, id);
    } catch (_) {
      document.getElementById('productDetailContent').innerHTML =
        '<div class="empty-state">' +
          '<p class="empty-state-title">Could not load product data</p>' +
          '<p class="empty-state-text">The product may have been deleted or the server is unreachable.</p>' +
        '</div>';
    }
  }

  function renderProductDetailContent(data, id) {
    var container = document.getElementById('productDetailContent');
    if (!container) return;

    var product = data.monitor || data;
    var countries = product.countries || ['us'];
    var history = data.history || product.history || [];
    var currentPrices = data.current_prices || product.current_prices || [];

    // Page header
    var headerHtml = '<div class="page-header">' +
      '<h1 class="page-title">' + escapeHtml(product.query || product.name || 'Product') + '</h1>' +
      '<p class="page-subtitle">Monitor ID: ' + escapeHtml(String(id)) + ' &middot; Status: ' +
        (product.status === 'active'
          ? '<span class="badge badge-green">Active</span>'
          : '<span class="badge badge-yellow">Paused</span>') +
      '</p>' +
    '</div>';

    // Country tabs
    var tabsHtml = '<div class="tabs" id="countryTabs">';
    countries.forEach(function (cc, i) {
      var c = getCountry(cc);
      tabsHtml += '<button class="tab-btn' + (i === 0 ? ' active' : '') + '" data-country="' + cc + '">' +
        c.flag + ' ' + escapeHtml(c.name) + '</button>';
    });
    tabsHtml += '</div>';

    // Analytics stats
    var statsHtml = '<div class="grid-4 mb-20" id="analyticsStats"></div>';

    // Price history chart
    var chartHtml = '<div class="grid-2 mb-20">' +
      '<div class="chart-container"><h3 class="mb-12">Price History</h3><canvas id="priceHistoryChart"></canvas></div>' +
      '<div class="chart-container"><h3 class="mb-12">Price Distribution</h3><canvas id="priceDistChart"></canvas></div>' +
    '</div>';

    // Current prices table
    var tableHtml = '<div class="card mb-20">' +
      '<h3 class="mb-12">Current Prices</h3>' +
      '<div class="table-wrap"><table class="table" id="pricesTable">' +
        '<thead><tr><th>Store</th><th>Price</th><th>Currency</th><th>Condition</th><th>In Stock</th><th>Link</th></tr></thead>' +
        '<tbody id="pricesTableBody"></tbody>' +
      '</table></div>' +
    '</div>';

    container.innerHTML = headerHtml + tabsHtml + statsHtml + chartHtml + tableHtml;

    // Initialize with first country
    var activeCountry = countries[0];
    updateProductDetailForCountry(activeCountry, history, currentPrices);

    // Tab switching
    container.querySelectorAll('.tab-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        container.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        activeCountry = btn.getAttribute('data-country');
        updateProductDetailForCountry(activeCountry, history, currentPrices);
      });
    });
  }

  function updateProductDetailForCountry(cc, history, currentPrices) {
    var c = getCountry(cc);

    // Filter data for this country
    var countryHistory = history.filter(function (h) { return h.country === cc; });
    var countryPrices = currentPrices.filter(function (p) { return p.country === cc; });

    // If no data, show demo data for illustration
    if (countryHistory.length === 0) {
      countryHistory = generateDemoHistory(cc);
    }
    if (countryPrices.length === 0) {
      countryPrices = generateDemoPrices(cc);
    }

    // Analytics
    var prices = countryPrices.map(function (p) { return p.price; }).filter(function (p) { return p > 0; });
    var avg = prices.length ? prices.reduce(function (a, b) { return a + b; }, 0) / prices.length : 0;
    var min = prices.length ? Math.min.apply(null, prices) : 0;
    var max = prices.length ? Math.max.apply(null, prices) : 0;
    var sorted = prices.slice().sort(function (a, b) { return a - b; });
    var median = sorted.length ? (sorted.length % 2 === 0 ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2 : sorted[Math.floor(sorted.length / 2)]) : 0;
    var variance = prices.length ? prices.reduce(function (sum, p) { return sum + Math.pow(p - avg, 2); }, 0) / prices.length : 0;
    var stddev = Math.sqrt(variance);

    var statsEl = document.getElementById('analyticsStats');
    if (statsEl) {
      statsEl.innerHTML =
        '<div class="stat-card"><div class="stat-card-value price-low">' + formatPrice(min, c.currency) + '</div><div class="stat-card-label">Minimum</div></div>' +
        '<div class="stat-card"><div class="stat-card-value">' + formatPrice(avg, c.currency) + '</div><div class="stat-card-label">Average</div></div>' +
        '<div class="stat-card"><div class="stat-card-value">' + formatPrice(median, c.currency) + '</div><div class="stat-card-label">Median</div></div>' +
        '<div class="stat-card"><div class="stat-card-value price-high">' + formatPrice(max, c.currency) + '</div><div class="stat-card-label">Maximum</div></div>';
    }

    // Current prices table
    var tbody = document.getElementById('pricesTableBody');
    if (tbody) {
      tbody.innerHTML = countryPrices.map(function (p) {
        var rep = isReputable(p.store || '');
        var priceClass = p.price <= min * 1.05 ? 'price-low' : (p.price >= max * 0.95 ? 'price-high' : '');
        return '<tr>' +
          '<td class="flex-center">' + escapeHtml(p.store || 'Unknown') +
            (rep ? ' <span class="verified-badge" title="Reputable">\u2713</span>' : '') + '</td>' +
          '<td class="font-bold ' + priceClass + '">' + formatPrice(p.price, c.currency) + '</td>' +
          '<td>' + c.currency + '</td>' +
          '<td>' + (p.condition || 'New') + '</td>' +
          '<td>' + (p.in_stock !== false ? '<span class="badge badge-green">Yes</span>' : '<span class="badge badge-red">No</span>') + '</td>' +
          '<td><a href="' + escapeHtml(p.link || '#') + '" target="_blank" rel="noopener" class="btn btn-sm btn-ghost">Visit</a></td>' +
        '</tr>';
      }).join('');
    }

    // Render charts
    renderPriceHistoryChart(countryHistory, c);
    renderPriceDistChart(countryPrices, c);
  }

  function renderPriceHistoryChart(history, country) {
    if (state.chartInstances.priceHistory) {
      state.chartInstances.priceHistory.destroy();
    }

    var canvas = document.getElementById('priceHistoryChart');
    if (!canvas) return;

    // Group by store
    var storeMap = {};
    history.forEach(function (h) {
      var store = h.store || 'Average';
      if (!storeMap[store]) storeMap[store] = [];
      storeMap[store].push({ date: h.date || h.timestamp, price: h.price });
    });

    var colors = ['#3b82f6', '#10b981', '#ef4444', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'];
    var datasets = [];
    var idx = 0;
    Object.keys(storeMap).forEach(function (store) {
      var points = storeMap[store].sort(function (a, b) { return new Date(a.date) - new Date(b.date); });
      datasets.push({
        label: store,
        data: points.map(function (p) { return { x: p.date, y: p.price }; }),
        borderColor: colors[idx % colors.length],
        backgroundColor: colors[idx % colors.length] + '20',
        fill: false,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 5,
        borderWidth: 2,
      });
      idx++;
    });

    var isDark = state.settings.theme === 'dark';
    state.chartInstances.priceHistory = new Chart(canvas, {
      type: 'line',
      data: { datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
          legend: { labels: { color: isDark ? '#94a3b8' : '#475569', font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: function (ctx) { return ctx.dataset.label + ': ' + formatPrice(ctx.parsed.y, country.currency); }
            }
          }
        },
        scales: {
          x: {
            type: 'time',
            time: { unit: 'day', tooltipFormat: 'MMM d, yyyy' },
            ticks: { color: isDark ? '#64748b' : '#94a3b8', maxTicksLimit: 8 },
            grid: { color: isDark ? '#1f2330' : '#e2e8f0' },
          },
          y: {
            ticks: {
              color: isDark ? '#64748b' : '#94a3b8',
              callback: function (v) { return country.symbol + v; }
            },
            grid: { color: isDark ? '#1f2330' : '#e2e8f0' },
          }
        }
      }
    });
  }

  function renderPriceDistChart(prices, country) {
    if (state.chartInstances.priceDist) {
      state.chartInstances.priceDist.destroy();
    }

    var canvas = document.getElementById('priceDistChart');
    if (!canvas) return;

    var priceVals = prices.map(function (p) { return p.price; }).filter(function (p) { return p > 0; });
    if (priceVals.length === 0) return;

    var min = Math.min.apply(null, priceVals);
    var max = Math.max.apply(null, priceVals);
    var bucketCount = Math.min(8, Math.max(3, priceVals.length));
    var step = (max - min) / bucketCount || 1;

    var labels = [];
    var counts = [];
    for (var i = 0; i < bucketCount; i++) {
      var lo = min + i * step;
      var hi = min + (i + 1) * step;
      labels.push(country.symbol + Math.round(lo) + '-' + country.symbol + Math.round(hi));
      var count = priceVals.filter(function (p) { return p >= lo && (i === bucketCount - 1 ? p <= hi : p < hi); }).length;
      counts.push(count);
    }

    var isDark = state.settings.theme === 'dark';
    state.chartInstances.priceDist = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Number of Stores',
          data: counts,
          backgroundColor: '#3b82f640',
          borderColor: '#3b82f6',
          borderWidth: 1,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            ticks: { color: isDark ? '#64748b' : '#94a3b8', maxRotation: 45, font: { size: 10 } },
            grid: { display: false },
          },
          y: {
            beginAtZero: true,
            ticks: { color: isDark ? '#64748b' : '#94a3b8', stepSize: 1 },
            grid: { color: isDark ? '#1f2330' : '#e2e8f0' },
          }
        }
      }
    });
  }

  // Demo data generators for when API has no history yet
  function generateDemoHistory(cc) {
    var stores = ['Amazon', 'Best Buy', 'Walmart'];
    var basePrice = 299;
    var points = [];
    var now = Date.now();
    stores.forEach(function (store) {
      var base = basePrice + Math.random() * 100;
      for (var d = 29; d >= 0; d--) {
        var date = new Date(now - d * 86400000).toISOString();
        var variation = (Math.random() - 0.5) * 40;
        points.push({ date: date, price: Math.round((base + variation) * 100) / 100, store: store, country: cc });
      }
    });
    return points;
  }

  function generateDemoPrices(cc) {
    var c = getCountry(cc);
    return [
      { store: 'Amazon', price: 299.99, condition: 'New', in_stock: true, link: '#', country: cc },
      { store: 'Best Buy', price: 319.99, condition: 'New', in_stock: true, link: '#', country: cc },
      { store: 'Walmart', price: 289.99, condition: 'New', in_stock: true, link: '#', country: cc },
      { store: 'Target', price: 309.99, condition: 'New', in_stock: false, link: '#', country: cc },
      { store: 'Newegg', price: 279.99, condition: 'New', in_stock: true, link: '#', country: cc },
      { store: 'eBay', price: 259.99, condition: 'Used', in_stock: true, link: '#', country: cc },
      { store: 'Adorama', price: 324.99, condition: 'Refurbished', in_stock: true, link: '#', country: cc },
      { store: 'B&H Photo', price: 299.00, condition: 'New', in_stock: true, link: '#', country: cc },
    ];
  }

  // ───────────────────────────────────────────────
  // Page: Settings
  // ───────────────────────────────────────────────
  function renderSettings() {
    // Load settings from localStorage
    var saved = localStorage.getItem('shopserp-settings');
    if (saved) {
      try {
        var parsed = JSON.parse(saved);
        Object.assign(state.settings, parsed);
      } catch (_) { /* ignore */ }
    }
    state.settings.theme = document.documentElement.getAttribute('data-theme') || 'dark';

    var countryCbs = COUNTRIES.map(function (c) {
      var checked = state.settings.activeCountries.includes(c.code) ? 'checked' : '';
      return '<label class="checkbox-label">' +
        '<input type="checkbox" name="settings-country" value="' + c.code + '" ' + checked + '>' +
        '<span class="cb-indicator"></span>' +
        '<span class="cb-text">' + c.flag + ' ' + escapeHtml(c.name) + '</span>' +
        '</label>';
    }).join('');

    var html = '<div class="page-enter">' +
      '<div class="page-header">' +
        '<h1 class="page-title">Settings</h1>' +
        '<p class="page-subtitle">Configure your ShopSerp instance</p>' +
      '</div>' +

      // Theme
      '<div class="settings-section">' +
        '<div class="settings-section-title">' +
          '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>' +
          'Appearance' +
        '</div>' +
        '<div class="settings-row">' +
          '<div><div class="settings-row-label">Dark Mode</div><div class="settings-row-desc">Switch between light and dark themes</div></div>' +
          '<div class="settings-row-value">' +
            '<label class="toggle"><input type="checkbox" id="settingsTheme"' + (state.settings.theme === 'dark' ? ' checked' : '') + '><span class="toggle-slider"></span></label>' +
          '</div>' +
        '</div>' +
      '</div>' +

      // Countries
      '<div class="settings-section">' +
        '<div class="settings-section-title">' +
          '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>' +
          'Active Countries' +
        '</div>' +
        '<p class="text-sm text-secondary mb-12">Select which countries to include in searches and monitoring by default.</p>' +
        '<div class="checkbox-group" id="settingsCountries">' + countryCbs + '</div>' +
      '</div>' +

      // Monitoring
      '<div class="settings-section">' +
        '<div class="settings-section-title">' +
          '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>' +
          'Monitoring' +
        '</div>' +
        '<div class="settings-row">' +
          '<div><div class="settings-row-label">Check Interval</div><div class="settings-row-desc">How often to check for price updates (in minutes)</div></div>' +
          '<div class="settings-row-value">' +
            '<select class="form-select" id="settingsInterval">' +
              '<option value="15"' + (state.settings.monitorInterval === 15 ? ' selected' : '') + '>Every 15 minutes</option>' +
              '<option value="30"' + (state.settings.monitorInterval === 30 ? ' selected' : '') + '>Every 30 minutes</option>' +
              '<option value="60"' + (state.settings.monitorInterval === 60 ? ' selected' : '') + '>Every hour</option>' +
              '<option value="360"' + (state.settings.monitorInterval === 360 ? ' selected' : '') + '>Every 6 hours</option>' +
              '<option value="720"' + (state.settings.monitorInterval === 720 ? ' selected' : '') + '>Every 12 hours</option>' +
              '<option value="1440"' + (state.settings.monitorInterval === 1440 ? ' selected' : '') + '>Daily</option>' +
            '</select>' +
          '</div>' +
        '</div>' +
      '</div>' +

      // Proxy
      '<div class="settings-section">' +
        '<div class="settings-section-title">' +
          '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>' +
          'Proxy Configuration' +
        '</div>' +
        '<div class="settings-row">' +
          '<div><div class="settings-row-label">Proxy URL</div><div class="settings-row-desc">HTTP(S) proxy for scraping requests (optional)</div></div>' +
          '<div class="settings-row-value">' +
            '<input type="text" class="form-input" id="settingsProxy" placeholder="http://user:pass@host:port" value="' + escapeHtml(state.settings.proxyUrl || '') + '">' +
          '</div>' +
        '</div>' +
      '</div>' +

      // Webhook
      '<div class="settings-section">' +
        '<div class="settings-section-title">' +
          '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>' +
          'Notifications' +
        '</div>' +
        '<div class="settings-row">' +
          '<div><div class="settings-row-label">Webhook URL</div><div class="settings-row-desc">Receive price alerts via webhook (Discord, Slack, custom)</div></div>' +
          '<div class="settings-row-value">' +
            '<input type="url" class="form-input" id="settingsWebhook" placeholder="https://hooks.slack.com/..." value="' + escapeHtml(state.settings.webhookUrl || '') + '">' +
          '</div>' +
        '</div>' +
      '</div>' +

      // Save
      '<div class="flex-between mt-20">' +
        '<button class="btn btn-secondary" id="settingsReset">Reset to Defaults</button>' +
        '<button class="btn btn-primary" id="settingsSave">' +
          '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>' +
          'Save Settings' +
        '</button>' +
      '</div>' +
    '</div>';

    $app.innerHTML = html;

    // Theme toggle
    document.getElementById('settingsTheme').addEventListener('change', function (e) {
      applyTheme(e.target.checked ? 'dark' : 'light');
    });

    // Save
    document.getElementById('settingsSave').addEventListener('click', saveSettings);
    document.getElementById('settingsReset').addEventListener('click', resetSettings);
  }

  async function saveSettings() {
    var checked = document.querySelectorAll('input[name="settings-country"]:checked');
    var countries = [];
    checked.forEach(function (cb) { countries.push(cb.value); });

    state.settings.activeCountries = countries;
    state.settings.monitorInterval = parseInt(document.getElementById('settingsInterval').value, 10);
    state.settings.proxyUrl = document.getElementById('settingsProxy').value.trim();
    state.settings.webhookUrl = document.getElementById('settingsWebhook').value.trim();

    // Save locally
    localStorage.setItem('shopserp-settings', JSON.stringify(state.settings));

    // Try saving to server
    try {
      await api('PUT', '/settings', {
        active_countries: state.settings.activeCountries,
        monitor_interval: state.settings.monitorInterval,
        proxy_url: state.settings.proxyUrl,
        webhook_url: state.settings.webhookUrl,
        theme: state.settings.theme,
      });
      showToast('Settings saved successfully', 'success');
    } catch (_) {
      // Still saved locally
      showToast('Settings saved locally (server unreachable)', 'warning');
    }
  }

  function resetSettings() {
    state.settings = {
      activeCountries: ['us', 'gb', 'au'],
      monitorInterval: 60,
      proxyUrl: '',
      webhookUrl: '',
      theme: state.settings.theme,
    };
    localStorage.setItem('shopserp-settings', JSON.stringify(state.settings));
    renderSettings();
    showToast('Settings reset to defaults', 'info');
  }

  // ───────────────────────────────────────────────
  // Init
  // ───────────────────────────────────────────────
  function init() {
    initTheme();

    // Load saved settings
    var saved = localStorage.getItem('shopserp-settings');
    if (saved) {
      try { Object.assign(state.settings, JSON.parse(saved)); } catch (_) { /* ignore */ }
    }

    // Load countries from API (fallback to built-in list)
    api('GET', '/countries').then(function (data) {
      // If server provides countries, we could merge them in
      // For now, we use our built-in list
    }).catch(function () {
      // Silently use built-in countries
    });

    handleRoute();

    // If no hash, default to search
    if (!window.location.hash || window.location.hash === '#' || window.location.hash === '#/') {
      window.location.hash = '#/search';
    }
  }

  init();
})();
