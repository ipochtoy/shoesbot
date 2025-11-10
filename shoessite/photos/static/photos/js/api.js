// photos/static/photos/js/api.js
// Централизованные API вызовы через Axios

const API = {
    // ========== Photo Operations ==========

    /**
     * Загрузить фото с компьютера
     * @param {number} cardId - ID карточки товара
     * @param {File|FileList} files - Файл(ы) для загрузки
     */
    async uploadPhoto(cardId, files) {
        const formData = new FormData();

        // Поддержка как одного файла, так и множественных
        if (files instanceof FileList) {
            for (let i = 0; i < files.length; i++) {
                formData.append('images', files[i]);
            }
        } else {
            formData.append('images', files);
        }

        return axios.post(`/photos/api/upload-photo-from-computer/${cardId}/`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
    },

    /**
     * Добавить фото по URL
     * @param {number} cardId - ID карточки товара
     * @param {string} imageUrl - URL изображения
     */
    async addPhotoFromUrl(cardId, imageUrl) {
        return axios.post(`/photos/api/add-photo-from-url/${cardId}/`, {
            image_url: imageUrl
        });
    },

    /**
     * Удалить фото
     * @param {number} photoId - ID фото
     */
    async deletePhoto(photoId) {
        return axios.post(`/photos/api/delete-photo/${photoId}/`);
    },

    /**
     * Повернуть фото
     * @param {number} photoId - ID фото
     * @param {string} direction - Направление: 'left' или 'right'
     */
    async rotatePhoto(photoId, direction = 'right') {
        return axios.post(`/photos/api/rotate-photo/${photoId}/`, {
            direction: direction
        });
    },

    /**
     * Установить главное фото
     * @param {number} photoId - ID фото
     */
    async setMainPhoto(photoId) {
        return axios.post(`/photos/api/set-main-photo/${photoId}/`);
    },

    /**
     * Переместить фото (изменить порядок)
     * @param {number} photoId - ID фото
     * @param {object} data - Данные для перемещения
     */
    async movePhoto(photoId, data) {
        return axios.post(`/photos/api/move-photo/${photoId}/`, data);
    },

    /**
     * Переобработать фото (распознавание штрих-кода)
     * @param {number} photoId - ID фото
     */
    async reprocessPhoto(photoId) {
        return axios.post(`/photos/api/reprocess-photo/${photoId}/`);
    },

    // ========== AI Operations ==========

    /**
     * Сгенерировать описание товара через AI
     * @param {number} cardId - ID карточки товара
     */
    async generateSummary(cardId) {
        return axios.post(`/photos/api/generate-summary/${cardId}/`);
    },

    /**
     * Сгенерировать из инструкции
     * @param {number} cardId - ID карточки товара
     * @param {object} data - Данные инструкции
     */
    async generateFromInstruction(cardId, data) {
        return axios.post(`/photos/api/generate-from-instruction/${cardId}/`, data);
    },

    /**
     * Сохранить AI описание
     * @param {number} cardId - ID карточки товара
     * @param {object} data - Данные для сохранения
     */
    async saveAISummary(cardId, data) {
        return axios.post(`/photos/api/save-ai-summary/${cardId}/`, data);
    },

    /**
     * Обработать фото через FASHN (удаление фона, манекен и т.д.)
     * @param {number} photoId - ID фото
     * @param {string} mode - Режим обработки: 'ghost_mannequin', 'remove_bg', 'quality'
     */
    async enhancePhoto(photoId, mode = 'ghost_mannequin') {
        return axios.post(`/photos/api/enhance-photo/${photoId}/`, {
            mode: mode
        });
    },

    // ========== Search Operations ==========

    /**
     * Поиск стоковых фото
     * @param {number} cardId - ID карточки товара
     */
    async searchStockPhotos(cardId) {
        return axios.get(`/photos/api/search-stock-photos/${cardId}/`);
    },

    /**
     * Поиск по штрих-коду
     * @param {string} barcode - Штрих-код
     */
    async searchByBarcode(barcode) {
        return axios.post(`/photos/api/search-barcode/`, {
            barcode: barcode
        });
    },

    // ========== Barcode Operations ==========

    /**
     * Добавить штрих-код вручную
     * @param {number} cardId - ID карточки товара
     * @param {string} barcode - Штрих-код
     */
    async addBarcodeManually(cardId, barcode) {
        return axios.post(`/photos/api/add-barcode/${cardId}/`, {
            barcode: barcode
        });
    },

    // ========== Group Operations (для сортировки) ==========

    /**
     * Обновить группу фото
     * @param {number} photoId - ID фото
     * @param {object} data - Данные группы
     */
    async updatePhotoGroup(photoId, data) {
        return axios.post(`/photos/api/update-photo-group/${photoId}/`, data);
    },

    /**
     * Отправить группу в бот
     * @param {number} groupId - ID группы
     */
    async sendGroupToBot(groupId) {
        return axios.post(`/photos/api/send-group-to-bot/${groupId}/`);
    },

    /**
     * Отправить группу в Почтой
     * @param {number} groupId - ID группы
     */
    async sendGroupToPochtoy(groupId) {
        return axios.post(`/photos/api/send-group-to-pochtoy/${groupId}/`);
    },

    // ========== Buffer Operations ==========

    /**
     * Загрузить в буфер
     * @param {FormData} formData - Данные формы
     */
    async bufferUpload(formData) {
        return axios.post('/photos/api/buffer-upload/', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
    },

    /**
     * Обнаружить GG в буфере
     */
    async detectGGInBuffer() {
        return axios.post('/photos/api/detect-gg-in-buffer/');
    },

    /**
     * Очистить буфер
     */
    async clearBuffer() {
        return axios.post('/photos/api/clear-buffer/');
    },

    /**
     * Удалить фото из буфера
     * @param {number} photoId - ID фото
     */
    async deleteBufferPhoto(photoId) {
        return axios.post(`/photos/api/delete-buffer-photo/${photoId}/`);
    },

    // ========== Card Operations ==========

    /**
     * Получить последнюю карточку
     */
    async getLastCard() {
        return axios.get('/photos/api/get-last-card/');
    },

    /**
     * Удалить карточку по correlation ID
     * @param {string} correlationId - Correlation ID
     */
    async deleteCardByCorrelation(correlationId) {
        return axios.post(`/photos/api/delete-card-by-correlation/${correlationId}/`);
    },

    // ========== Batch Operations ==========

    /**
     * Загрузить пакет фото
     * @param {FormData} formData - Данные формы с файлами
     */
    async uploadBatch(formData) {
        return axios.post('/photos/api/upload-batch/', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
    },

    // ========== Utility Functions ==========

    /**
     * Получить CSRF токен из cookie
     */
    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
};

// Экспортируем для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}
