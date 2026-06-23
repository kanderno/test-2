"""
Telegram-бот для записи клиентов — Malika HairColor 💛
Запуск: python bot.py
"""

import logging
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ─── НАСТРОЙКИ ────────────────────────────────────────────────────────────────
BOT_TOKEN = "8996912351:AAG4ZHXVAWF1xyOeHAQDeFgcMTnJjydIteg"
MASTER_CHAT_ID = 1717846178
MASTER_USERNAME = "@malika_haircolor"

# ─── УСЛУГИ ───────────────────────────────────────────────────────────────────
SERVICES = {
    "blond":     {"name": "✨ Блонд (полное осветление)",     "price": "от 25 000 ₸", "duration": "3–5 ч"},
    "balayage":  {"name": "🌅 Балаяж / Шатуш",               "price": "от 30 000 ₸", "duration": "3–4 ч"},
    "highlights":{"name": "💛 Мелирование",                   "price": "от 20 000 ₸", "duration": "2–3 ч"},
    "toning":    {"name": "🎨 Тонирование / Глоссинг",        "price": "от 8 000 ₸",  "duration": "1–1.5 ч"},
    "correction":{"name": "🔧 Коррекция цвета",               "price": "от 15 000 ₸", "duration": "2–4 ч"},
    "care":      {"name": "💆 Восстановление (Olaplex и др.)", "price": "от 10 000 ₸", "duration": "1–2 ч"},
}

# ─── ДОСТУПНОЕ ВРЕМЯ ──────────────────────────────────────────────────────────
TIME_SLOTS = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]

# ─── ШАГИ ДИАЛОГА ─────────────────────────────────────────────────────────────
ASK_PHONE, ASK_SERVICE, ASK_DATE, ASK_TIME, ASK_COMMENT, CONFIRM = range(6)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════════════════════

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Записаться на приём",  callback_data="book")],
        [InlineKeyboardButton("💰 Прайс-лист",           callback_data="price")],
        [InlineKeyboardButton("📸 Портфолио (Instagram)", url="https://www.instagram.com/malika_haircolor")],
        [InlineKeyboardButton("📍 Адрес и контакты",     callback_data="contacts")],
        [InlineKeyboardButton("❓ FAQ",                   callback_data="faq")],
    ])


def services_keyboard():
    rows = []
    for key, svc in SERVICES.items():
        rows.append([InlineKeyboardButton(svc["name"], callback_data=f"svc_{key}")])
    rows.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


def dates_keyboard():
    """Ближайшие 14 дней (кроме воскресенья)."""
    rows = []
    today = datetime.now().date()
    available = []
    d = today + timedelta(days=1)
    while len(available) < 12:
        if d.weekday() != 6:          # 6 = воскресенье — выходной
            available.append(d)
        d += timedelta(days=1)

    day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for i in range(0, len(available), 2):
        row = []
        for date in available[i:i+2]:
            label = f"{day_names[date.weekday()]} {date.strftime('%d.%m')}"
            row.append(InlineKeyboardButton(label, callback_data=f"date_{date.isoformat()}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 Назад", callback_data="back_service")])
    return InlineKeyboardMarkup(rows)


def times_keyboard():
    rows = []
    for i in range(0, len(TIME_SLOTS), 3):
        row = [InlineKeyboardButton(t, callback_data=f"time_{t}") for t in TIME_SLOTS[i:i+3]]
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 Назад", callback_data="back_date")])
    return InlineKeyboardMarkup(rows)


def confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить запись", callback_data="confirm_yes")],
        [InlineKeyboardButton("✏️ Изменить",           callback_data="confirm_edit")],
        [InlineKeyboardButton("❌ Отменить",            callback_data="back_main")],
    ])


def booking_summary(data: dict) -> str:
    svc = SERVICES.get(data.get("service", ""), {})
    date_str = data.get("date", "—")
    try:
        d = datetime.fromisoformat(date_str)
        date_str = d.strftime("%d.%m.%Y (%A)").replace(
            "Monday","Пн").replace("Tuesday","Вт").replace("Wednesday","Ср"
            ).replace("Thursday","Чт").replace("Friday","Пт").replace("Saturday","Сб")
    except Exception:
        pass
    lines = [
        "📋 *Ваша запись:*",
        f"👤 Имя: {data.get('name', '—')}",
        f"📞 Телефон: {data.get('phone', '—')}",
        f"💇 Услуга: {svc.get('name', '—')}",
        f"💰 Стоимость: {svc.get('price', '—')}",
        f"⏱ Длительность: {svc.get('duration', '—')}",
        f"📅 Дата: {date_str}",
        f"🕐 Время: {data.get('time', '—')}",
    ]
    comment = data.get("comment", "").strip()
    if comment:
        lines.append(f"💬 Комментарий: {comment}")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  КОМАНДЫ
