// =============================================
// ВЕСЬ ФУНКЦИОНАЛ APP: ВКЛАДКИ, ФИЛЬТРЫ, AJAX, МОДАЛКИ
// =============================================

document.addEventListener('DOMContentLoaded', function() {
    const body = document.body;
    const teamModal = document.getElementById('teamModal');
    const gameModal = document.getElementById('gameModal');
    // Глобальная переменная для хранения примененных фильтров. Использую чтобы избежать ошибки, при котором в loadTeamModal загружались не примененные фильтры.
    let appliedFilters = {};
    // Инициализируем appliedFilters из URL при загрузке страницы
    const urlParams = new URLSearchParams(window.location.search);
    appliedFilters = {};
    ['game_series', 'date_from', 'date_to', 'city', 'search'].forEach(key => {
        const value = urlParams.get(key);
        if (value) {
            appliedFilters[key] = value;
        }
    });
    
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
        // Используем сохраненные примененные фильтры
        const params = new URLSearchParams();
        const filterKeys = ['game_series', 'date_from', 'date_to'];
        
        filterKeys.forEach(key => {
            if (appliedFilters[key]) {
                params.append(key, appliedFilters[key]);
            }
        });
        
        // Добавляем остальные параметры из URL (active_tab и т.д.)
        const urlParams = new URLSearchParams(window.location.search);
        ['active_tab', 'search', 'city'].forEach(key => {
            const value = urlParams.get(key);
            if (value) params.append(key, value);
        });
        
        const url = `/team/${teamId}/modal/?${params.toString()}`;
        
        showModalWithLoader(teamModal, 'Загрузка данных команды...');
        fetch(url)
            .then(response => response.ok ? response.text() : Promise.reject(response.status))
            .then(html => {
                teamModal.querySelector('.modal-content').innerHTML = html;
                setTimeout(initRadarChart, 100);
            })
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
        // Обработчики для строк таблиц(открытие модального окна) (обновляются при AJAX)
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
            
            // Сохраняем текущие фильтры
            updateAppliedFilters();
            
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

    // Функция для сохранения текущих фильтров
    function updateAppliedFilters() {
        const formData = new FormData(document.getElementById('filters'));
        appliedFilters = {};
        
        // Сохраняем только нужные параметры фильтрации
        const filterKeys = ['game_series', 'date_from', 'date_to', 'city', 'search'];
        filterKeys.forEach(key => {
            const value = formData.get(key);
            if (value) {
                appliedFilters[key] = value;
            }
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
    } else if (dateFrom.value) {
        const from = new Date(dateFrom.value).toLocaleDateString('ru-RU');
        button.innerHTML = `<i class="fas fa-calendar"></i> С ${from}`;
    } else if (dateTo.value) {
        const to = new Date(dateTo.value).toLocaleDateString('ru-RU');
        button.innerHTML = `<i class="fas fa-calendar"></i> По ${to}`;
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

// Обработчик кнопки сброса
document.getElementById('reset-filters').addEventListener('click', function() {
    // Сбрасываем значения всех полей формы
    document.getElementById('filters').reset();
    
    // Очищаем поля дат вручную
    document.getElementById('date_from').value = '';
    document.getElementById('date_to').value = '';
    
    // Сбрасываем скрытое поле поиска
    document.querySelector('input[name="search"]').value = '';
    
    // Сбрасываем поле поиска в UI
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = '';
    }
    
    // Сбрасываем appliedFilters
    appliedFilters = {};
    
    // Обновляем текст кнопки периода
    updatePeriodButton();
    
    // ★ ВАЖНО: Отправляем форму как при нажатии "Применить" ★
    document.getElementById('filters').dispatchEvent(new Event('submit'));
});


// =============================================
// 14. ИНИЦИАЛИЗАЦИЯ РАДАР-ЧАРТА
// =============================================

function initRadarChart() {
    // Находим элемент canvas для диаграммы по его ID
    const radarCanvas = document.getElementById('topicRadarChart');
    // Если элемент не найден, выходим из функции
    if (!radarCanvas) return;

    // === ДАННЫЕ ДЛЯ ДИАГРАММЫ ===
    const labels = radarCanvas.dataset.labels.split(',');          
    const rawValues = radarCanvas.dataset.values.split(',').map(Number); 
    const fullNames = radarCanvas.dataset.fullnames.split(',');    

    // === ОКРУГЛЕНИЕ ДЛЯ ОТОБРАЖЕНИЯ (до 0.5) ===
    const displayValues = rawValues.map(value => {
        // Округляем до ближайшего 0.5
        const rounded = Math.round(value * 2) / 2;
        // Ограничиваем максимальное значение 5 для отображения
        return Math.min(rounded, 5);
    });   

    // === НАСТРОЙКИ МАСШТАБА ДИАГРАММЫ ===
    const minValue = 0;   // Минимальное значение на шкале (центр диаграммы)
    const maxValue = 5;   // Максимальное значение на шкале (внешний круг)

    // === СОЗДАНИЕ И НАСТРОЙКА ДИАГРАММЫ ===
    new Chart(radarCanvas, {
        type: 'radar',   // Тип диаграммы: радарная (паутинная)
        data: {
            labels: labels,   // Подписи для осей (короткие названия тем)
            datasets: [{
                label: 'Средний балл по темам', // Название набора данных
                data: displayValues, // ★ ВОТ ЗДЕСЬ ПЕРЕДАЮТСЯ ДАННЫЕ ★ - числовые значения для отображения
                borderColor: '#7c4dff',                 // Цвет линии диаграммы
                backgroundColor: 'rgba(124, 77, 255, 0.25)', // Цвет заливки области
                pointBackgroundColor: '#7c4dff',        // Цвет точек данных
                pointBorderColor: '#fff',               // Цвет обводки точек
                pointHoverBackgroundColor: '#fff',      // Цвет точек при наведении
                pointHoverBorderColor: '#7c4dff',       // Цвет обводки при наведении
                pointRadius: 3.5,   // Размер точек в пикселях
                pointHoverRadius: 5, // Размер точек при наведении
                fill: true,         // Закрашивать область под линией
                borderWidth: 2.8    // Толщина линии в пикселях
            }]
        },
        options: {
            responsive: true,          // Диаграмма адаптируется к размеру контейнера
            maintainAspectRatio: false, // Не сохранять пропорции (занимает всё доступное пространство)
            scales: {
                r: { // Настройки радиальной (круговой) шкалы
                    angleLines: { // Линии, идущие от центра к краям (оси)
                        color: 'rgba(255, 255, 255, 0.2)', // Цвет осей
                        lineWidth: 1 // Толщина линий осей
                    },
                    grid: { // Круговые линии сетки (концентрические круги)
                        color: 'rgba(255, 255, 255, 0.1)', // Цвет линий сетки
                        lineWidth: 1.2 // Толщина линий сетки
                    },
                    pointLabels: { // Подписи тем на концах осей
                        color: '#e6ddff', // Цвет текста подписей
                        font: {
                            size: 16, // Размер шрифта подписей
                            weight: 'bold', // Жирность шрифта
                            family: 'Arial, sans-serif' // Шрифт
                        },
                        padding: 10 // Отступ подписей от края
                    },
                    ticks: { // Деления и подписи значений на шкале
                        stepSize: 0.5,     // Шаг между делениями (0.5 балла)
                        display: false,    // Не показывать числовые подписи на шкале
                        backdropColor: 'transparent', // Цвет фона подписей
                        font: {
                            size: 10,     // Размер шрифта числовых подписей
                        },
                        // Функция форматирования числовых значений
                        callback: function(value) {
                            return value.toFixed(1); // Отображать числа с одной decimal (0.0, 0.5, 1.0 и т.д.)
                        }
                    },
                    min: minValue,       // Минимальное значение шкалы
                    max: maxValue,       // Максимальное значение шкалы
                    suggestedMax: maxValue // Рекомендуемый максимум (исключает автоматическое расширение)
                }
            },
            plugins: {
                legend: {
                    display: false // Скрыть легенду диаграммы
                },
                tooltip: { // Настройки всплывающих подсказок
                    usePointStyle: true, // Использовать стиль точек вместо квадратиков
                    callbacks: {
                        // Функция для заголовка подсказки
                        title: function(tooltipItems) { 
                            const index = tooltipItems[0].dataIndex; // Получаем индекс данных
                            return fullNames[index]; // Возвращаем полное название темы
                        },
                        // Функция для основного текста подсказки
                        label: function(context) { 
                            const index = context.dataIndex; // Получаем индекс данных
                            // ★ ВОТ ЗДЕСЬ ИСПОЛЬЗУЮТСЯ ДАННЫЕ ДЛЯ ПОДСКАЗОК ★
                            return `Средний балл: ${rawValues[index].toFixed(1)}`;
                        },
                        // Функция для стиля точки в подсказке
                        labelPointStyle: function() { 
                            return {
                                pointStyle: 'circle', // Форма точки - круг
                                rotation: 0,          // Без вращения
                                borderColor: '#7c4dff', // Цвет обводки
                                backgroundColor: '#7c4dff' // Цвет заливки
                            };
                        }
                    },
                    backgroundColor: 'rgba(31, 15, 58, 0.95)', // Цвет фона подсказки
                    titleColor: '#fff', // Цвет заголовка подсказки
                    bodyColor: '#e6ddff', // Цвет основного текста подсказки
                    borderColor: '#7c4dff', // Цвет рамки подсказки
                    borderWidth: 1, // Толщина рамки
                    cornerRadius: 10, // Скругление углов
                    titleFont: { size: 14, weight: 'bold' }, // Шрифт заголовка
                    bodyFont: { size: 13 }, // Шрифт основного текста
                    padding: 12, // Внутренние отступы
                    boxPadding: 6, // Отступы вокруг элементов
                    boxWidth: 8, // Ширина box'ов
                    boxHeight: 8 // Высота box'ов
                }
            }
        }
    });
}