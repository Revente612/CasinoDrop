import random
import sqlite3
import time
import re
from telebot import TeleBot, types
from datetime import datetime

# Инициализация бота
bot = TeleBot('5001368696:AAEtqufmeXROZAjA2IBBHJZDRe_iiPFPTmE/test')
ADMINS = [5001448188, 2201285640]  # ТВОИ АДМИНЫ

# Конфигурация безопасности
MAX_BALANCE = 1000000
MAX_BET = 1000
MIN_BET = 1

# Глобальное подключение к БД
conn = sqlite3.connect('casino.db', check_same_thread=False, isolation_level=None)
cursor = conn.cursor()

# Создание таблиц
def init_db():
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0, 
                    wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, total_bet INTEGER DEFAULT 0,
                    reg_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS deposits
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, 
                    status TEXT, date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS withdrawals
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, 
                    status TEXT, date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS games
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, game_type TEXT, 
                    result TEXT, bet INTEGER, win_amount INTEGER, date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin_logs
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, action TEXT, 
                    target_user INTEGER, details TEXT, date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS security_logs
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, 
                    details TEXT, ip TEXT, date TEXT)''')
    conn.commit()

# Инициализация БД при запуске
init_db()

# Функции безопасности
def is_admin(user_id):
    """Проверка прав администратора"""
    return user_id in ADMINS

def validate_user_id(user_id):
    """Валидация ID пользователя"""
    return isinstance(user_id, int) and user_id > 0

def validate_amount(amount):
    """Валидация суммы"""
    try:
        amount = int(amount)
        return amount >= 0
    except:
        return False

def safe_balance_update(user_id, amount):
    """Безопасное обновление баланса с проверками"""
    if not validate_user_id(user_id) or not validate_amount(abs(amount)):
        return False
    
    try:
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        if not result:
            return False
            
        current_balance = result[0]
        new_balance = current_balance + amount
        
        # Проверка лимитов
        if new_balance < 0 or new_balance > MAX_BALANCE:
            return False
            
        cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Balance update error: {e}")
        return False

def log_security_event(user_id, action, details=""):
    """Логирование событий безопасности"""
    try:
        cursor.execute("INSERT INTO security_logs (user_id, action, details, date) VALUES (?, ?, ?, ?)",
                      (user_id, action, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        print(f"Security logging error: {e}")

def log_admin_action(admin_id, action, target_user=None, details=""):
    """Логирование действий админа"""
    if not is_admin(admin_id):
        return
        
    try:
        cursor.execute("INSERT INTO admin_logs (admin_id, action, target_user, details, date) VALUES (?, ?, ?, ?, ?)",
                      (admin_id, action, target_user, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        print(f"Admin logging error: {e}")

# Красивое основное меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.row(
        types.KeyboardButton('🎮 ИГРАТЬ'),
        types.KeyboardButton('💰 БАЛАНС')
    )
    markup.row(
        types.KeyboardButton('📥 ПОПОЛНИТЬ'),
        types.KeyboardButton('📤 ВЫВЕСТИ')
    )
    markup.row(
        types.KeyboardButton('📊 ПРОФИЛЬ'),
        types.KeyboardButton('🎰 О КАЗИНО')
    )
    return markup

# Админ меню
def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row(
        types.KeyboardButton('👥 ПОЛЬЗОВАТЕЛИ'),
        types.KeyboardButton('📥 ЗАЯВКИ ПОПОЛНЕНИЯ')
    )
    markup.row(
        types.KeyboardButton('📤 ЗАЯВКИ ВЫВОДА'),
        types.KeyboardButton('📊 СТАТИСТИКА')
    )
    markup.row(
        types.KeyboardButton('📋 ЛОГИ'),
        types.KeyboardButton('⚡ АННУЛИРОВАТЬ БАЛАНС')
    )
    markup.row(
        types.KeyboardButton('🎮 ИГРАТЬ'),
        types.KeyboardButton('📊 ПРОФИЛЬ')
    )
    return markup

# Команда старт
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Неизвестный"
    
    try:
        cursor.execute("INSERT OR IGNORE INTO users (id, username, balance, reg_date) VALUES (?, ?, ?, ?)", 
                      (user_id, username, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    
    welcome_text = (
        "🎰 <b>ДОБРО ПОЖАЛОВАТЬ В CASINODROP!</b>\n\n"
        "👋 <b>Приветствуем тебя, @{}</b>!\n\n"
        "💎 <b>Чтобы начать играть, просто пополни баланс</b>\n"
        "🎯 <b>Честные ставки:</b> 60% проигрыша | 40% выигрыша\n\n"
        "📢 <b>ОБЯЗАТЕЛЬНАЯ ПОДПИСКА:</b>\n"
        "➡️ @CasinoDrop\n\n"
        "💵 <b>Минимальная ставка:</b> 1 монета\n"
        "💰 <b>Выигрыш:</b> 2x от ставки\n"
        "⚡ <b>Мгновенные выплаты</b>"
    ).format(username)
    
    bot.send_message(message.chat.id, welcome_text, 
                    parse_mode='HTML', reply_markup=main_menu())

# Команда админки
@bot.message_handler(commands=['admin'])
def admin_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "❌ <b>Доступ запрещен!</b>", parse_mode='HTML')
        log_security_event(user_id, "unauthorized_admin_access")
        return
    
    admin_text = (
        "👑 <b>АДМИН ПАНЕЛЬ CASINODROP</b>\n\n"
        "⚡ <b>Добро пожаловать, администратор!</b>\n\n"
        "🆔 <b>Ваш ID:</b> <code>{}</code>\n"
        "📅 <b>Время:</b> {}\n\n"
        "🎯 <b>Доступные функции:</b>\n"
        "• 👥 Просмотр пользователей\n"
        "• 📥 Одобрение пополнений\n"
        "• 📤 Выплата выводов\n"
        "• 📊 Статистика системы\n"
        "• 📋 Просмотр логов\n"
        "• ⚡ Аннулирование баланса"
    ).format(user_id, datetime.now().strftime('%d.%m.%Y %H:%M'))
    
    bot.send_message(message.chat.id, admin_text, 
                    parse_mode='HTML', reply_markup=admin_menu())

# Пополнение баланса
@bot.message_handler(func=lambda message: message.text == '📥 ПОПОЛНИТЬ')
def deposit(message):
    user_id = message.from_user.id
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Я ОТПРАВИЛ(А)", callback_data="deposit_sent"))
    
    deposit_text = (
        "💳 <b>ПОПОЛНЕНИЕ БАЛАНСА</b>\n\n"
        "💰 <b>Курс:</b> 1 торт = 1 монета\n"
        "📨 <b>Кошелек:</b> @Gifts_456\n\n"
        "📝 <b>Инструкция:</b>\n"
        "1. Отправьте торты на @Gifts_456\n"
        "2. Нажмите кнопку '✅ Я ОТПРАВИЛ(А)'\n"
        "3. Ожидайте проверки админа (до 3 минут)\n\n"
        "⚠️ <b>ВНИМАНИЕ:</b> Указывайте в комментарии ваш ID: <code>{}</code>\n\n"
        "⚡ <b>Пополнение обрабатывается мгновенно!</b>"
    ).format(user_id)
    
    bot.send_message(message.chat.id, deposit_text, 
                    parse_mode='HTML', reply_markup=markup)

# Обработка кнопки "Я отправил"
@bot.callback_query_handler(func=lambda call: call.data == "deposit_sent")
def deposit_sent(call):
    user_id = call.from_user.id
    amount = 1  # 1 торт = 1 монета
    
    try:
        cursor.execute("INSERT INTO deposits (user_id, amount, status, date) VALUES (?, ?, 'pending', ?)", 
                      (user_id, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    
    success_text = (
        "📨 <b>ЗАЯВКА ОТПРАВЛЕНА!</b>\n\n"
        "✅ <b>Ваша заявка на пополнение принята!</b>\n"
        "💰 <b>Сумма:</b> {} монета\n"
        "⏰ <b>Ожидайте проверки:</b> до 3 минут\n"
        "🆔 <b>Ваш ID:</b> <code>{}</code>\n\n"
        "⚡ <b>Статус заявки можно отслеживать</b>"
    ).format(amount, user_id)
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                         text=success_text, parse_mode='HTML')
    
    # Уведомление админам
    for admin_id in ADMINS:
        try:
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✅ ПРИНЯТЬ", callback_data=f"accept_deposit_{user_id}"),
                types.InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_deposit_{user_id}")
            )
            
            admin_notification = (
                "📥 <b>НОВАЯ ЗАЯВКА НА ПОПОЛНЕНИЕ</b>\n\n"
                "👤 <b>Пользователь:</b> @{}\n"
                "🆔 <b>ID:</b> <code>{}</code>\n"
                "💰 <b>Сумма:</b> {} монет\n"
                "📅 <b>Время:</b> {}\n\n"
                "⚡ <b>Ожидает проверки</b>"
            ).format(call.from_user.username or 'Нет username', user_id, amount, 
                    datetime.now().strftime('%H:%M %d.%m.%Y'))
            
            bot.send_message(admin_id, admin_notification, 
                           parse_mode='HTML', reply_markup=markup)
        except Exception as e:
            print(f"Error sending to admin {admin_id}: {e}")

# Обработка принятия пополнения админом
@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_deposit_"))
def accept_deposit(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Доступ запрещен!", show_alert=True)
        log_security_event(call.from_user.id, "unauthorized_deposit_accept", call.data)
        return
    
    try:
        user_id = int(call.data.split("_")[2])
        if not validate_user_id(user_id):
            raise ValueError("Invalid user ID")
    except:
        bot.answer_callback_query(call.id, "❌ Неверный запрос!", show_alert=True)
        return
    
    try:
        cursor.execute("SELECT amount FROM deposits WHERE user_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1", (user_id,))
        deposit_data = cursor.fetchone()
        
        if deposit_data:
            amount = deposit_data[0]
            
            # Безопасное обновление баланса
            if safe_balance_update(user_id, amount):
                cursor.execute("UPDATE deposits SET status = 'accepted' WHERE user_id = ? AND status = 'pending'", (user_id,))
                conn.commit()
                
                # Логируем действие
                log_admin_action(call.from_user.id, "accept_deposit", user_id, f"Amount: {amount}")
                
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                     text=f"✅ <b>ПОПОЛНЕНИЕ ПРИНЯТО</b>\n\n"
                                          f"👤 <b>Пользователь:</b> <code>{user_id}</code>\n"
                                          f"💰 <b>Сумма:</b> {amount} монет\n"
                                          f"⏰ <b>Время:</b> {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
                                          f"✅ <b>Баланс пользователя пополнен</b>",
                                     parse_mode='HTML')
                
                # Уведомляем пользователя
                try:
                    bot.send_message(user_id,
                                   f"💰 <b>БАЛАНС ПОПОЛНЕН!</b>\n\n"
                                   f"✅ <b>Ваша заявка на пополнение принята</b>\n"
                                   f"💸 <b>Сумма:</b> <b>{amount} монет</b>\n"
                                   f"💎 <b>Текущий баланс обновлен</b>\n\n"
                                   f"🎮 <b>Приятной игры!</b>",
                                   parse_mode='HTML')
                except:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка обновления баланса!", show_alert=True)
    except Exception as e:
        print(f"Database error: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка базы данных!", show_alert=True)

# Обработка отклонения пополнения админом
@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_deposit_"))
def reject_deposit(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Доступ запрещен!", show_alert=True)
        log_security_event(call.from_user.id, "unauthorized_deposit_reject", call.data)
        return
    
    try:
        user_id = int(call.data.split("_")[2])
        if not validate_user_id(user_id):
            raise ValueError("Invalid user ID")
    except:
        bot.answer_callback_query(call.id, "❌ Неверный запрос!", show_alert=True)
        return
    
    try:
        cursor.execute("UPDATE deposits SET status = 'rejected' WHERE user_id = ? AND status = 'pending'", (user_id,))
        conn.commit()
        
        # Логируем действие
        log_admin_action(call.from_user.id, "reject_deposit", user_id)
        
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                             text=f"❌ <b>ПОПОЛНЕНИЕ ОТКЛОНЕНО</b>\n\n"
                                  f"👤 <b>Пользователь:</b> <code>{user_id}</code>\n"
                                  f"⏰ <b>Время:</b> {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
                                  f"❌ <b>Заявка отклонена</b>",
                             parse_mode='HTML')
        
        # Уведомляем пользователя
        try:
            bot.send_message(user_id,
                           f"❌ <b>ЗАЯВКА ОТКЛОНЕНА</b>\n\n"
                           f"😢 <b>Ваша заявка на пополнение отклонена</b>\n"
                           f"📞 <b>Свяжитесь с поддержкой для уточнения причин</b>\n\n"
                           f"💎 @Gifts_456",
                           parse_mode='HTML')
        except:
            pass
    except Exception as e:
        print(f"Database error: {e}")

# Игры
@bot.message_handler(func=lambda message: message.text == '🎮 ИГРАТЬ')
def play(message):
    user_id = message.from_user.id
    
    try:
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result else 0
    except Exception as e:
        print(f"Database error: {e}")
        balance = 0
    
    if balance < MIN_BET:
        no_money_text = (
            "😢 <b>НЕДОСТАТОЧНО СРЕДСТВ</b>\n\n"
            "💰 <b>Ваш баланс:</b> {} монет\n"
            "💸 <b>Минимальная ставка:</b> {} монета\n\n"
            "📥 <b>Пополните баланс чтобы начать играть!</b>\n"
            "⚡ <b>И помните - удача любит смелых!</b>"
        ).format(balance, MIN_BET)
        
        bot.send_message(message.chat.id, no_money_text, parse_mode='HTML')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("🎲 КОСТИ", callback_data="game_dice"),
        types.InlineKeyboardButton("⚽ ФУТБОЛ", callback_data="game_football")
    )
    markup.row(
        types.InlineKeyboardButton("🏀 БАСКЕТБОЛ", callback_data="game_basketball"),
        types.InlineKeyboardButton("🎰 СПИН", callback_data="game_slot")
    )
    
    play_text = (
        "🎮 <b>ВЫБЕРИТЕ ИГРУ</b>\n\n"
        "💰 <b>Ваш баланс:</b> <b>{} монет</b>\n"
        "🎯 <b>Шансы:</b> 40% выигрыш | 60% проигрыш\n"
        "💰 <b>Выигрыш:</b> 2x от ставки\n\n"
        "💵 <b>Доступные ставки:</b>\n"
        "1 🎯 3 🎯 5 🎯 10 🎯 20 🎯 50 🎯\n\n"
        "⚡ <b>Удачи в игре!</b>"
    ).format(balance)
    
    bot.send_message(message.chat.id, play_text, 
                    parse_mode='HTML', reply_markup=markup)

# Выбор ставки для игры
@bot.callback_query_handler(func=lambda call: call.data.startswith("game_"))
def select_bet(call):
    user_id = call.from_user.id
    
    try:
        game_type = call.data.split("_")[1]
        if game_type not in ['dice', 'football', 'basketball', 'slot']:
            raise ValueError("Invalid game type")
    except:
        bot.answer_callback_query(call.id, "❌ Неверный тип игры!", show_alert=True)
        return
    
    try:
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result else 0
    except Exception as e:
        print(f"Database error: {e}")
        balance = 0
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    bets = [1, 3, 5, 10, 20, 50]
    buttons = []
    
    for bet in bets:
        if balance >= bet and MIN_BET <= bet <= MAX_BET:
            buttons.append(types.InlineKeyboardButton(f"{bet} 🎯", callback_data=f"bet_{game_type}_{bet}"))
        else:
            buttons.append(types.InlineKeyboardButton(f"{bet} ❌", callback_data="no_money"))
    
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("🔙 НАЗАД К ИГРАМ", callback_data="back_to_games"))
    
    game_names = {
        'dice': '🎲 КОСТИ',
        'football': '⚽ ФУТБОЛ', 
        'basketball': '🏀 БАСКЕТБОЛ',
        'slot': '🎰 СПИН'
    }
    
    bet_text = (
        "🎯 <b>ВЫБЕРИТЕ СТАВКУ</b>\n\n"
        "🎮 <b>Игра:</b> {}\n"
        "💰 <b>Ваш баланс:</b> <b>{} монет</b>\n\n"
        "💸 <b>Доступные ставки:</b>\n"
        "⚡ <b>Выигрыш 2x от ставки!</b>"
    ).format(game_names[game_type], balance)
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                         text=bet_text, parse_mode='HTML', reply_markup=markup)

# Обработка ставки и игры
@bot.callback_query_handler(func=lambda call: call.data.startswith("bet_"))
def game_handler(call):
    user_id = call.from_user.id
    
    try:
        data = call.data.split("_")
        if len(data) != 3:
            raise ValueError("Invalid callback data")
            
        game_type = data[1]
        bet = int(data[2])
        
        if game_type not in ['dice', 'football', 'basketball', 'slot']:
            raise ValueError("Invalid game type")
            
        if not (MIN_BET <= bet <= MAX_BET):
            raise ValueError("Invalid bet amount")
    except:
        bot.answer_callback_query(call.id, "❌ Неверный запрос!", show_alert=True)
        log_security_event(user_id, "invalid_bet_request", call.data)
        return
    
    try:
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result else 0
    except Exception as e:
        print(f"Database error: {e}")
        balance = 0
    
    if balance < bet:
        bot.answer_callback_query(call.id, "❌ НЕДОСТАТОЧНО СРЕДСТВ!", show_alert=True)
        return
    
    # Списываем ставку с проверкой безопасности
    if not safe_balance_update(user_id, -bet):
        bot.answer_callback_query(call.id, "❌ Ошибка списания средств!", show_alert=True)
        return
    
    try:
        cursor.execute("UPDATE users SET total_bet = total_bet + ? WHERE id = ?", (bet, user_id))
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    
    # Показываем сообщение "Ставка принята..."
    loading_text = (
        "🎯 <b>СТАВКА ПРИНЯТА...</b>\n\n"
        "💸 <b>Сумма:</b> {} монет\n"
        "🎮 <b>Игра:</b> {}\n"
        "⏳ <b>Определяем результат...</b>\n\n"
        "⚡ <b>Удачи!</b>"
    ).format(bet, game_type)
    
    loading_msg = bot.send_message(call.message.chat.id, loading_text, parse_mode='HTML')
    
    # Имитируем задержку для азарта
    time.sleep(2)
    
    # Определяем результат (40% шанс выигрыша)
    is_win = random.random() < 0.4
    
    if is_win:
        win_amount = bet * 2  # Выигрыш 2x
        
        # Безопасное начисление выигрыша
        if safe_balance_update(user_id, win_amount):
            try:
                cursor.execute("UPDATE users SET wins = wins + 1 WHERE id = ?", (user_id,))
                result_text = "🎉 ПОБЕДА!"
                result_emoji = "✅"
            except Exception as e:
                print(f"Database error: {e}")
        else:
            win_amount = 0
            result_text = "❌ ОШИБКА ВЫПЛАТЫ!"
            result_emoji = "⚠️"
        
        # Генерируем результат для разных игр
        if game_type == 'dice':
            user_dice = random.randint(4, 6)  # Выигрышные значения
            bot_dice = random.randint(1, 3)   # Проигрышные значения
            game_result = f"🎲 <b>Ваш кубик:</b> {user_dice} | <b>Бот:</b> {bot_dice}"
        elif game_type == 'football':
            game_result = "⚽ <b>МЯЧ В ВОРОТАХ! ГОООЛ!</b>"
        elif game_type == 'basketball':
            game_result = "🏀 <b>МЯЧ В КОРЗИНЕ! Отличный бросок!</b>"
        elif game_type == 'slot':
            game_result = "🎰 <b>ДЖЕКПОТ! Три одинаковых символа!</b>"
            
    else:
        win_amount = 0
        try:
            cursor.execute("UPDATE users SET losses = losses + 1 WHERE id = ?", (user_id,))
            result_text = "💀 ПРОИГРЫШ!"
            result_emoji = "❌"
        except Exception as e:
            print(f"Database error: {e}")
        
        # Генерируем результат для разных игр
        if game_type == 'dice':
            user_dice = random.randint(1, 3)  # Проигрышные значения
            bot_dice = random.randint(4, 6)   # Выигрышные значения
            game_result = f"🎲 <b>Ваш кубик:</b> {user_dice} | <b>Бот:</b> {bot_dice}"
        elif game_type == 'football':
            game_result = "❌ <b>МИМО ВОРОТ! Промах...</b>"
        elif game_type == 'basketball':
            game_result = "❌ <b>МИМО КОРЗИНЫ! Неудача...</b>"
        elif game_type == 'slot':
            game_result = "🎰 <b>Ничего не совпало... Попробуйте снова!</b>"
    
    # Сохраняем игру в историю
    try:
        cursor.execute("INSERT INTO games (user_id, game_type, result, bet, win_amount, date) VALUES (?, ?, ?, ?, ?, ?)",
                      (user_id, game_type, 'win' if is_win else 'loss', bet, win_amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    
    # Получаем обновленный баланс
    try:
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        new_balance = result[0] if result else 0
    except Exception as e:
        print(f"Database error: {e}")
        new_balance = 0
    
    # Удаляем сообщение "Ставка принята..." и показываем результат
    bot.delete_message(call.message.chat.id, loading_msg.message_id)
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🎮 ИГРАТЬ СНОВА", callback_data=f"game_{game_type}"),
        types.InlineKeyboardButton("📊 ПРОФИЛЬ", callback_data="profile")
    )
    
    result_text_full = (
        "🎮 <b>РЕЗУЛЬТАТ ИГРЫ</b>\n\n"
        "{}\n\n"
        "💵 <b>Ставка:</b> <b>{} монет</b>\n"
        "🎯 <b>Результат:</b> <b>{}</b>\n"
        "💰 <b>Выигрыш:</b> <b>{} монет</b>\n"
        "💎 <b>Баланс:</b> <b>{} монет</b>\n\n"
        "{} <i>Статистика обновлена</i>"
    ).format(game_result, bet, result_text, win_amount, new_balance, result_emoji)
    
    bot.send_message(call.message.chat.id, result_text_full, 
                    parse_mode='HTML', reply_markup=markup)

# Баланс
@bot.message_handler(func=lambda message: message.text == '💰 БАЛАНС')
def show_balance(message):
    user_id = message.from_user.id
    
    try:
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result else 0
    except Exception as e:
        print(f"Database error: {e}")
        balance = 0
    
    balance_text = (
        "💰 <b>ВАШ БАЛАНС</b>\n\n"
        "💎 <b>Доступно:</b> <b>{} монет</b>\n\n"
        "📥 <b>Пополнить баланс</b> - кнопка ниже\n"
        "🎮 <b>Играть</b> - кнопка ниже\n\n"
        "⚡ <b>Удачи в игре!</b>"
    ).format(balance)
    
    bot.send_message(message.chat.id, balance_text, parse_mode='HTML')

# Профиль - ИСПРАВЛЕННАЯ ФУНКЦИЯ
@bot.message_handler(func=lambda message: message.text == '📊 ПРОФИЛЬ')
def show_profile(message):
    user_id = message.from_user.id
    
    try:
        cursor.execute("SELECT username, balance, wins, losses, total_bet, reg_date FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
    except Exception as e:
        print(f"Database error: {e}")
        user_data = None
    
    if user_data:
        username, balance, wins, losses, total_bet, reg_date = user_data
        total_games = wins + losses
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        profile_text = (
            "📊 <b>ВАШ ПРОФИЛЬ</b>\n\n"
            "👤 <b>Игрок:</b> <b>@{}</b>\n"
            "🆔 <b>ID:</b> <code>{}</code>\n"
            "💎 <b>Баланс:</b> <b>{} монет</b>\n\n"
            "🎮 <b>СТАТИСТИКА ИГР:</b>\n"
            "✅ <b>Побед:</b> <b>{}</b>\n"
            "❌ <b>Поражений:</b> <b>{}</b>\n"
            "📈 <b>Винрейт:</b> <b>{:.1f}%</b>\n"
            "💵 <b>Всего ставок:</b> <b>{} монет</b>\n\n"
            "📅 <b>Регистрация:</b> {}\n\n"
            "⚡ <b>Продолжайте в том же духе!</b>"
        ).format(username, user_id, balance, wins, losses, win_rate, total_bet, reg_date)
        
        bot.send_message(message.chat.id, profile_text, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, "❌ <b>Профиль не найден!</b>", parse_mode='HTML')

# Вывод средств
@bot.message_handler(func=lambda message: message.text == '📤 ВЫВЕСТИ')
def withdraw(message):
    user_id = message.from_user.id
    
    try:
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result else 0
    except Exception as e:
        print(f"Database error: {e}")
        balance = 0
    
    if balance < 1:
        no_money_text = (
            "😢 <b>НЕДОСТАТОЧНО СРЕДСТВ</b>\n\n"
            "💰 <b>Ваш баланс:</b> {} монет\n"
            "💸 <b>Минимальный вывод:</b> 1 монета\n\n"
            "🎮 <b>Играйте чтобы заработать больше!</b>\n"
            "⚡ <b>Удача на вашей стороне!</b>"
        ).format(balance)
        
        bot.send_message(message.chat.id, no_money_text, parse_mode='HTML')
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📝 ЗАКАЗАТЬ ВЫВОД", callback_data="request_withdraw"))
    
    withdraw_text = (
        "📤 <b>ВЫВОД СРЕДСТВ</b>\n\n"
        "💰 <b>Доступно для вывода:</b> <b>{} монет</b>\n"
        "💸 <b>Курс:</b> 1 монета = 1 торт\n\n"
        "📝 <b>Для вывода средств нажмите кнопку ниже</b>\n"
        "⏰ <b>Вывод обрабатывается вручную администратором</b>\n\n"
        "⚡ <b>Мгновенные выплаты!</b>"
    ).format(balance)
    
    bot.send_message(message.chat.id, withdraw_text, 
                    parse_mode='HTML', reply_markup=markup)

# Обработка заявки на вывод
@bot.callback_query_handler(func=lambda call: call.data == "request_withdraw")
def request_withdraw(call):
    user_id = call.from_user.id
    
    try:
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result else 0
    except Exception as e:
        print(f"Database error: {e}")
        balance = 0
    
    if balance < 1:
        bot.answer_callback_query(call.id, "❌ НЕДОСТАТОЧНО СРЕДСТВ!", show_alert=True)
        return
    
    # Создаем заявку на вывод
    try:
        cursor.execute("INSERT INTO withdrawals (user_id, amount, status, date) VALUES (?, ?, 'pending', ?)", 
                      (user_id, balance, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        # Обнуляем баланс с проверкой безопасности
        if safe_balance_update(user_id, -balance):
            conn.commit()
        else:
            cursor.execute("DELETE FROM withdrawals WHERE user_id = ? AND status = 'pending'", (user_id,))
            bot.answer_callback_query(call.id, "❌ Ошибка обработки вывода!", show_alert=True)
            return
            
    except Exception as e:
        print(f"Database error: {e}")
    
    withdraw_success_text = (
        "📨 <b>ЗАЯВКА НА ВЫВОД ОТПРАВЛЕНА!</b>\n\n"
        "✅ <b>Ваша заявка на вывод принята!</b>\n"
        "💰 <b>Сумма:</b> <b>{} монет</b>\n"
        "💸 <b>К получению:</b> <b>{} тортов</b>\n"
        "⏰ <b>Ожидайте проверки администратора</b>\n"
        "🆔 <b>Ваш ID:</b> <code>{}</code>\n\n"
        "⚡ <b>Выплата в течение 5 минут!</b>"
    ).format(balance, balance, user_id)
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                         text=withdraw_success_text, parse_mode='HTML')
    
    # Уведомление админам
    for admin_id in ADMINS:
        try:
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✅ ВЫПЛАТИТЬ", callback_data=f"pay_withdraw_{user_id}"),
                types.InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_withdraw_{user_id}")
            )
            
            admin_notification = (
                "📤 <b>НОВАЯ ЗАЯВКА НА ВЫВОД</b>\n\n"
                "👤 <b>Пользователь:</b> @{}\n"
                "🆔 <b>ID:</b> <code>{}</code>\n"
                "💰 <b>Сумма:</b> {} монет ({} тортов)\n"
                "📅 <b>Время:</b> {}\n\n"
                "⚡ <b>Ожидает выплаты</b>"
            ).format(call.from_user.username or 'Нет username', user_id, balance, balance,
                    datetime.now().strftime('%H:%M %d.%m.%Y'))
            
            bot.send_message(admin_id, admin_notification, 
                           parse_mode='HTML', reply_markup=markup)
        except Exception as e:
            print(f"Error sending to admin {admin_id}: {e}")

# Обработка выплаты вывода админом
@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_withdraw_"))
def pay_withdraw(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Доступ запрещен!", show_alert=True)
        log_security_event(call.from_user.id, "unauthorized_withdraw_pay", call.data)
        return
    
    try:
        user_id = int(call.data.split("_")[2])
        if not validate_user_id(user_id):
            raise ValueError("Invalid user ID")
    except:
        bot.answer_callback_query(call.id, "❌ Неверный запрос!", show_alert=True)
        return
    
    try:
        cursor.execute("SELECT amount FROM withdrawals WHERE user_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1", (user_id,))
        withdraw_data = cursor.fetchone()
        
        if withdraw_data:
            amount = withdraw_data[0]
            cursor.execute("UPDATE withdrawals SET status = 'paid' WHERE user_id = ? AND status = 'pending'", (user_id,))
            conn.commit()
            
            # Логируем действие
            log_admin_action(call.from_user.id, "pay_withdraw", user_id, f"Amount: {amount}")
            
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                 text=f"✅ <b>ВЫПЛАТА ВЫПОЛНЕНА</b>\n\n"
                                      f"👤 <b>Пользователь:</b> <code>{user_id}</code>\n"
                                      f"💰 <b>Сумма:</b> {amount} тортов\n"
                                      f"⏰ <b>Время:</b> {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
                                      f"✅ <b>Средства выплачены пользователю</b>",
                                 parse_mode='HTML')
            
            # Уведомляем пользователя
            try:
                bot.send_message(user_id,
                               f"💰 <b>ВЫВОД ВЫПОЛНЕН!</b>\n\n"
                               f"✅ <b>Ваша заявка на вывод выполнена</b>\n"
                               f"💸 <b>Сумма:</b> <b>{amount} тортов</b>\n"
                               f"📨 <b>Средства отправлены на ваш счет</b>\n\n"
                               f"🎮 <b>Спасибо за игру!</b>",
                               parse_mode='HTML')
            except:
                pass
    except Exception as e:
        print(f"Database error: {e}")

# Обработка отклонения вывода админом
@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_withdraw_"))
def reject_withdraw(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Доступ запрещен!", show_alert=True)
        log_security_event(call.from_user.id, "unauthorized_withdraw_reject", call.data)
        return
    
    try:
        user_id = int(call.data.split("_")[2])
        if not validate_user_id(user_id):
            raise ValueError("Invalid user ID")
    except:
        bot.answer_callback_query(call.id, "❌ Неверный запрос!", show_alert=True)
        return
    
    try:
        cursor.execute("SELECT amount FROM withdrawals WHERE user_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1", (user_id,))
        withdraw_data = cursor.fetchone()
        
        if withdraw_data:
            amount = withdraw_data[0]
            # Возвращаем средства на баланс с проверкой безопасности
            if safe_balance_update(user_id, amount):
                cursor.execute("UPDATE withdrawals SET status = 'rejected' WHERE user_id = ? AND status = 'pending'", (user_id,))
                conn.commit()
                
                # Логируем действие
                log_admin_action(call.from_user.id, "reject_withdraw", user_id, f"Amount: {amount}")
                
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                     text=f"❌ <b>ВЫВОД ОТКЛОНЕН</b>\n\n"
                                          f"👤 <b>Пользователь:</b> <code>{user_id}</code>\n"
                                          f"💰 <b>Сумма:</b> {amount} монет\n"
                                          f"⏰ <b>Время:</b> {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
                                          f"❌ <b>Заявка отклонена, средства возвращены</b>",
                                     parse_mode='HTML')
                
                # Уведомляем пользователя
                try:
                    bot.send_message(user_id,
                                   f"❌ <b>ВЫВОД ОТКЛОНЕН</b>\n\n"
                                   f"😢 <b>Ваша заявка на вывод отклонена</b>\n"
                                   f"💎 <b>Сумма возвращена на ваш баланс</b>\n"
                                   f"📞 <b>Свяжитесь с поддержкой для уточнения</b>\n\n"
                                   f"💎 @Gifts_456",
                                   parse_mode='HTML')
                except:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка возврата средств!", show_alert=True)
    except Exception as e:
        print(f"Database error: {e}")

# О Казино
@bot.message_handler(func=lambda message: message.text == '🎰 О КАЗИНО')
def about_casino(message):
    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM games")
        total_games = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(bet) FROM games")
        total_bet_result = cursor.fetchone()
        total_bet = total_bet_result[0] if total_bet_result[0] else 0
    except Exception as e:
        print(f"Database error: {e}")
        total_users = 0
        total_games = 0
        total_bet = 0
    
    about_text = (
        "🎰 <b>CASINODROP - ИНФОРМАЦИЯ</b>\n\n"
        "📊 <b>СТАТИСТИКА БОТА:</b>\n"
        "👥 <b>Всего пользователей:</b> <b>{}</b>\n"
        "🎮 <b>Сыграно игр:</b> <b>{}</b>\n"
        "💵 <b>Общий оборот:</b> <b>{} монет</b>\n\n"
        "🎯 <b>ПРАВИЛА ИГРЫ:</b>\n"
        "• 🎰 <b>Шанс выигрыша:</b> 40%\n"
        "• 💀 <b>Шанс проигрыша:</b> 60%\n"
        "• 💰 <b>Выигрыш:</b> 2x от ставки\n"
        "• 💎 <b>Минимальная ставка:</b> 1 монета\n\n"
        "💎 <b>ВАЛЮТА:</b>\n"
        "1 торт = 1 монета\n\n"
        "📢 <b>ОБЯЗАТЕЛЬНАЯ ПОДПИСКА:</b>\n"
        "@CasinoDrop\n\n"
        "⚡ <b>Быстрая игра</b>\n"
        "🔒 <b>Честная система</b>\n"
        "👑 <b>Поддержка 24/7</b>\n"
        "💰 <b>Мгновенные выплаты</b>"
    ).format(total_users, total_games, total_bet)
    
    bot.send_message(message.chat.id, about_text, parse_mode='HTML')

# АДМИН ФУНКЦИИ

# Админ - статистика
@bot.message_handler(func=lambda message: message.text == '📊 СТАТИСТИКА' and message.from_user.id in ADMINS)
def admin_stats(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ <b>Доступ запрещен!</b>", parse_mode='HTML')
        return
        
    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM games")
        total_games = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(bet) FROM games")
        total_bet_result = cursor.fetchone()
        total_bet = total_bet_result[0] if total_bet_result[0] else 0
        
        cursor.execute("SELECT SUM(win_amount) FROM games")
        total_win_result = cursor.fetchone()
        total_win = total_win_result[0] if total_win_result[0] else 0
        
        cursor.execute("SELECT COUNT(*) FROM deposits WHERE status = 'accepted'")
        total_deposits = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status = 'paid'")
        total_withdrawals = cursor.fetchone()[0]
        
        profit = total_bet - total_win
        
        stats_text = (
            "👑 <b>СТАТИСТИКА СИСТЕМЫ</b>\n\n"
            "👥 <b>Пользователей:</b> <b>{}</b>\n"
            "🎮 <b>Сыграно игр:</b> <b>{}</b>\n"
            "💵 <b>Общий оборот:</b> <b>{} монет</b>\n"
            "💰 <b>Выплачено выигрышей:</b> <b>{} монет</b>\n"
            "💸 <b>Прибыль системы:</b> <b>{} монет</b>\n\n"
            "📥 <b>Пополнений:</b> <b>{}</b>\n"
            "📤 <b>Выводов:</b> <b>{}</b>\n\n"
            "📅 <b>Дата:</b> {}"
        ).format(total_users, total_games, total_bet, total_win, profit, 
                 total_deposits, total_withdrawals, datetime.now().strftime('%d.%m.%Y %H:%M'))
        
        bot.send_message(message.chat.id, stats_text, parse_mode='HTML')
    except Exception as e:
        print(f"Database error: {e}")

# Админ - заявки пополнения
@bot.message_handler(func=lambda message: message.text == '📥 ЗАЯВКИ ПОПОЛНЕНИЯ' and message.from_user.id in ADMINS)
def admin_deposits(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ <b>Доступ запрещен!</b>", parse_mode='HTML')
        return
        
    try:
        cursor.execute("SELECT d.user_id, u.username, d.amount, d.date FROM deposits d LEFT JOIN users u ON d.user_id = u.id WHERE d.status = 'pending' ORDER BY d.id DESC")
        pending_deposits = cursor.fetchall()
        
        if not pending_deposits:
            bot.send_message(message.chat.id, "📭 <b>НЕТ ОЖИДАЮЩИХ ЗАЯВОК</b>", parse_mode='HTML')
            return
        
        text = "📥 <b>ОЖИДАЮЩИЕ ЗАЯВКИ ПОПОЛНЕНИЯ</b>\n\n"
        
        for deposit in pending_deposits:
            user_id, username, amount, date = deposit
            text += f"👤 @{username or 'Нет username'} | ID: <code>{user_id}</code>\n"
            text += f"💰 Сумма: {amount} монет\n"
            text += f"📅 {date}\n"
            text += "─" * 30 + "\n"
        
        bot.send_message(message.chat.id, text, parse_mode='HTML')
    except Exception as e:
        print(f"Database error: {e}")

# Админ - заявки вывода
@bot.message_handler(func=lambda message: message.text == '📤 ЗАЯВКИ ВЫВОДА' and message.from_user.id in ADMINS)
def admin_withdrawals(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ <b>Доступ запрещен!</b>", parse_mode='HTML')
        return
        
    try:
        cursor.execute("SELECT w.user_id, u.username, w.amount, w.date FROM withdrawals w LEFT JOIN users u ON w.user_id = u.id WHERE w.status = 'pending' ORDER BY w.id DESC")
        pending_withdrawals = cursor.fetchall()
        
        if not pending_withdrawals:
            bot.send_message(message.chat.id, "📭 <b>НЕТ ОЖИДАЮЩИХ ЗАЯВОК</b>", parse_mode='HTML')
            return
        
        text = "📤 <b>ОЖИДАЮЩИЕ ЗАЯВКИ ВЫВОДА</b>\n\n"
        
        for withdrawal in pending_withdrawals:
            user_id, username, amount, date = withdrawal
            text += f"👤 @{username or 'Нет username'} | ID: <code>{user_id}</code>\n"
            text += f"💰 Сумма: {amount} монет ({amount} тортов)\n"
            text += f"📅 {date}\n"
            text += "─" * 30 + "\n"
        
        bot.send_message(message.chat.id, text, parse_mode='HTML')
    except Exception as e:
        print(f"Database error: {e}")

# Админ - список пользователей
@bot.message_handler(func=lambda message: message.text == '👥 ПОЛЬЗОВАТЕЛИ' and message.from_user.id in ADMINS)
def admin_users(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ <b>Доступ запрещен!</b>", parse_mode='HTML')
        return
        
    try:
        cursor.execute("SELECT id, username, balance, reg_date FROM users ORDER BY id DESC LIMIT 10")
        users = cursor.fetchall()
        
        text = "👥 <b>ПОСЛЕДНИЕ 10 ПОЛЬЗОВАТЕЛЕЙ</b>\n\n"
        
        for user in users:
            user_id, username, balance, reg_date = user
            text += f"👤 @{username or 'Нет username'}\n"
            text += f"🆔 ID: <code>{user_id}</code>\n"
            text += f"💎 Баланс: {balance} монет\n"
            text += f"📅 {reg_date}\n"
            text += "─" * 30 + "\n"
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        text += f"\n📊 <b>Всего пользователей:</b> <b>{total_users}</b>"
        
        bot.send_message(message.chat.id, text, parse_mode='HTML')
    except Exception as e:
        print(f"Database error: {e}")

# Админ - логи
@bot.message_handler(func=lambda message: message.text == '📋 ЛОГИ' and message.from_user.id in ADMINS)
def admin_logs(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ <b>Доступ запрещен!</b>", parse_mode='HTML')
        return
        
    try:
        cursor.execute("SELECT al.admin_id, al.action, al.target_user, al.details, al.date, u.username FROM admin_logs al LEFT JOIN users u ON al.target_user = u.id ORDER BY al.id DESC LIMIT 20")
        logs = cursor.fetchall()
        
        text = "📋 <b>ПОСЛЕДНИЕ 20 ЛОГОВ</b>\n\n"
        
        for log in logs:
            admin_id, action, target_user, details, date, target_username = log
            text += f"👤 <b>Админ:</b> <code>{admin_id}</code>\n"
            text += f"⚡ <b>Действие:</b> {action}\n"
            if target_user:
                text += f"🎯 <b>Цель:</b> @{target_username or 'Нет username'} (<code>{target_user}</code>)\n"
            if details:
                text += f"📝 <b>Детали:</b> {details}\n"
            text += f"📅 <b>Время:</b> {date}\n"
            text += "─" * 30 + "\n"
        
        if not logs:
            text += "📭 <b>Логов пока нет</b>"
        
        bot.send_message(message.chat.id, text, parse_mode='HTML')
    except Exception as e:
        print(f"Database error: {e}")

# Админ - аннулировать баланс
@bot.message_handler(func=lambda message: message.text == '⚡ АННУЛИРОВАТЬ БАЛАНС' and message.from_user.id in ADMINS)
def annul_balance(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ <b>Доступ запрещен!</b>", parse_mode='HTML')
        return
        
    msg = bot.send_message(message.chat.id, 
                          "⚡ <b>АННУЛИРОВАНИЕ БАЛАНСА</b>\n\n"
                          "Введите ID пользователя для аннулирования баланса:",
                          parse_mode='HTML')
    bot.register_next_step_handler(msg, process_annul_user_id)

def process_annul_user_id(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ <b>Доступ запрещен!</b>", parse_mode='HTML')
        return
        
    try:
        user_id = int(message.text)
        
        if not validate_user_id(user_id):
            bot.send_message(message.chat.id, "❌ <b>Неверный ID пользователя!</b>", parse_mode='HTML')
            return
        
        # Проверяем существование пользователя
        cursor.execute("SELECT username, balance FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            bot.send_message(message.chat.id, "❌ <b>Пользователь не найден!</b>", parse_mode='HTML')
            return
        
        username, current_balance = user_data
        
        msg = bot.send_message(message.chat.id,
                              f"👤 <b>Пользователь:</b> @{username or 'Нет username'}\n"
                              f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                              f"💰 <b>Текущий баланс:</b> {current_balance} монет\n\n"
                              f"Введите сумму для аннулирования (0 для полного обнуления):",
                              parse_mode='HTML')
        bot.register_next_step_handler(msg, process_annul_amount, user_id, username, current_balance)
    except ValueError:
        bot.send_message(message.chat.id, "❌ <b>Неверный формат ID!</b>", parse_mode='HTML')

def process_annul_amount(message, user_id, username, current_balance):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ <b>Доступ запрещен!</b>", parse_mode='HTML')
        return
        
    try:
        amount = int(message.text)
        
        if amount < 0:
            bot.send_message(message.chat.id, "❌ <b>Сумма не может быть отрицательной!</b>", parse_mode='HTML')
            return
        
        if amount == 0:
            # Полное обнуление
            new_balance = 0
            amount_to_remove = current_balance
        else:
            if amount > current_balance:
                bot.send_message(message.chat.id, "❌ <b>Сумма превышает текущий баланс!</b>", parse_mode='HTML')
                return
            new_balance = current_balance - amount
            amount_to_remove = amount
        
        # Обновляем баланс с проверкой безопасности
        if safe_balance_update(user_id, -amount_to_remove):
            # Логируем действие
            log_admin_action(message.from_user.id, "annul_balance", user_id, f"Removed: {amount_to_remove}, New balance: {new_balance}")
            
            result_text = (
                "✅ <b>БАЛАНС АННУЛИРОВАН</b>\n\n"
                "👤 <b>Пользователь:</b> @{}\n"
                "🆔 <b>ID:</b> <code>{}</code>\n"
                "💰 <b>Аннулировано:</b> {} монет\n"
                "💎 <b>Новый баланс:</b> {} монет\n"
                "⏰ <b>Время:</b> {}\n\n"
                "⚡ <b>Операция выполнена успешно!</b>"
            ).format(username, user_id, amount_to_remove, new_balance, datetime.now().strftime('%H:%M %d.%m.%Y'))
            
            bot.send_message(message.chat.id, result_text, parse_mode='HTML')
            
            # Уведомляем пользователя
            try:
                if amount_to_remove > 0:
                    bot.send_message(user_id,
                                   f"⚠️ <b>АННУЛИРОВАНИЕ БАЛАНСА</b>\n\n"
                                   f"💰 <b>Списано:</b> {amount_to_remove} монет\n"
                                   f"💎 <b>Текущий баланс:</b> {new_balance} монет\n\n"
                                   f"📞 <b>По вопросам обращайтесь к администратору</b>",
                                   parse_mode='HTML')
            except:
                pass
        else:
            bot.send_message(message.chat.id, "❌ <b>Ошибка обновления баланса!</b>", parse_mode='HTML')
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ <b>Неверный формат суммы!</b>", parse_mode='HTML')

# Обработка кнопки "Нет денег"
@bot.callback_query_handler(func=lambda call: call.data == "no_money")
def no_money(call):
    bot.answer_callback_query(call.id, "❌ НЕДОСТАТОЧНО СРЕДСТВ НА БАЛАНСЕ!", show_alert=True)

# Назад к играм
@bot.callback_query_handler(func=lambda call: call.data == "back_to_games")
def back_to_games(call):
    play(call.message)

# Профиль через callback
@bot.callback_query_handler(func=lambda call: call.data == "profile")
def profile_callback(call):
    user_id = call.from_user.id
    
    try:
        cursor.execute("SELECT username, balance, wins, losses, total_bet, reg_date FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
    except Exception as e:
        print(f"Database error: {e}")
        user_data = None
    
    if user_data:
        username, balance, wins, losses, total_bet, reg_date = user_data
        total_games = wins + losses
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        profile_text = (
            "📊 <b>ВАШ ПРОФИЛЬ</b>\n\n"
            "👤 <b>Игрок:</b> <b>@{}</b>\n"
            "🆔 <b>ID:</b> <code>{}</code>\n"
            "💎 <b>Баланс:</b> <b>{} монет</b>\n\n"
            "🎮 <b>СТАТИСТИКА ИГР:</b>\n"
            "✅ <b>Побед:</b> <b>{}</b>\n"
            "❌ <b>Поражений:</b> <b>{}</b>\n"
            "📈 <b>Винрейт:</b> <b>{:.1f}%</b>\n"
            "💵 <b>Всего ставок:</b> <b>{} монет</b>\n\n"
            "📅 <b>Регистрация:</b> {}\n\n"
            "⚡ <b>Продолжайте в том же духе!</b>"
        ).format(username, user_id, balance, wins, losses, win_rate, total_bet, reg_date)
        
        bot.send_message(call.message.chat.id, profile_text, parse_mode='HTML')

# Запуск бота
if __name__ == "__main__":
    print("🎰 CASINODROP BOT ЗАПУЩЕН!")
    print("⚡ Бот готов к работе!")
    print("🔒 Режим безопасности активирован!")
    print("👑 Админы:", ADMINS)
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Bot error: {e}")