// photos/static/photos/js/photo-card.js
// Логика карточки товара

// ========== Photo Enhancement ==========

/**
 * Улучшить фото через FASHN API
 * @param {number} photoId - ID фото
 * @param {string} mode - Режим обработки: 'ghost_mannequin', 'remove_bg', 'quality'
 */
async function enhancePhoto(photoId, mode = 'ghost_mannequin') {
    const photoElement = document.getElementById(`photo-${photoId}`);
    const img = photoElement?.querySelector('img');

    console.log(`🚀 Starting enhancePhoto: photoId=${photoId}, mode=${mode}`);

    if (img) {
        UI.setImageLoading(img, true);
        console.log('✅ Set image loading state');
    } else {
        console.warn('⚠️ Image element not found');
    }

    const modeText = mode === 'ghost_mannequin' ? 'Генерирую модель (может занять 30-60 сек)' : 'Улучшаю фото';
    console.log(`${modeText} для фото ${photoId}...`);

    try {
        const response = await API.enhancePhoto(photoId, mode);
        console.log('📥 Response data:', response.data);

        if (response.data.success) {
            console.log(`✅ ${response.data.message}`);

            // Перезагружаем страницу чтобы показать новое фото
            if (response.data.reload) {
                console.log('🔄 Reloading page...');
                window.location.reload();
            } else if (img && response.data.photo_url) {
                img.src = response.data.photo_url + '?t=' + Date.now();
                UI.setImageLoading(img, false);
                UI.showToast(response.data.message || 'Фото обработано', 'success');
            }
        } else {
            console.error('❌ API error:', response.data.error);
            UI.showToast(`Ошибка: ${response.data.error}`, 'error', 5000);
            if (img) UI.setImageLoading(img, false);
        }
    } catch (error) {
        console.error('❌ Exception in enhancePhoto:', error);
        const errorMsg = error.response?.data?.error || error.message;
        UI.showToast(`Ошибка при обработке: ${errorMsg}`, 'error', 5000);
        if (img) UI.setImageLoading(img, false);
    }
}

// ========== Photo Rotation ==========

/**
 * Повернуть фото
 * @param {number} photoId - ID фото
 * @param {string} direction - Направление: 'left' или 'right'
 */
async function rotatePhoto(photoId, direction = 'right') {
    const photoElement = document.getElementById(`photo-${photoId}`);
    const img = photoElement?.querySelector('img');

    if (img) {
        UI.setImageLoading(img, true);
    }

    try {
        const response = await API.rotatePhoto(photoId, direction);

        if (response.data.success) {
            if (img) {
                img.src = response.data.photo_url + '?t=' + Date.now();
                UI.setImageLoading(img, false);
                UI.showToast('Фото повернуто', 'success');
            }
        } else {
            UI.showToast(`Ошибка: ${response.data.error || 'Неизвестная ошибка'}`, 'error');
            if (img) UI.setImageLoading(img, false);
        }
    } catch (error) {
        console.error('Error rotating photo:', error);
        UI.showToast(`Ошибка при повороте: ${error.message}`, 'error');
        if (img) UI.setImageLoading(img, false);
    }
}

// ========== Photo Deletion ==========

/**
 * Удалить фото
 * @param {number} photoId - ID фото
 */
async function deletePhoto(photoId) {
    const confirmed = await UI.confirm('Удалить это фото?');
    if (!confirmed) return;

    try {
        const response = await API.deletePhoto(photoId);

        if (response.data.success) {
            // Удаляем элемент из DOM
            const photoElement = document.getElementById(`photo-${photoId}`);
            if (photoElement) {
                photoElement.remove();
            }

            // Обновляем счетчик фото
            const photosGrid = document.querySelector('.photos-grid');
            const photoCount = photosGrid?.querySelectorAll('.photo-item').length || 0;
            const title = document.querySelector('.card-header h2');
            if (title) {
                title.textContent = `📸 Фото (${photoCount})`;
            }

            UI.showToast('Фото удалено', 'success');
        } else {
            UI.showToast(`Ошибка: ${response.data.error || 'Неизвестная ошибка'}`, 'error');
        }
    } catch (error) {
        console.error('Error deleting photo:', error);
        UI.showToast(`Ошибка при удалении: ${error.message}`, 'error');
    }
}

