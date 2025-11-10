// photos/static/photos/js/ui.js
// UI утилиты для работы с интерфейсом

const UI = {
    // ========== Toast Notifications ==========

    /**
     * Показать уведомление (toast)
     * @param {string} message - Текст сообщения
     * @param {string} type - Тип: 'success', 'error', 'info', 'warning'
     * @param {number} duration - Длительность в мс (по умолчанию 3000)
     */
    showToast(message, type = 'info', duration = 3000) {
        // Проверяем, есть ли уже контейнер для toast
        let toastContainer = document.getElementById('toast-container');

        if (!toastContainer) {
            // Создаем контейнер
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 10px;
            `;
            document.body.appendChild(toastContainer);
        }

        // Создаем toast элемент
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        // Цвета для разных типов
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            info: '#3b82f6',
            warning: '#f59e0b'
        };

        toast.style.cssText = `
            background-color: ${colors[type] || colors.info};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            max-width: 350px;
            animation: slideIn 0.3s ease-out;
            cursor: pointer;
            font-size: 14px;
            line-height: 1.5;
        `;

        toast.textContent = message;

        // Добавляем анимацию
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        if (!document.getElementById('toast-styles')) {
            style.id = 'toast-styles';
            document.head.appendChild(style);
        }

        // Функция для удаления toast
        const removeToast = () => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                toast.remove();
                // Удаляем контейнер, если пустой
                if (toastContainer.children.length === 0) {
                    toastContainer.remove();
                }
            }, 300);
        };

        // Удаление по клику
        toast.addEventListener('click', removeToast);

        // Автоматическое удаление
        if (duration > 0) {
            setTimeout(removeToast, duration);
        }

        toastContainer.appendChild(toast);

        return toast;
    },

    // ========== Loading States ==========

    /**
     * Установить состояние загрузки для элемента
     * @param {HTMLElement} element - DOM элемент
     * @param {boolean} isLoading - Флаг загрузки
     * @param {string} loadingText - Текст для отображения при загрузке
     */
    setLoading(element, isLoading, loadingText = '') {
        if (!element) return;

        if (isLoading) {
            element.style.opacity = '0.6';
            element.style.pointerEvents = 'none';
            element.style.cursor = 'wait';

            // Добавляем data-атрибут для отслеживания
            element.dataset.loading = 'true';

            // Если это кнопка, сохраняем оригинальный текст и меняем его
            if (element.tagName === 'BUTTON' && loadingText) {
                element.dataset.originalText = element.textContent;
                element.textContent = loadingText;
            }

            // Отключаем элемент, если это input или button
            if (element.tagName === 'INPUT' || element.tagName === 'BUTTON' || element.tagName === 'TEXTAREA') {
                element.disabled = true;
            }
        } else {
            element.style.opacity = '1';
            element.style.pointerEvents = 'auto';
            element.style.cursor = '';

            delete element.dataset.loading;

            // Восстанавливаем оригинальный текст кнопки
            if (element.tagName === 'BUTTON' && element.dataset.originalText) {
                element.textContent = element.dataset.originalText;
                delete element.dataset.originalText;
            }

            // Включаем элемент обратно
            if (element.tagName === 'INPUT' || element.tagName === 'BUTTON' || element.tagName === 'TEXTAREA') {
                element.disabled = false;
            }
        }
    },

    /**
     * Добавить спиннер загрузки к элементу
     * @param {HTMLElement} element - DOM элемент
     * @returns {HTMLElement} Созданный спиннер
     */
    addSpinner(element) {
        if (!element) return null;

        const spinner = document.createElement('div');
        spinner.className = 'ui-spinner';
        spinner.style.cssText = `
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
            margin-left: 8px;
        `;

        // Добавляем анимацию спиннера
        const style = document.createElement('style');
        style.textContent = `
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        `;
        if (!document.getElementById('spinner-styles')) {
            style.id = 'spinner-styles';
            document.head.appendChild(style);
        }

        element.appendChild(spinner);
        return spinner;
    },

    /**
     * Удалить спиннер из элемента
     * @param {HTMLElement} element - DOM элемент
     */
    removeSpinner(element) {
        if (!element) return;

        const spinner = element.querySelector('.ui-spinner');
        if (spinner) {
            spinner.remove();
        }
    },

    // ========== Confirmation Dialogs ==========

    /**
     * Показать диалог подтверждения
     * @param {string} message - Текст сообщения
     * @param {string} confirmText - Текст кнопки подтверждения
     * @param {string} cancelText - Текст кнопки отмены
     * @returns {Promise<boolean>} Promise с результатом
     */
    confirm(message, confirmText = 'OK', cancelText = 'Отмена') {
        return new Promise((resolve) => {
            // Пока используем нативный confirm, можно позже заменить на кастомный
            const result = window.confirm(message);
            resolve(result);
        });
    },

    // ========== Image Utilities ==========

    /**
     * Установить состояние загрузки для изображения
     * @param {HTMLImageElement} img - Элемент изображения
     * @param {boolean} isLoading - Флаг загрузки
     */
    setImageLoading(img, isLoading) {
        if (!img) return;

        if (isLoading) {
            img.style.opacity = '0.5';
            img.style.filter = 'blur(2px)';

            // Добавляем overlay со спиннером
            const container = img.parentElement;
            if (container && !container.querySelector('.image-loading-overlay')) {
                const overlay = document.createElement('div');
                overlay.className = 'image-loading-overlay';
                overlay.style.cssText = `
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: rgba(255, 255, 255, 0.7);
                    z-index: 10;
                `;

                const spinner = document.createElement('div');
                spinner.style.cssText = `
                    width: 40px;
                    height: 40px;
                    border: 4px solid rgba(0, 0, 0, 0.1);
                    border-top-color: #3b82f6;
                    border-radius: 50%;
                    animation: spin 0.8s linear infinite;
                `;

                overlay.appendChild(spinner);
                container.style.position = 'relative';
                container.appendChild(overlay);
            }
        } else {
            img.style.opacity = '1';
            img.style.filter = '';

            // Удаляем overlay
            const container = img.parentElement;
            if (container) {
                const overlay = container.querySelector('.image-loading-overlay');
                if (overlay) {
                    overlay.remove();
                }
            }
        }
    },

    // ========== Scroll Utilities ==========

    /**
     * Плавная прокрутка к элементу
     * @param {HTMLElement|string} elementOrSelector - Элемент или селектор
     * @param {object} options - Опции прокрутки
     */
    scrollTo(elementOrSelector, options = {}) {
        const element = typeof elementOrSelector === 'string'
            ? document.querySelector(elementOrSelector)
            : elementOrSelector;

        if (!element) return;

        const defaultOptions = {
            behavior: 'smooth',
            block: 'center',
            inline: 'nearest'
        };

        element.scrollIntoView({ ...defaultOptions, ...options });
    },

    // ========== Form Utilities ==========

    /**
     * Получить данные формы как объект
     * @param {HTMLFormElement} form - Форма
     * @returns {object} Объект с данными формы
     */
    getFormData(form) {
        if (!form) return {};

        const formData = new FormData(form);
        const data = {};

        for (let [key, value] of formData.entries()) {
            // Если ключ уже существует, создаем массив
            if (data[key]) {
                if (!Array.isArray(data[key])) {
                    data[key] = [data[key]];
                }
                data[key].push(value);
            } else {
                data[key] = value;
            }
        }

        return data;
    },

    /**
     * Очистить форму
     * @param {HTMLFormElement} form - Форма
     */
    clearForm(form) {
        if (!form) return;
        form.reset();
    },

    // ========== Element Utilities ==========

    /**
     * Показать/скрыть элемент
     * @param {HTMLElement} element - DOM элемент
     * @param {boolean} show - Показать или скрыть
     * @param {string} displayStyle - Стиль display (по умолчанию 'block')
     */
    toggle(element, show, displayStyle = 'block') {
        if (!element) return;

        if (show) {
            element.style.display = displayStyle;
        } else {
            element.style.display = 'none';
        }
    },

    /**
     * Добавить/удалить класс
     * @param {HTMLElement} element - DOM элемент
     * @param {string} className - Имя класса
     * @param {boolean} add - Добавить или удалить
     */
    toggleClass(element, className, add) {
        if (!element) return;

        if (add) {
            element.classList.add(className);
        } else {
            element.classList.remove(className);
        }
    }
};

// Экспортируем для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UI;
}