# ══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    user = update.effective_user
    text = (
        f"Привет, {user.first_name}! 👋\n\n"
        "Добро пожаловать к *Малике* — мастеру по окрашиванию волос 💛\n\n"
        "Здесь вы можете:\n"
        "• Записаться на приём\n"
        "• Узнать цены и услуги\n"
        "• Посмотреть портфолио\n\n"
        "Выберите, что вас интересует 👇"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def menu_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Главное меню 👇", reply_markup=main_menu_keyboard()
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACK-КНОПКИ (меню, прайс, контакты, FAQ)
# ══════════════════════════════════════════════════════════════════════════════

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    # ── Главное меню ──
    if data == "back_main":
        ctx.user_data.clear()
        await q.edit_message_text(
            "Главное меню 👇", reply_markup=main_menu_keyboard()
        )

    elif data == "price":
        lines = ["💰 *Прайс-лист Malika HairColor*\n"]
        for svc in SERVICES.values():
            lines.append(f"{svc['name']}\n   {svc['price']} · {svc['duration']}\n")
        lines.append("_Точная цена определяется на консультации в зависимости от длины и состояния волос._")
        await q.edit_message_text(
            "\n".join(lines), parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]])
        )

    elif data == "contacts":
        text = (
            "📍 *Контакты*\n\n"
            f"📱 Instagram: {MASTER_USERNAME}\n"
            "📞 WhatsApp / Telegram: напишите в личку\n"
            "🏙 Город: Астана\n\n"
            "_Точный адрес салона уточняйте при записи._"
        )
        await q.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]])
        )

    elif data == "faq":
        text = (
            "❓ *Частые вопросы*\n\n"
            "*Как подготовиться к окрашиванию?*\n"
            "Не мойте волосы за 1–2 дня, придите с чистыми, но не свежевымытыми волосами.\n\n"
            "*Сколько держится окрашивание?*\n"
            "Балаяж и мелирование — 3–6 месяцев. Тонирование — 4–6 недель.\n\n"
            "*Можно ли записаться с химической завивкой?*\n"
            "Да, но требуется консультация — уточните при записи.\n\n"
            "*Как ухаживать после окрашивания?*\n"
            "Рекомендую шампуни и маски для окрашенных волос, минимальный термоукладка.\n\n"
            "*Есть ли скидки?*\n"
            "Да! Постоянным клиентам и при рекомендации подруги — спросите Малику 💛"
        )
        await q.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]])
        )

    # ── Начало бронирования ──
    elif data == "book":
        ctx.user_data.clear()
        await q.edit_message_text(
            "💇 *Запись на приём*\n\nВыберите услугу 👇",
            parse_mode="Markdown", reply_markup=services_keyboard()
        )
        return ASK_SERVICE

    # ── Выбор услуги ──
    elif data.startswith("svc_"):
        key = data[4:]
        ctx.user_data["service"] = key
        svc = SERVICES[key]
        await q.edit_message_text(
            f"Вы выбрали: *{svc['name']}*\n"
            f"💰 {svc['price']} · ⏱ {svc['duration']}\n\n"
            "📅 Выберите удобную дату 👇",
            parse_mode="Markdown", reply_markup=dates_keyboard()
        )
        return ASK_DATE

    elif data == "back_service":
        await q.edit_message_text(
            "💇 Выберите услугу 👇",
            parse_mode="Markdown", reply_markup=services_keyboard()
        )
        return ASK_SERVICE

    # ── Выбор даты ──
    elif data.startswith("date_"):
        ctx.user_data["date"] = data[5:]
        await q.edit_message_text(
            "🕐 Выберите удобное время 👇",
            reply_markup=times_keyboard()
        )
        return ASK_TIME

    elif data == "back_date":
        await q.edit_message_text(
            "📅 Выберите удобную дату 👇",
            reply_markup=dates_keyboard()
        )
        return ASK_DATE

    # ── Выбор времени ──
    elif data.startswith("time_"):
        ctx.user_data["time"] = data[5:]
        await q.edit_message_text(
            "✍️ Введите ваше *имя* для записи:",
            parse_mode="Markdown"
        )
        ctx.user_data["step"] = "name"
        return ASK_PHONE

    # ── Подтверждение ──
    elif data == "confirm_yes":
        await send_booking_to_master(ctx.user_data, ctx)
        await q.edit_message_text(
            "✅ *Запись принята!*\n\n"
            f"{booking_summary(ctx.user_data)}\n\n"
            "Малика свяжется с вами для подтверждения.\n"
            "До встречи! 💛",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]])
        )
        ctx.user_data.clear()
        return ConversationHandler.END

    elif data == "confirm_edit":
        await q.edit_message_text(
            "💇 Начнём заново — выберите услугу 👇",
            reply_markup=services_keyboard()
        )
        return ASK_SERVICE