// ========== Set Main Photo ==========

/**
 * Установить главное фото
 * @param {number} photoId - ID фото
 */
async function setMainPhoto(photoId) {
    try {
        const response = await API.setMainPhoto(photoId);

        if (response.data.success) {
            window.location.reload();
        } else {
            UI.showToast(`Ошибка: ${response.data.error || 'Неизвестная ошибка'}`, 'error');
        }
    } catch (error) {
        console.error('Error setting main photo:', error);
        UI.showToast(`Ошибка при установке главного фото: ${error.message}`, 'error');
    }
}

// ========== Photo Upload ==========

/**
 * Загрузить фото с компьютера
 */
async function uploadPhotosFromComputer() {
    const fileInput = document.getElementById('file-input');
    const files = fileInput?.files;

    if (!files || files.length === 0) {
        return;
    }

    const cardId = document.querySelector('.content-area')?.dataset.cardId;
    if (!cardId) {
        UI.showToast('Ошибка: не найден ID карточки', 'error');
        return;
    }

    const button = fileInput.previousElementSibling;
    const originalText = button?.textContent || '';

    if (button) {
        UI.setLoading(button, true, '⏳ Загружаю...');
    }

    let successCount = 0;
    let errorCount = 0;

    for (let i = 0; i < files.length; i++) {
        const file = files[i];

        try {
            const formData = new FormData();
            formData.append('photo', file);

            const response = await API.uploadPhoto(cardId, file);

            if (response.data.success) {
                successCount++;
            } else {
                errorCount++;
                console.error('Error uploading photo:', response.data.error);
            }
        } catch (error) {
            errorCount++;
            console.error('Error uploading photo:', error);
        }
    }

    if (button) {
        UI.setLoading(button, false);
        button.textContent = originalText;
    }

    fileInput.value = '';

    if (successCount > 0) {
        if (errorCount > 0) {
            UI.showToast(`Загружено: ${successCount}, ошибок: ${errorCount}`, 'warning', 4000);
        } else {
            UI.showToast(`Загружено фото: ${successCount}`, 'success');
        }
        // Небольшая задержка перед перезагрузкой для показа toast
        setTimeout(() => window.location.reload(), 500);
    } else {
        UI.showToast('Ошибка при загрузке фото. Проверь формат и размер файлов.', 'error');
    }
}

/**
 * Добавить фото по URL
 * @param {string} imageUrl - URL изображения
 */
async function addPhotoFromUrl(imageUrl) {
    const cardId = document.querySelector('.content-area')?.dataset.cardId;
    if (!cardId) {
        UI.showToast('Ошибка: не найден ID карточки', 'error');
        return;
    }

    try {
        const response = await API.addPhotoFromUrl(cardId, imageUrl);

        if (response.data.success) {
            UI.showToast('Фото добавлено', 'success');
            setTimeout(() => window.location.reload(), 500);
        } else {
            UI.showToast(`Ошибка: ${response.data.error || 'Неизвестная ошибка'}`, 'error');
        }
    } catch (error) {
        console.error('Error adding photo from URL:', error);
        UI.showToast(`Ошибка при добавлении фото: ${error.message}`, 'error');
    }
}

// ========== Photo Reprocessing ==========

/**
 * Переобработать фото (распознавание штрих-кода)
 * @param {number} photoId - ID фото
 * @param {Event} event - Событие клика
 */
