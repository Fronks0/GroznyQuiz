// =============================================
// ВЕСЬ ФУНКЦИОНАЛ APP: ВКЛАДКИ, ФИЛЬТРЫ, AJAX, МОДАЛКИ
// =============================================

document.addEventListener('DOMContentLoaded', function() {
    const body = document.body;
    const teamModal = document.getElementById('teamModal');
    const gameModal = document.getElementById('gameModal');
    
    // =============================================
    // 1. БУРГЕР-МЕНЮ
    // =============================================
    const navToggle = document.querySelector('.nav-btn');
    const navBar = document.querySelector('.navbar');

    function closeMenu() {
        if (navBar && navToggle) {
            navBar.classList.remove('active');
            navToggle.classList.remove('active');
            body.classList.remove('menu-open');
        }
    }

    if (navToggle && navBar) {
        navToggle.addEventListener('click', function() {
            navBar.classList.toggle('active');
            navToggle.classList.toggle('active');
            body.classList.toggle('menu-open');
        });
    }

    window.addEventListener('resize', closeMenu);
    if (window.innerWidth >= 768) closeMenu();

    // =============================================
    // 2. ФУНКЦИИ ДЛЯ МОДАЛОК
    // =============================================
    function showModalWithLoader(modal, message) {
        modal.querySelector('.modal-content').innerHTML = `<div class="loading">${message}</div>`;
        modal.classList.add('active');
        body.style.overflow = 'hidden';
    }

    function hideModal(modal) {
        modal.classList.remove('active');
        body.style.overflow = '';
    }

    function showError(modal, message) {
        modal.querySelector('.modal-content').innerHTML = `<div class="error">${message}</div>`;
    }

    // =============================================
    // 3. ФУНКЦИИ ДЛЯ ФИЛЬТРОВ
    // =============================================
    function showTeamFilters() {
        document.querySelectorAll('.team-only').forEach(el => el.style.display = "block");
        document.querySelectorAll('.game-only').forEach(el => el.style.display = "none");
    }

    function showGameFilters() {
        document.querySelectorAll('.team-only').forEach(el => el.style.display = "none");
        document.querySelectorAll('.game-only').forEach(el => el.style.display = "block");
    }

    function updateFilterVisibility() {
        const activeTab = document.getElementById('active_tab').value;
        if (activeTab === 'teams') showTeamFilters();
        else if (activeTab === 'games') showGameFilters();
    }

    // =============================================
    // 4. AJAX ДЛЯ МОДАЛОК
    // =============================================
    function loadTeamModal(teamId) {
        showModalWithLoader(teamModal, 'Загрузка данных команды...');
        fetch(`/team/${teamId}/modal/`)
            .then(response => response.ok ? response.text() : Promise.reject(response.status))
            .then(html => teamModal.querySelector('.modal-content').innerHTML = html)
            .catch(error => showError(teamModal, `Ошибка загрузки команды: ${error}`));
    }

    function loadGameModal(gameId) {
        showModalWithLoader(gameModal, 'Загрузка данных игры...');
        fetch(`/game/${gameId}/modal/`)
            .then(response => response.ok ? response.text() : Promise.reject(response.status))
            .then(html => gameModal.querySelector('.modal-content').innerHTML = html)
            .catch(error => showError(gameModal, `Ошибка загрузки игры: ${error}`));
    }

// =============================================
// 5. ОБРАБОТЧИКИ СОБЫТИЙ
// =============================================
function attachEventHandlers() {
    // ТОЛЬКО обработчики для строк таблиц (они обновляются при AJAX)
    document.querySelectorAll('.team-row').forEach(row => {
        row.addEventListener('click', () => loadTeamModal(row.getAttribute('data-team-id')));
    });
    
    document.querySelectorAll('.game-row').forEach(row => {
        row.addEventListener('click', () => loadGameModal(row.getAttribute('data-game-id')));
    });
}


    // =============================================
    // 6. УПРАВЛЕНИЕ ВКЛАДКАМИ И AJAX
    // =============================================
    function updateSearchInForm() {
    const searchInput = document.getElementById('search-input');
    const formSearch = document.querySelector('input[name="search"]');
    
    if (searchInput && formSearch) {
        formSearch.value = searchInput.value.trim();}
    }

    function loadActiveTabContent() {
        const activeTab = document.querySelector('.main-tab.active').getAttribute('data-tab');
        loadTabContent(activeTab);
    }

    function switchTab(tabName) {
        // Обновляем визуально
        document.querySelectorAll('.main-tab').forEach(tab => tab.classList.remove('active'));
        document.querySelector(`.main-tab[data-tab="${tabName}"]`).classList.add('active');
        
        // Обновляем скрытое поле
        document.getElementById('active_tab').value = tabName;
        
        // Показываем соответствующую таблицу
        document.querySelectorAll('.table-wrapper').forEach(wrapper => {
            wrapper.classList.remove('active');
            if (wrapper.id === tabName + '-table') wrapper.classList.add('active');
        });
        
        // Переключаем фильтры
        updateFilterVisibility();
    }

    function loadTabContent(tabName) {
        const tablesContainer = document.getElementById('ajax-content');
        tablesContainer.innerHTML = '<div class="loading">Загрузка...</div>';
        
        const formData = new FormData(document.getElementById('filters'));
        
        fetch(`?${new URLSearchParams(formData)}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.ok ? response.text() : Promise.reject(response.status))
        .then(html => {
            tablesContainer.innerHTML = html;
            switchTab(tabName);
            attachEventHandlers();
            cleanUrl();
        })
        .catch(error => {
            console.error('Load error:', error);
            tablesContainer.innerHTML = `<div class="error">Ошибка загрузки</div>`;
        });
    }

    // =============================================
    // 7. ИНИЦИАЛИЗАЦИЯ ВКЛАДОК
    // =============================================
    document.querySelectorAll('.main-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            loadTabContent(tabName);
        });
    });

    // =============================================
    // 8. AJAX ФИЛЬТРАЦИЯ
    // =============================================
    const filterForm = document.getElementById('filters');
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            updateSearchInForm();   // <<< сначала обновляем скрытое поле "search"
            const activeTab = document.querySelector('.main-tab.active').getAttribute('data-tab');
            loadTabContent(activeTab); // загружаем контент с учетом поиска и фильтров
        });
    }

    // =============================================
    // 9. ОБРАБОТЧИКИ ЗАКРЫТИЯ МОДАЛОК
    // =============================================
    document.querySelectorAll('.modal-overlay').forEach(btn => {
        btn.addEventListener('click', () => { hideModal(teamModal); hideModal(gameModal); });
    });

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') { hideModal(teamModal); hideModal(gameModal); }
    });

    document.addEventListener('click', e => {
        if (e.target.classList.contains('close-modal')) { hideModal(teamModal); hideModal(gameModal); }
    });

    // =============================================
    // 10. ОЧИСТКА URL
    // =============================================
    function cleanUrl() {
        const url = new URL(window.location);
        const params = new URLSearchParams(url.search);
        
        for (const [key, value] of params) {
            if (value === '') params.delete(key);
        }
        
        if (params.toString() !== url.searchParams.toString()) {
            window.history.replaceState({}, '', `${url.pathname}?${params.toString()}`);
        }
    }

    // =============================================
// 12. ОБРАБОТЧИКИ ПОИСКА 
// =============================================
    function setupSearchHandlers() {
        const searchInput = document.getElementById('search-input');
        const searchButton = document.getElementById('search-button');
        const clearSearch = document.querySelector('.clear-search');

        // Поиск по кнопке
        if (searchButton) {
            searchButton.addEventListener('click', function(e) {
                e.preventDefault();
                updateSearchInForm();
                loadActiveTabContent();
            });
        }

        // Поиск по Enter
        if (searchInput) {
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    updateSearchInForm();
                    loadActiveTabContent();
                }
            });
        }

        // Очистка поиска
        if (clearSearch) {
            clearSearch.addEventListener('click', function(e) {
                e.preventDefault();
                if (searchInput) {
                    searchInput.value = '';
                    updateSearchInForm();
                    loadActiveTabContent();
                }
            });
        }
    }

    // =============================================
    // 11. ИНИЦИАЛИЗАЦИЯ ПРИ ЗАГРУЗКЕ
    // =============================================
    attachEventHandlers();
    setupSearchHandlers();
    updateFilterVisibility();
    cleanUrl();
    

    if (document.getElementById('search-input') && document.querySelector('input[name="search"]')) {
        document.getElementById('search-input').value = document.querySelector('input[name="search"]').value;
    }
});






// Открытие/закрытие выпадающего меню
document.querySelectorAll('.period-toggle').forEach(button => {
    button.addEventListener('click', function(e) {
        e.stopPropagation();
        const periodFields = this.closest('.period-filter').querySelector('.period-fields');
        periodFields.classList.toggle('show');
    });
});

// Закрытие при клике вне области
document.addEventListener('click', function(e) {
    if (!e.target.closest('.period-filter')) {
        document.querySelectorAll('.period-fields').forEach(fields => {
            fields.classList.remove('show');
        });
    }
});

// Обновление текста кнопки при выборе дат
function updatePeriodButton() {
    const dateFrom = document.querySelector('input[name="date_from"]');
    const dateTo = document.querySelector('input[name="date_to"]');
    const button = document.querySelector('.period-toggle');
    
    if (dateFrom.value && dateTo.value) {
        const from = new Date(dateFrom.value).toLocaleDateString('ru-RU');
        const to = new Date(dateTo.value).toLocaleDateString('ru-RU');
        button.innerHTML = `<i class="fas fa-calendar"></i> ${from} - ${to}`;
    } else {
        button.innerHTML = `<i class="fas fa-sliders-h"></i> Выбрать`;
    }
}

// Слушаем изменения date input
document.querySelectorAll('input[type="date"]').forEach(input => {
    input.addEventListener('change', updatePeriodButton);
});

// Инициализация
document.addEventListener('DOMContentLoaded', updatePeriodButton);

// Очистка всех дат
document.querySelector('.clear-dates-btn').addEventListener('click', function() {
    document.getElementById('date_from').value = '';
    document.getElementById('date_to').value = '';
    updatePeriodButton();
    document.getElementById('filters').dispatchEvent(new Event('submit'));
});