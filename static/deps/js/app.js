// =============================================
// ВЕСЬ ФУНКЦИОНАЛ APP: ВКЛАДКИ, ФИЛЬТРЫ, AJAX, МОДАЛКИ
// =============================================

document.addEventListener('DOMContentLoaded', function() {
    const body = document.body;
    const teamModal = document.getElementById('teamModal');
    const gameModal = document.getElementById('gameModal');
    
    // =============================================
    // ПАГИНАЦИЯ
    // =============================================

    /**
     * Обработчик клика по пагинации
     * Предотвращает стандартное поведение и загружает страницу через AJAX
     */
    function setupPaginationHandlers() {
        document.querySelectorAll('.pagination a').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Извлекаем номер страницы из URL
                const url = new URL(this.href);
                const page = url.searchParams.get('page');
                
                // Обновляем скрытое поле page в форме
                const pageInput = document.querySelector('input[name="page"]');
                if (pageInput) {
                    pageInput.value = page;
                } else {
                    // Создаем скрытое поле если его нет
                    const hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = 'page';
                    hiddenInput.value = page;
                    document.getElementById('filters').appendChild(hiddenInput);
                }
                
                // Загружаем контент с новой страницей
                const activeTab = document.querySelector('.main-tab.active').getAttribute('data-tab');
                loadTabContent(activeTab);
            });
        });
    }

/**
 * Удаляет параметр page из формы после загрузки
 * чтобы при следующих фильтрациях не сохранялся старый номер страницы
 */