async function reprocessPhoto(photoId, event) {
    const confirmed = await UI.confirm('Перечитать коды с этого фото? Это может занять несколько секунд.');
    if (!confirmed) return;

    const btn = event?.target;
    const photoItem = btn?.closest('.photo-item');

    if (photoItem) {
        photoItem.classList.add('processing');
    }

    if (btn) {
        UI.setLoading(btn, true, 'Обработка...');
    }

    try {
        const response = await API.reprocessPhoto(photoId);
        const data = response.data;

        if (data.success) {
            let message = '';
            if (data.barcodes_found > 0) {
                message = `✅ Найдено новых кодов: ${data.barcodes_found}\n\nНайденные коды:\n${data.barcodes.join('\n')}`;
            } else {
                message = `ℹ️ Новых кодов не найдено.\nВсего обработано результатов: ${data.total_results || 0}`;
            }

            if (data.api_info) {
                message += `\n\n📡 Статус API:\n${data.api_info.join('\n')}`;
            }

            if (data.debug_info) {
                message += `\n\n🔍 Отладка:\n`;
                message += `Использован: ${data.debug_info.used_pipeline || 'unknown'}\n`;
                message += `Google Vision: ${data.debug_info.google_vision_called ? 'вызван' : 'не вызван'}\n`;
                message += `OpenAI: ${data.debug_info.openai_called ? 'вызван' : 'не вызван'}`;
            }

            alert(message);
            window.location.reload();
        } else {
            let errorMsg = 'Ошибка: ' + (data.error || 'Неизвестная ошибка');
            if (data.traceback) {
                console.error('Traceback:', data.traceback);
                errorMsg += '\n\nПроверь консоль браузера (F12) для деталей.';
            }
            alert(errorMsg);
        }
    } catch (error) {
        console.error('Error reprocessing photo:', error);
        alert('Ошибка при обработке: ' + error.message);
    } finally {
        if (photoItem) {
            photoItem.classList.remove('processing');
        }
        if (btn) {
            UI.setLoading(btn, false);
            btn.textContent = '🔍 Прочесть коды';
        }
    }
}

// ========== Stock Photos ==========

/**
 * Поиск стоковых фото
 */
async function searchStockPhotos() {
    const cardId = document.querySelector('.content-area')?.dataset.cardId;
    if (!cardId) {
        UI.showToast('Ошибка: не найден ID карточки', 'error');
        return;
    }

    const stockSection = document.getElementById('stock-photos-section');
    const stockGrid = document.getElementById('stock-photos-grid');

    if (stockSection) {
        stockSection.style.display = 'block';
    }

    if (stockGrid) {
        stockGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 20px; color: #6b7280;">🔍 Ищу стоковые фото...</div>';
    }

    try {
        const response = await API.searchStockPhotos(cardId);
        const data = response.data;

        if (data.success && data.images && data.images.length > 0) {
            // Сохраняем массив фото для lightbox (глобальная переменная)
            window.stockPhotosArray = data.images;

            if (stockGrid) {
                stockGrid.innerHTML = '';
                data.images.forEach((img, index) => {
                    const imgDiv = document.createElement('div');
                    imgDiv.className = 'stock-photo-item';
                    imgDiv.style.cursor = 'pointer';

                    const imgEl = document.createElement('img');
                    imgEl.src = img.thumbnail || img.url;
                    imgEl.onerror = function () {
                        this.src = img.url;
                    };

                    // Клик по фото открывает lightbox
                    imgDiv.onclick = () => {
                        if (typeof openStockPhotoLightbox === 'function') {
                            openStockPhotoLightbox(index);
                        }
                    };

                    const addDiv = document.createElement('div');
                    addDiv.className = 'stock-photo-add';

                    const addBtn = document.createElement('button');
                    addBtn.className = 'btn btn-success btn-sm';
                    addBtn.textContent = '+ Добавить';
                    addBtn.onclick = (e) => {
                        e.stopPropagation();
                        addPhotoFromUrl(img.url);
                    };

                    addDiv.appendChild(addBtn);
                    imgDiv.appendChild(imgEl);
                    imgDiv.appendChild(addDiv);
                    stockGrid.appendChild(imgDiv);
                });
            }

            UI.showToast(`Найдено стоковых фото: ${data.images.length}`, 'success');
        } else {
            if (stockGrid) {
                stockGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 20px; color: #ef4444;">❌ Стоковые фото не найдены</div>';
            }
            UI.showToast('Стоковые фото не найдены', 'info');
        }
    } catch (error) {
        console.error('Error searching stock photos:', error);
        if (stockGrid) {
            stockGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 20px; color: #ef4444;">❌ Ошибка: ${error.message}</div>`;
        }
        UI.showToast(`Ошибка поиска: ${error.message}`, 'error');
    }
}

/**
 * Закрыть секцию стоковых фото
 */
function closeStockPhotos() {
    const stockSection = document.getElementById('stock-photos-section');
    if (stockSection) {
        stockSection.style.display = 'none';
    }
}

// ========== Barcode Functions ==========

/**
 * Показать форму добавления баркода
 */
