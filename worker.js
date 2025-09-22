// Cloudflare Worker для Telegram бота
// Адаптация Python бота для работы в Cloudflare Workers

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

addEventListener('scheduled', event => {
  event.waitUntil(handleScheduled(event))
})

// Основная функция обработки запросов
async function handleRequest(request) {
  const url = new URL(request.url)
  
  // Webhook endpoint для Telegram
  if (url.pathname === '/webhook' && request.method === 'POST') {
    const update = await request.json()
    await handleTelegramUpdate(update)
    return new Response('OK')
  }
  
  // Health check
  if (url.pathname === '/health') {
    return new Response('Bot is running', { status: 200 })
  }
  
  return new Response('Not Found', { status: 404 })
}

// Обработка Telegram обновлений
async function handleTelegramUpdate(update) {
  try {
    if (update.message) {
      await handleMessage(update.message)
    } else if (update.callback_query) {
      await handleCallbackQuery(update.callback_query)
    }
  } catch (error) {
    console.error('Error handling update:', error)
  }
}

// Обработка сообщений
async function handleMessage(message) {
  const chatId = message.chat.id
  const userId = message.from.id
  const text = message.text
  
  // Получаем состояние пользователя
  const userState = await getUserState(userId)
  
  if (text === '/start') {
    await handleStartCommand(chatId, userId)
  } else if (text === '/new') {
    await handleNewCommand(chatId, userId)
  } else if (text === '/help') {
    await handleHelpCommand(chatId)
  } else if (text === '/last') {
    await handleLastCommand(chatId, userId)
  } else {
    // Обработка FSM состояний
    await handleFSMInput(chatId, userId, text, userState)
  }
}

// Обработка callback запросов
async function handleCallbackQuery(callbackQuery) {
  const chatId = callbackQuery.message.chat.id
  const userId = callbackQuery.from.id
  const data = callbackQuery.data
  
  // Отвечаем на callback
  await answerCallbackQuery(callbackQuery.id)
  
  // Обработка различных callback'ов
  if (data === 'new_entry') {
    await startNewEntry(chatId, userId)
  } else if (data === 'time_now') {
    await handleTimeNow(chatId, userId)
  } else if (data === 'confirm_save') {
    await handleConfirmSave(chatId, userId)
  }
  // ... другие callback'ы
}

// Команда /start
async function handleStartCommand(chatId, userId) {
  const user = await getUser(userId)
  
  if (!user) {
    await sendMessage(chatId, 
      "👋 Добро пожаловать!\\n\\n" +
      "Для начала работы необходимо пройти регистрацию.\\n" +
      "📝 Введите ваше ФИО (Фамилия Имя Отчество):"
    )
    await setUserState(userId, 'waiting_registration')
  } else {
    await sendMessage(chatId, 
      `👋 Добро пожаловать, <b>${user.full_name}</b>!`,
      { parse_mode: 'HTML' }
    )
    await sendMainMenu(chatId)
  }
}

// Отправка главного меню
async function sendMainMenu(chatId) {
  const keyboard = {
    inline_keyboard: [
      [{ text: "🆕 Новая запись", callback_data: "new_entry" }],
      [
        { text: "📋 Последние записи", callback_data: "last_entries" },
        { text: "✏️ Редактировать", callback_data: "edit_last" }
      ],
      [{ text: "ℹ️ Помощь", callback_data: "help" }]
    ]
  }
  
  await sendMessage(chatId, 
    "🚗 <b>Журнал поездок инженера</b>\\n\\nВыберите действие:",
    { parse_mode: 'HTML', reply_markup: keyboard }
  )
}

// Функции для работы с Telegram API
async function sendMessage(chatId, text, options = {}) {
  const token = TELEGRAM_BOT_TOKEN
  const url = `https://api.telegram.org/bot${token}/sendMessage`
  
  const payload = {
    chat_id: chatId,
    text: text,
    ...options
  }
  
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  
  return response.json()
}

async function answerCallbackQuery(callbackQueryId, text = '') {
  const token = TELEGRAM_BOT_TOKEN
  const url = `https://api.telegram.org/bot${token}/answerCallbackQuery`
  
  await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      callback_query_id: callbackQueryId,
      text: text
    })
  })
}

// Функции для работы с пользователями (KV Storage)
async function getUser(userId) {
  try {
    const userData = await USERS_KV.get(`user_${userId}`)
    return userData ? JSON.parse(userData) : null
  } catch (error) {
    console.error('Error getting user:', error)
    return null
  }
}

async function saveUser(userId, userData) {
  try {
    await USERS_KV.put(`user_${userId}`, JSON.stringify(userData))
  } catch (error) {
    console.error('Error saving user:', error)
  }
}

async function getUserState(userId) {
  try {
    const state = await USERS_KV.get(`state_${userId}`)
    return state ? JSON.parse(state) : null
  } catch (error) {
    return null
  }
}

async function setUserState(userId, state, data = {}) {
  try {
    await USERS_KV.put(`state_${userId}`, JSON.stringify({ state, data }))
  } catch (error) {
    console.error('Error setting user state:', error)
  }
}

// Функции для работы с Google Sheets
async function appendToSheet(rowData) {
  try {
    // Используем Google Sheets API через fetch
    const response = await fetch(
      `https://sheets.googleapis.com/v4/spreadsheets/${GOOGLE_SHEET_ID}/values/${GOOGLE_SHEET_NAME}!A1:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await getGoogleAccessToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          values: [rowData]
        })
      }
    )
    
    return response.ok
  } catch (error) {
    console.error('Error appending to sheet:', error)
    return false
  }
}

async function getGoogleAccessToken() {
  // Упрощенная версия - для полной реализации нужно JWT токен
  // В Cloudflare Workers это сложнее, чем в Python
  // Рекомендуется использовать сервис-прокси или Google Apps Script
  throw new Error('Google Sheets integration requires additional setup in Cloudflare Workers')
}

// Scheduled handler (cron jobs)
async function handleScheduled(event) {
  console.log('Scheduled event triggered:', event.cron)
  // Можно добавить периодические задачи
}

// Экспорт для ES modules
export default {
  async fetch(request, env, ctx) {
    // Устанавливаем глобальные переменные
    global.TELEGRAM_BOT_TOKEN = env.TELEGRAM_BOT_TOKEN
    global.GOOGLE_SHEET_ID = env.GOOGLE_SHEET_ID
    global.ADMIN_IDS = env.ADMIN_IDS
    global.USERS_KV = env.USERS_KV
    
    return handleRequest(request)
  },
  
  async scheduled(event, env, ctx) {
    global.TELEGRAM_BOT_TOKEN = env.TELEGRAM_BOT_TOKEN
    global.GOOGLE_SHEET_ID = env.GOOGLE_SHEET_ID
    global.USERS_KV = env.USERS_KV
    
    return handleScheduled(event)
  }
}