function cleanupPageParam() {
    const pageInput = document.querySelector('input[name="page"]');
    if (pageInput) {
        pageInput.remove();
    }
}
    
    // =============================================
    // 1. БУРГЕР-МЕНЮ (для основной навигации сайта)
    // =============================================
    const navToggle = document.querySelector('.nav-btn');
    const navBar = document.querySelector('.navbar');

    /**
     * Закрывает бургер-меню на мобильных устройствах
     * Убирает активные классы и восстанавливает прокрутку body
     */
    function closeMenu() {
        if (navBar && navToggle) {
            navBar.classList.remove('active');
            navToggle.classList.remove('active');
            body.classList.remove('menu-open');
        }
    }

    // Обработчик клика по бургер-кнопке
    if (navToggle && navBar) {
        navToggle.addEventListener('click', function() {
            navBar.classList.toggle('active');
            navToggle.classList.toggle('active');
            body.classList.toggle('menu-open');
        });
    }

    // Закрытие меню при ресайзе окна и на десктопе
    window.addEventListener('resize', closeMenu);
    if (window.innerWidth >= 768) closeMenu();

    // =============================================
    // 2. ФУНКЦИИ ДЛЯ МОДАЛОК
    // =============================================
    
    /**
     * Показывает модальное окно с индикатором загрузки
     * @param {HTMLElement} modal - DOM-элемент модального окна
     * @param {string} message - Сообщение для отображения во время загрузки
     */
    function showModalWithLoader(modal, message) {
        modal.querySelector('.modal-content').innerHTML = `<div class="loading">${message}</div>`;
        modal.classList.add('active');
        body.style.overflow = 'hidden';
    }

    /**
     * Скрывает модальное окно и восстанавливает прокрутку страницы
     * @param {HTMLElement} modal - DOM-элемент модального окна
     */
    function hideModal(modal) {
        modal.classList.remove('active');
        body.style.overflow = '';
    }

    /**
     * Показывает сообщение об ошибке в модальном окне
     * @param {HTMLElement} modal - DOM-элемент модального окна
     * @param {string} message - Текст ошибки
     */
    function showError(modal, message) {
        modal.querySelector('.modal-content').innerHTML = `<div class="error">${message}</div>`;
    }

    // =============================================
    // 3. ФУНКЦИИ ДЛЯ ФИЛЬТРОВ
    // =============================================
    
    /**
     * Показывает только фильтры, относящиеся к вкладке "Команды"
     * Скрывает фильтры для игр
     */
    function showTeamFilters() {
        document.querySelectorAll('.team-only').forEach(el => el.style.display = "block");
        document.querySelectorAll('.game-only').forEach(el => el.style.display = "none");
    }

    /**
     * Показывает только фильтры, относящиеся к вкладке "Игры"
     * Скрывает фильтры для команд
     */
    function showGameFilters() {
        document.querySelectorAll('.team-only').forEach(el => el.style.display = "none");
        document.querySelectorAll('.game-only').forEach(el => el.style.display = "block");
    }

    /**
     * Обновляет видимость фильтров в зависимости от активной вкладки
     * Вызывается при переключении вкладок и инициализации
     */
    function updateFilterVisibility() {
        const activeTab = document.getElementById('active_tab').value;
        if (activeTab === 'teams') showTeamFilters();
        else if (activeTab === 'games') showGameFilters();
    }

    // =============================================
    // 4. AJAX ДЛЯ МОДАЛОК
    // =============================================
    
    /**
     * Загружает содержимое модального окна для команды через AJAX
     * @param {number} teamId - ID команды для загрузки
     */
    function loadTeamModal(teamId) {
        showModalWithLoader(teamModal, 'Загрузка данных команды...');
        fetch(`/team/${teamId}/modal/`)
            .then(response => response.ok ? response.text() : Promise.reject(response.status))
            .then(html => teamModal.querySelector('.modal-content').innerHTML = html)
            .catch(error => showError(teamModal, `Ошибка загрузки команды: ${error}`));
    }

    /**
     * Загружает содержимое модального окна для игры через AJAX
     * @param {number} gameId - ID игры для загрузки
     */
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
    
    /**
     * Привязывает обработчики событий к элементам
     * Особенно важно вызывать после AJAX-обновления таблиц,
     * так как старые элементы заменяются новыми
     */
    function attachEventHandlers() {
        // Обработчики для строк таблиц (обновляются при AJAX)
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
    
    /**
     * Синхронизирует значение поиска из видимого поля в скрытое поле формы
     * Нужно потому что видимое поле поиска не находится внутри формы фильтров
     */
    function updateSearchInForm() {
        const searchInput = document.getElementById('search-input');
        const formSearch = document.querySelector('input[name="search"]');
        
        if (searchInput && formSearch) {
            formSearch.value = searchInput.value.trim();
        }
    }

    /**
     * Загружает контент для активной вкладки через AJAX
     * Основная функция для обновления таблиц без перезагрузки страницы
     */
    function loadActiveTabContent() {
        const activeTab = document.querySelector('.main-tab.active').getAttribute('data-tab');
        loadTabContent(activeTab);
    }

    /**
     * Переключает визуальное состояние вкладок и обновляет UI
     * @param {string} tabName - Название вкладки ('teams' или 'games')
     */
    function switchTab(tabName) {
        // Обновляем визуально активную вкладку
        document.querySelectorAll('.main-tab').forEach(tab => tab.classList.remove('active'));
        document.querySelector(`.main-tab[data-tab="${tabName}"]`).classList.add('active');
        
        // Обновляем скрытое поле для отправки на сервер
        document.getElementById('active_tab').value = tabName;
        
        // Показываем соответствующую таблицу
        document.querySelectorAll('.table-wrapper').forEach(wrapper => {
            wrapper.classList.remove('active');
            if (wrapper.id === tabName + '-table') wrapper.classList.add('active');
        });
        
        // Переключаем видимость фильтров
        updateFilterVisibility();
    }

    /**
     * Основная функция загрузки контента вкладки через AJAX
     * @param {string} tabName - Название вкладки для загрузки
     */
    function loadTabContent(tabName) {
        const tablesContainer = document.getElementById('ajax-content');
        tablesContainer.innerHTML = '<div class="loading">Загрузка...</div>';

        // Обновляем значение active_tab в форме перед отправкой
        document.getElementById('active_tab').value = tabName;

        const formData = new FormData(document.getElementById('filters'));

        fetch(`?${new URLSearchParams(formData)}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.ok ? response.text() : Promise.reject(response.status))
        .then(html => {
            tablesContainer.innerHTML = html;
            switchTab(tabName);
            attachEventHandlers();
            setupPaginationHandlers();
            cleanupPageParam();
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
    
    // Обработчики клика по вкладкам "Команды" и "Игры"
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
            
            // Сбрасываем пагинацию при изменении фильтров
            const pageInput = document.querySelector('input[name="page"]');
            if (pageInput) {
                pageInput.value = 1;
            }
            
            updateSearchInForm();
            const activeTab = document.querySelector('.main-tab.active').getAttribute('data-tab');
            loadTabContent(activeTab);
        });
    }

    // =============================================
    // 9. ОБРАБОТЧИКИ ЗАКРЫТИЯ МОДАЛОК
    // =============================================
    
    // Закрытие модалок по клику на оверлей
    document.querySelectorAll('.modal-overlay').forEach(btn => {
        btn.addEventListener('click', () => { hideModal(teamModal); hideModal(gameModal); });
    });

    // Закрытие модалок по клавише Escape
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') { hideModal(teamModal); hideModal(gameModal); }
    });

    // Закрытие модалок по клику на кнопку закрытия
    document.addEventListener('click', e => {
        if (e.target.classList.contains('close-modal')) { hideModal(teamModal); hideModal(gameModal); }
    });

    // =============================================
    // 10. ОЧИСТКА URL
    // =============================================
    
    /**
     * Очищает URL браузера от пустых GET-параметров
     * Удаляет все параметры с пустыми значениями для красоты
     */
    function cleanUrl() {
        const url = new URL(window.location);
        const params = new URLSearchParams(url.search);
        
        for (const [key, value] of params) {
            if (value === '' || key === 'page') params.delete(key);
        }
        
        if (params.toString() !== url.searchParams.toString()) {
            window.history.replaceState({}, '', `${url.pathname}?${params.toString()}`);
        }
    }

    // =============================================
    // 11. ОБРАБОТЧИКИ ПОИСКА 
    // =============================================
    
    /**
     * Настраивает обработчики для поиска: кнопка, Enter, очистка
     */
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
    // 12. ИНИЦИАЛИЗАЦИЯ ПРИ ЗАГРУЗКЕ
    // =============================================
    
    // Первоначальная настройка при загрузке страницы
    attachEventHandlers();
    setupPaginationHandlers()
    setupSearchHandlers();
    updateFilterVisibility();
    cleanUrl();
    
    // Синхронизация поискового запроса при загрузке страницы
    if (document.getElementById('search-input') && document.querySelector('input[name="search"]')) {
        document.getElementById('search-input').value = document.querySelector('input[name="search"]').value;
    }
});

// =============================================
// ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ФИЛЬТРА ДАТ
// =============================================

// Открытие/закрытие выпадающего меню фильтра дат
document.querySelectorAll('.period-toggle').forEach(button => {
    button.addEventListener('click', function(e) {
        e.stopPropagation();
        const periodFields = this.closest('.period-filter').querySelector('.period-fields');
        periodFields.classList.toggle('show');
    });
});

// Закрытие при клике вне области фильтра дат
document.addEventListener('click', function(e) {
    if (!e.target.closest('.period-filter')) {
        document.querySelectorAll('.period-fields').forEach(fields => {
            fields.classList.remove('show');
        });
    }
});

/**
 * Обновляет текст кнопки фильтра дат при выборе дат
 * Показывает выбранный диапазон дат на кнопке
 */
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

// Слушаем изменения date input для обновления кнопки
document.querySelectorAll('input[type="date"]').forEach(input => {
    input.addEventListener('change', updatePeriodButton);
});

// Инициализация текста кнопки при загрузке
document.addEventListener('DOMContentLoaded', updatePeriodButton);

// Очистка всех дат в фильтре
document.querySelector('.clear-dates-btn').addEventListener('click', function() {
    document.getElementById('date_from').value = '';
    document.getElementById('date_to').value = '';
    updatePeriodButton();
    document.getElementById('filters').dispatchEvent(new Event('submit'));
});