function showAddBarcodeForm() {
    const form = document.getElementById('add-barcode-form');
    const input = document.getElementById('barcode-data');

    if (form) {
        form.style.display = 'block';
    }
    if (input) {
        input.focus();
    }
}

/**
 * Скрыть форму добавления баркода
 */
function hideAddBarcodeForm() {
    const form = document.getElementById('add-barcode-form');
    const input = document.getElementById('barcode-data');

    if (form) {
        form.style.display = 'none';
    }
    if (input) {
        input.value = '';
    }
}

/**
 * Добавить баркод вручную
 */
async function addBarcodeManually() {
    const cardId = document.querySelector('.content-area')?.dataset.cardId;
    const barcodeInput = document.getElementById('barcode-data');
    const barcodeTypeSelect = document.getElementById('barcode-type');

    if (!cardId) {
        UI.showToast('Ошибка: не найден ID карточки', 'error');
        return;
    }

    const barcodeData = barcodeInput?.value.trim();
    const barcodeType = barcodeTypeSelect?.value;

    if (!barcodeData) {
        UI.showToast('Введите код', 'warning');
        if (barcodeInput) barcodeInput.focus();
        return;
    }

    try {
        const response = await API.addBarcodeManually(cardId, barcodeData);

        if (response.data.success) {
            UI.showToast('Баркод добавлен', 'success');
            setTimeout(() => window.location.reload(), 500);
        } else {
            UI.showToast(`Ошибка: ${response.data.error || 'Неизвестная ошибка'}`, 'error');
        }
    } catch (error) {
        console.error('Error adding barcode:', error);
        UI.showToast(`Ошибка при добавлении баркода: ${error.message}`, 'error');
    }
}

/**
 * Поиск по баркоду
 * @param {string} barcode - Штрих-код
 */
async function searchByBarcode(barcode) {
    const resultsDiv = document.getElementById('search-results');
    const loadingDiv = document.getElementById('search-loading');
    const contentDiv = document.getElementById('search-content');

    if (resultsDiv) resultsDiv.style.display = 'block';
    if (loadingDiv) loadingDiv.style.display = 'block';
    if (contentDiv) contentDiv.innerHTML = '';

    try {
        // Ищем информацию о товаре по баркоду
        const response = await API.searchByBarcode(barcode);
        const data = response.data;

        // Также ищем стоковые фото по баркоду
        const cardId = document.querySelector('.content-area')?.dataset.cardId;
        let stockPhotosHtml = '';

        if (cardId) {
            try {
                const stockResponse = await axios.get(
                    `/photos/api/search-stock-photos/${cardId}/?barcode=${encodeURIComponent(barcode)}`
                );
                const stockData = stockResponse.data;

                if (stockData.success && stockData.images && stockData.images.length > 0) {
                    stockPhotosHtml = '<div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e5e7eb;">';
                    stockPhotosHtml += '<h4 style="font-size: 13px; font-weight: 600; margin-bottom: 10px; color: #111827;">📷 Найденные стоковые фото:</h4>';
                    stockPhotosHtml += '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px;">';
                    stockData.images.forEach(img => {
                        const imgUrl = img.thumbnail || img.url;
                        stockPhotosHtml += `<div style="position: relative; border-radius: 4px; overflow: hidden; border: 1px solid #e5e7eb; cursor: pointer;" onclick="addPhotoFromUrl('${img.url}')">`;
                        stockPhotosHtml += `<img src="${imgUrl}" style="width: 100%; height: 100px; object-fit: cover; display: block;" onerror="this.src='${img.url}'">`;
                        stockPhotosHtml += `<div style="position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.7); padding: 4px; text-align: center; font-size: 10px; color: white;">+ Добавить</div>`;
                        stockPhotosHtml += '</div>';
                    });
                    stockPhotosHtml += '</div></div>';
                }
            } catch (stockError) {
                console.log('Stock photos search error:', stockError);
            }
        }

        if (loadingDiv) loadingDiv.style.display = 'none';

        if (data.success && data.results && contentDiv) {
            let html = '<div style="background: white; padding: 12px; border-radius: 6px;">';

            if (data.results.title) {
                html += `<h3 style="margin-bottom: 8px; font-size: 14px; color: #111827;">${data.results.title}</h3>`;
            }

            if (data.results.description) {
                html += `<p style="margin-bottom: 8px; font-size: 12px; color: #374151;">${data.results.description}</p>`;
            }

            if (data.results.brand) {
                html += `<p style="margin-bottom: 4px; font-size: 11px; color: #6b7280;"><strong>Бренд:</strong> ${data.results.brand}</p>`;
            }

            html += stockPhotosHtml;
            html += '</div>';

            contentDiv.innerHTML = html;
            UI.showToast('Информация найдена', 'success');
        } else if (contentDiv) {
            contentDiv.innerHTML = '<div style="padding: 12px; color: #6b7280; text-align: center;">Информация не найдена</div>';
            UI.showToast('Информация не найдена', 'info');
        }
    } catch (error) {
        console.error('Error searching by barcode:', error);
        if (loadingDiv) loadingDiv.style.display = 'none';
        if (contentDiv) {
            contentDiv.innerHTML = `<div style="padding: 12px; color: #ef4444; text-align: center;">Ошибка: ${error.message}</div>`;
        }
        UI.showToast(`Ошибка поиска: ${error.message}`, 'error');
    }
}

