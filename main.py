import asyncio import logging from aiogram import Bot, Dispatcher, F, Router, types from aiogram.filters import CommandStart from aiogram.fsm.context import FSMContext from aiogram.fsm.state import State, StatesGroup from aiogram.fsm.storage.memory import MemoryStorage from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
----------------- КОНФИГУРАЦИЯ (Ваши данные) -----------------
BOT_TOKEN = "8952006747:AAGgeoyeL7N2JpmYDha2SqoJglPwbdleJ8Y" ADMIN_ID = 5897493181 CARD_NUMBER = "4441 1110 6793 7569 (Монобанк — Діана С.)"
Текст правил
RULES_TEXT = ( "📄 Правила сервиса:\n\n" "1. Время ожидания: После создания заявки продавец должен принять её в течение 10 минут. " "Если сделка не принята вовремя, она автоматически аннулируется.\n" "2. Безопасность: Все звёзды являются полностью чистыми и приобретаются легальным путем. " "Риск списания (рефла) с вашего баланса исключен.\n" "3. Порядок оплаты: Оплата производится исключительно в гривнах (UAH) по реквизитам, " "предоставленным в боте после принятия сделки. Обязательно сохраняйте скриншот чека." )
----------------- FSM СОСТОЯНИЯ -----------------
class OrderState(StatesGroup): waiting_for_stars = State() waiting_for_username = State() waiting_for_acceptance = State() waiting_for_receipt = State() waiting_for_admin_proof = State() waiting_for_review = State()
bot = Bot(token=BOT_TOKEN) dp = Dispatcher(storage=MemoryStorage()) router = Router()
Словарь для отслеживания активных заявок (user_id -> order_status)
active_orders = {}
----------------- ХЕНДЛЕРЫ -----------------
@router.message(CommandStart()) async def cmd_start(message: types.Message, state: FSMContext): await state.clear() text = ( "👋 Добро пожаловать в официальный бот по продаже Telegram Stars за гривны!\n\n" "📈 Актуальный курс:\n" "• От 50 ⭐ — 0.80 грн / шт.\n" "• От 100 ⭐ — 0.75 грн / шт.\n\n" "⚠️ Важные условия:\n" "• Минимальный заказ — 50 звезд.\n" "• Звезды поступают напрямую на баланс вашего аккаунта.\n\n" "💬 По всем вопросам и для поддержки обращайтесь: @frosyyy" ) kb = InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text="⭐ Купить звёзды", callback_query_data="buy_stars")], [ InlineKeyboardButton(text="⭐ Отзывы", url="https://t.me/otzfrosy"), InlineKeyboardButton(text="📄 Правила", callback_query_data="show_rules") ] ]) await message.answer(text, reply_markup=kb, parse_mode="Markdown")
@router.callback_query(F.data == "show_rules") async def show_rules_handler(call: types.CallbackQuery): kb = InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text="⬅️ Назад в меню", callback_query_data="back_to_start")] ]) await call.message.edit_text(RULES_TEXT, reply_markup=kb, parse_mode="Markdown") await call.answer()
@router.callback_query(F.data == "back_to_start") async def back_to_start_handler(call: types.CallbackQuery, state: FSMContext): await cmd_start(call.message, state) await call.answer()
@router.callback_query(F.data == "buy_stars") async def ask_stars_count(call: types.CallbackQuery, state: FSMContext): await call.message.answer("Введите количество Stars, которое хотите купить (минимум 50):") await state.set_state(OrderState.waiting_for_stars) await call.answer()
@router.message(OrderState.waiting_for_stars) async def process_stars_count(message: types.Message, state: FSMContext): if not message.text.isdigit(): await message.answer("Пожалуйста, введите число (например: 50 или 100).") return
stars = int(message.text)
if stars < 50:
    await message.answer("Минимальный заказ — 50 Stars. Введите другое количество:")
    return

rate = 0.75 if stars >= 100 else 0.80
total_price = round(stars * rate, 2)

