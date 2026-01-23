# 🌐 НАСТРОЙКА CLOUDFLARE TUNNEL ДЛЯ matrixwatcher.space

## 📋 ЧТО У НАС ЕСТЬ:

- ✅ Домен: **matrixwatcher.space** (Porkbun)
- ✅ PWA работает на localhost:5555
- ✅ API ключ Porkbun (для переноса DNS)

## 🎯 ЧТО ПОЛУЧИМ:

- ✅ https://matrixwatcher.space - публичный доступ
- ✅ Бесплатно навсегда
- ✅ HTTPS автоматически
- ✅ DDoS защита
- ✅ Работает с твоего компа (пока нет Oracle)

---

## 🚀 ШАГ 1: ПЕРЕНЕСТИ ДОМЕН НА CLOUDFLARE

### 1.1. Создать аккаунт Cloudflare (если нет)
1. Иди на https://dash.cloudflare.com/sign-up
2. Зарегистрируйся (бесплатно)

### 1.2. Добавить домен в Cloudflare
1. В Cloudflare Dashboard нажми **"Add a Site"**
2. Введи: **matrixwatcher.space**
3. Выбери план: **Free** (бесплатный)
4. Нажми **Continue**

### 1.3. Cloudflare покажет nameservers (примерно такие):
```
ns1.cloudflare.com
ns2.cloudflare.com
```

### 1.4. Изменить nameservers в Porkbun
1. Иди на https://porkbun.com/account/domainsSpeedy
2. Найди **matrixwatcher.space**
3. Нажми **Details**
4. Найди **Nameservers** → **Edit**
5. Удали старые nameservers
6. Добавь nameservers от Cloudflare (из шага 1.3)
7. Сохрани

⏰ **Подожди 5-30 минут** пока DNS обновится

---

## 🚀 ШАГ 2: УСТАНОВИТЬ CLOUDFLARED

### 2.1. Установить cloudflared (на твоём Mac)
```bash
brew install cloudflare/cloudflare/cloudflared
```

### 2.2. Авторизоваться
```bash
cloudflared tunnel login
```

Откроется браузер → выбери **matrixwatcher.space** → разреши доступ

---

## 🚀 ШАГ 3: СОЗДАТЬ ТУННЕЛЬ

### 3.1. Создать туннель
```bash
cloudflared tunnel create matrix-watcher
```

Cloudflare создаст туннель и покажет:
```
Tunnel credentials written to: ~/.cloudflared/<UUID>.json
Created tunnel matrix-watcher with id <UUID>
```

### 3.2. Создать конфигурацию
```bash
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Вставь (замени <UUID> на твой UUID из шага 3.1):
```yaml
tunnel: <UUID>
credentials-file: /Users/amois/.cloudflared/<UUID>.json

ingress:
  - hostname: matrixwatcher.space
    service: http://localhost:5555
  - service: http_status:404
```

Сохрани (Ctrl+O, Enter, Ctrl+X)

### 3.3. Создать DNS запись
```bash
cloudflared tunnel route dns matrix-watcher matrixwatcher.space
```

---

## 🚀 ШАГ 4: ЗАПУСТИТЬ ТУННЕЛЬ

### 4.1. Запустить туннель
```bash
cloudflared tunnel run matrix-watcher
```

Или в фоне:
```bash
nohup cloudflared tunnel run matrix-watcher > cloudflared.log 2>&1 &
```

### 4.2. Проверить
Открой в браузере: **https://matrixwatcher.space**

Должен открыться твой PWA! 🎉

---

## 🔧 АВТОЗАПУСК (опционально)

Чтобы туннель запускался автоматически при включении компа:

```bash
sudo cloudflared service install
sudo launchctl start com.cloudflare.cloudflared
```

---

## 📊 МОНИТОРИНГ

### Проверить статус туннеля:
```bash
cloudflared tunnel info matrix-watcher
```

### Посмотреть логи:
```bash
tail -f cloudflared.log
```

### Список туннелей:
```bash
cloudflared tunnel list
```

---

## 🎯 КОГДА ПОЛУЧИШЬ ORACLE:

### Вариант 1: Перенести туннель на Oracle
```bash
# На Oracle инстансе:
1. Установить cloudflared
2. Скопировать ~/.cloudflared/ с твоего компа
3. Запустить туннель там
```

### Вариант 2: Использовать прямой IP
```bash
# В Cloudflare DNS:
1. Удалить CNAME запись туннеля
2. Добавить A запись с IP Oracle инстанса
```

---

## 🔒 БЕЗОПАСНОСТЬ

### Cloudflare автоматически даёт:
- ✅ HTTPS (SSL сертификат)
- ✅ DDoS защита
- ✅ Firewall
- ✅ Rate limiting

### Дополнительно можно:
- Включить "Under Attack Mode" (если будет атака)
- Настроить WAF правила
- Добавить аутентификацию (Cloudflare Access)

---

## 📝 ИТОГО:

После настройки:
- ✅ https://matrixwatcher.space - работает публично
- ✅ Работает с твоего Mac (пока нет Oracle)
- ✅ Бесплатно навсегда
- ✅ Легко перенести на Oracle потом

---

**Готов начать?** Скажи когда будешь готов, и я помогу пройти все шаги!