// ========== AI Summary Functions ==========

/**
 * Сгенерировать AI описание
 */
async function generateSummary() {
    const cardId = document.querySelector('.content-area')?.dataset.cardId;
    if (!cardId) {
        UI.showToast('Ошибка: не найден ID карточки', 'error');
        return;
    }

    const button = document.querySelector('[onclick*="generateSummary"]');
    if (button) {
        UI.setLoading(button, true, '⏳ Генерирую...');
    }

    try {
        const response = await API.generateSummary(cardId);
        const data = response.data;

        if (data.success) {
            UI.showToast('Описание сгенерировано', 'success');

            // Заполняем поля если есть функция
            if (typeof parseSummaryAndFillFields === 'function' && data.summary) {
                parseSummaryAndFillFields(data.summary);
            }

            // Показываем описание
            const summaryTextarea = document.getElementById('ai-summary-text');
            if (summaryTextarea && data.summary) {
                summaryTextarea.value = data.summary;
            }
        } else {
            UI.showToast(`Ошибка: ${data.error || 'Неизвестная ошибка'}`, 'error');
        }
    } catch (error) {
        console.error('Error generating summary:', error);
        UI.showToast(`Ошибка генерации: ${error.message}`, 'error');
    } finally {
        if (button) {
            UI.setLoading(button, false);
        }
    }
}

/**
 * Сохранить AI описание
 */
async function saveAISummary() {
    const cardId = document.querySelector('.content-area')?.dataset.cardId;
    const summaryTextarea = document.getElementById('ai-summary-text');

    if (!cardId) {
        UI.showToast('Ошибка: не найден ID карточки', 'error');
        return;
    }

    const summaryText = summaryTextarea?.value.trim();
    if (!summaryText) {
        UI.showToast('Введите описание', 'warning');
        return;
    }

    try {
        const response = await API.saveAISummary(cardId, {
            summary: summaryText
        });

        if (response.data.success) {
            UI.showToast('Описание сохранено', 'success');
        } else {
            UI.showToast(`Ошибка: ${response.data.error || 'Неизвестная ошибка'}`, 'error');
        }
    } catch (error) {
        console.error('Error saving summary:', error);
        UI.showToast(`Ошибка сохранения: ${error.message}`, 'error');
    }
}

// Экспортируем функции для использования в HTML (через window)
if (typeof window !== 'undefined') {
    window.enhancePhoto = enhancePhoto;
    window.rotatePhoto = rotatePhoto;
    window.deletePhoto = deletePhoto;
    window.setMainPhoto = setMainPhoto;
    window.uploadPhotosFromComputer = uploadPhotosFromComputer;
    window.addPhotoFromUrl = addPhotoFromUrl;
    window.reprocessPhoto = reprocessPhoto;
    window.searchStockPhotos = searchStockPhotos;
    window.closeStockPhotos = closeStockPhotos;
    window.showAddBarcodeForm = showAddBarcodeForm;
    window.hideAddBarcodeForm = hideAddBarcodeForm;
    window.addBarcodeManually = addBarcodeManually;
    window.searchByBarcode = searchByBarcode;
    window.generateSummary = generateSummary;
    window.saveAISummary = saveAISummary;
}