await state.update_data(stars=stars, price=total_price, rate=rate)
await message.answer(
    f"✅ **Детали заказа:**\n"
    f"• Количество: {stars} ⭐\n"
    f"• Курс: {rate} грн/шт\n"
    f"• Итого к оплате: **{total_price} грн**\n\n"
    f"Теперь укажите `@username` пользователя, которому зачислить звёзды:"
)
await state.set_state(OrderState.waiting_for_username)
@router.message(OrderState.waiting_for_username) async def process_username(message: types.Message, state: FSMContext): username = message.text.strip() if not username.startswith("@"): username = "@" + username
user_id = message.from_user.id
await state.update_data(target_username=username, user_id=user_id)
data = await state.get_data()

active_orders[user_id] = "waiting_acceptance"

await message.answer(
    "⏳ Ваша заявка отправлена продавцу. У него есть **10 минут** на её подтверждение."
)

admin_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✅ Принять сделку", callback_query_data=f"accept_{user_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_query_data=f"reject_{user_id}")
    ]
])

admin_msg = await bot.send_message(
    chat_id=ADMIN_ID,
    text=(
        f"🔔 **Новая заявка на сделку!**\n\n"
        f"• Покупатель: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"• Получатель: {data['target_username']}\n"
        f"• Кол-во: {data['stars']} ⭐\n"
        f"• К оплате: **{data['price']} грн**\n\n"
        f"⏱ *Срок принятия: 10 минут.*"
    ),
    reply_markup=admin_kb,
    parse_mode="Markdown"
)

await state.set_state(OrderState.waiting_for_acceptance)
asyncio.create_task(order_timeout_timer(user_id, admin_msg.message_id, state))
async def order_timeout_timer(user_id: int, admin_msg_id: int, state: FSMContext): await asyncio.sleep(600)  # 10 минут
if active_orders.get(user_id) == "waiting_acceptance":
    active_orders.pop(user_id, None)
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ **Сделка отменена автоматически:** продавец не принял её в течение 10 минут."
        )
    except Exception:
        pass

    try:
        await bot.edit_message_text(
            chat_id=ADMIN_ID,
            message_id=admin_msg_id,
            text="❌ **Заявка просрочена и отменена (прошло 10 минут).**",
            parse_mode="Markdown"
        )
    except Exception:
        pass
        
    await state.clear()
@router.callback_query(F.data.startswith("accept_")) async def admin_accept_deal(call: types.CallbackQuery, state: FSMContext): user_id = int(call.data.split("_")[1])
if active_orders.get(user_id) != "waiting_acceptance":
    await call.answer("Эта сделка уже отменена или обработана!", show_alert=True)
    return

active_orders[user_id] = "waiting_receipt"
await state.update_data(current_client_id=user_id)

user_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💳 Подтвердить оплату (Отправить чек)", callback_query_data="send_receipt")]
])

await bot.send_message(
    chat_id=user_id,
    text=(
        "🎉 **Продавец принял сделку!**\n\n"
        f"Переведите сумму на карту:\n`{CARD_NUMBER}`\n\n"
        "После оплаты нажмите кнопку ниже и отправьте **скриншот чека**."
    ),
    reply_markup=user_kb,
    parse_mode="Markdown"
)
await call.message.edit_text(call.message.text + "\n\n✅ **Сделка принята вами.**")
await call.answer("Сделка принята")
@router.callback_query(F.data.startswith("reject_")) async def admin_reject_deal(call: types.CallbackQuery, state: FSMContext): user_id = int(call.data.split("_")[1]) active_orders.pop(user_id, None)
await bot.send_message(chat_id=user_id, text="❌ Продавец отклонил сделку на данный момент.")
await call.message.edit_text(call.message.text + "\n\n❌ **Сделка отклонена.**")
await call.answer("Отклонено")
@router.callback_query(F.data == "send_receipt") async def prompt_receipt(call: types.CallbackQuery, state: FSMContext): await call.message.answer("Пожалуйста, отправьте фото/скриншот чека об оплате:") await state.set_state(OrderState.waiting_for_receipt) await call.answer()
@router.message(OrderState.waiting_for_receipt, F.photo) async def process_receipt(message: types.Message, state: FSMContext): photo_id = message.photo[-1].file_id data = await state.get_data()