# ══════════════════════════════════════════════════════════════════════════════
#  ТЕКСТОВЫЕ ШАГИ (имя → телефон → комментарий → подтверждение)
# ══════════════════════════════════════════════════════════════════════════════

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    step = ctx.user_data.get("step", "name")

    if step == "name":
        if len(text) < 2:
            await update.message.reply_text("Пожалуйста, введите корректное имя.")
            return ASK_PHONE
        ctx.user_data["name"] = text
        ctx.user_data["step"] = "phone"

        # Кнопка «Поделиться номером»
        kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await update.message.reply_text(
            f"Отлично, *{text}*! 👋\n\n"
            "Введите ваш номер телефона или нажмите кнопку ниже:",
            parse_mode="Markdown", reply_markup=kb
        )
        return ASK_PHONE

    elif step == "phone":
        # Принимаем как текст
        phone = text
        if not any(c.isdigit() for c in phone):
            await update.message.reply_text("Введите номер телефона (цифры).")
            return ASK_PHONE
        ctx.user_data["phone"] = phone
        return await ask_comment(update, ctx)

    elif step == "comment":
        ctx.user_data["comment"] = text if text not in ["—", "Без комментария"] else ""
        return await show_confirm(update, ctx)

    return ASK_PHONE


async def contact_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Получение номера через кнопку 'Поделиться номером'."""
    from telegram import ReplyKeyboardRemove
    contact = update.message.contact
    ctx.user_data["phone"] = contact.phone_number
    await update.message.reply_text("✅ Номер получен!", reply_markup=ReplyKeyboardRemove())
    return await ask_comment(update, ctx)


async def ask_comment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["step"] = "comment"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Без комментария →", callback_data="skip_comment")]
    ])
    await update.message.reply_text(
        "💬 Есть пожелания или вопросы к мастеру?\n_(длина волос, желаемый результат, аллергии и т.д.)_\n\n"
        "Или нажмите кнопку ниже, если нет:",
        parse_mode="Markdown", reply_markup=kb
    )
    return ASK_COMMENT


async def skip_comment_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["comment"] = ""
    await q.edit_message_text("Хорошо, без комментария!")
    return await show_confirm_query(q, ctx)


async def show_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    summary = booking_summary(ctx.user_data)
    await update.message.reply_text(
        f"{summary}\n\nВсё верно?",
        parse_mode="Markdown", reply_markup=confirm_keyboard()
    )
    return CONFIRM


async def show_confirm_query(q, ctx: ContextTypes.DEFAULT_TYPE):
    summary = booking_summary(ctx.user_data)
    await q.message.reply_text(
        f"{summary}\n\nВсё верно?",
        parse_mode="Markdown", reply_markup=confirm_keyboard()
    )
    return CONFIRM


# ══════════════════════════════════════════════════════════════════════════════
#  УВЕДОМЛЕНИЕ МАСТЕРУ
# ══════════════════════════════════════════════════════════════════════════════

async def send_booking_to_master(data: dict, ctx: ContextTypes.DEFAULT_TYPE):
    svc = SERVICES.get(data.get("service", ""), {})
    date_str = data.get("date", "—")
    try:
        d = datetime.fromisoformat(date_str)
        date_str = d.strftime("%d.%m.%Y")
    except Exception:
        pass

    text = (
        "🔔 *Новая запись!*\n\n"
        f"👤 {data.get('name', '—')}\n"
        f"📞 {data.get('phone', '—')}\n"
        f"💇 {svc.get('name', '—')}\n"
        f"📅 {date_str} в {data.get('time', '—')}\n"
        f"⏱ {svc.get('duration', '—')}\n"
        f"💰 {svc.get('price', '—')}\n"
    )
    comment = data.get("comment", "").strip()
    if comment:
        text += f"💬 {comment}\n"

    try:
        await ctx.bot.send_message(
            chat_id=MASTER_CHAT_ID, text=text, parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление мастеру: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  ОТМЕНА И ОШИБКИ
# ══════════════════════════════════════════════════════════════════════════════

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text(
        "Запись отменена. Возвращайтесь, когда будете готовы! 💛",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END


async def unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Используйте кнопки меню или введите /start",
        reply_markup=main_menu_keyboard()
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════════════════════════════════════

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler для бронирования
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^book$")],
        states={
            ASK_SERVICE: [
                CallbackQueryHandler(button_handler, pattern="^(svc_|back_main|back_service)"),
            ],
            ASK_DATE: [
                CallbackQueryHandler(button_handler, pattern="^(date_|back_service|back_main)"),
            ],
            ASK_TIME: [
                CallbackQueryHandler(button_handler, pattern="^(time_|back_date|back_main)"),
            ],
            ASK_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler),
                MessageHandler(filters.CONTACT, contact_handler),
            ],
            ASK_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler),
                CallbackQueryHandler(skip_comment_handler, pattern="^skip_comment$"),
            ],
            CONFIRM: [
                CallbackQueryHandler(button_handler, pattern="^(confirm_yes|confirm_edit|back_main)$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu",  menu_command))
    app.add_handler(conv)

    # Прочие кнопки меню (вне бронирования)
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("Бот запущен ✅")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
