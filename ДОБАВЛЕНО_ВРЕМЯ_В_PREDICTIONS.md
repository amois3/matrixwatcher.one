# Добавлено Время Обнаружения в Predictions

**Дата**: 18 января 2026  
**Статус**: ✅ Готово

## Изменение

Добавлено отображение времени и даты обнаружения в карточках Predictions в PWA.

## Что Добавлено

### 1. Новая Функция `formatDetectionTime()`

**Файл**: `web/static/index.html`

**Функция**:
```javascript
function formatDetectionTime(timestamp) {
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const detectionDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    
    const timeStr = date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
    });
    
    // Check if today
    if (detectionDate.getTime() === today.getTime()) {
        return `Today · ${timeStr}`;
    }
    
    // Check if yesterday
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    if (detectionDate.getTime() === yesterday.getTime()) {
        return `Yesterday · ${timeStr}`;
    }
    
    // Otherwise show date
    const dateStr = date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric' 
    });
    return `${dateStr} · ${timeStr}`;
}
```

**Форматы**:
- Сегодня: `Today · 14:23`
- Вчера: `Yesterday · 09:15`
- Раньше: `Jan 16 · 22:45`

### 2. Обновлена Карточка Prediction

**Файл**: `web/static/index.html`

**Добавлено**:
```html
<div class="prediction-time">
    🕒 ${detectionTime}
</div>
```

**Расположение**: между заголовком и описанием триггера

### 3. Добавлены Стили

**Файл**: `web/static/index.html`

```css
.prediction-time {
    font-size: 13px;
    color: var(--text-muted);
    margin: 6px 0 10px 0;
    font-family: 'JetBrains Mono', monospace;
}
```

## Результат

### До
```
┌─────────────────────────────────────┐
│ 🌍 Earthquake M5.0+          100%   │
│                                     │
│ When crypto shows unusual activity, │
│ earthquake typically follows        │
│ within ~6.3h                        │
│                                     │
│ Based on: 10,432 similar patterns   │
└─────────────────────────────────────┘
```

### После
```
┌─────────────────────────────────────┐
│ 🌍 Earthquake M5.0+          100%   │
│ 🕒 Today · 14:23                    │
│                                     │
│ When crypto shows unusual activity, │
│ earthquake typically follows        │
│ within ~6.3h                        │
│                                     │
│ Based on: 10,432 similar patterns   │
└─────────────────────────────────────┘
```

## Преимущества

✅ **Понятно когда обнаружено** - пользователь видит свежесть предсказания  
✅ **Умное форматирование** - "Today", "Yesterday" вместо дат для недавних событий  
✅ **24-часовой формат** - 14:23 вместо 2:23 PM (более точно)  
✅ **Консистентность** - такой же формат как в Level карточках  

## Технические Детали

- Timestamp берется из `p.timestamp` (Unix timestamp в секундах)
- Конвертируется в JavaScript Date объект
- Сравнивается с текущей датой для определения "Today"/"Yesterday"
- Форматируется в читаемый вид
- Отображается с иконкой 🕒 для визуальной идентификации
