import asyncio 
import logging 
from aiogram import Bot, Dispatcher, F, Router, types 
from aiogram.filters import CommandStart 
from aiogram.fsm.context import FSMContext 
from aiogram.fsm.state import State, StatesGroup 
from aiogram.fsm.storage.memory import MemoryStorage 
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
# КОНФИГУРАЦИЯ (Ваши данные)
BOT_TOKEN = "8952006747:AAGgeoyeL7N2JpmYDha2SqoJglPwbdleJ8Y" 
ADMIN_ID = 5897493181 
CARD_NUMBER = "4441111067937569" 
CARD_HOLDER = "Діана С."
# Текст правил
RULES_TEXT = ( "📌 Правила сервиса:\n\n" "1. Время ожидания: После создания заявки продавец должен принять её в течение 10 минут.\n" "2. Безопасность: Если сделка не принята вовремя, она автоматически аннулируется.\n" "3. Оплата: Переводите точную сумму на указанную карту Монобанка.\n" "4. Подтверждение: После оплаты обязательно отправьте чек или скриншот администратору.\n\n" "Желаем приятных покупок!" )
# SM СОСТОЯНИЯ
class OrderState(StatesGroup): 
    waiting_for_stars = State() 
    waiting_for_username = State() 
    waiting_for_acceptance = State() 
    waiting_for_receipt = State() 
    waiting_for_admin_proof = State() 
    waiting_for_review = State()
# Словарь для отслеживания активных заявок {user_id -> order_status}
active_orders = {}
router = Router() 
storage = MemoryStorage() 
bot = Bot(token=BOT_TOKEN) 
dp = Dispatcher(storage=storage) 
dp.include_router(router)
# ХЕНДЛЕРЫ
@router.message(CommandStart()) 
async def cmd_start(message: types.Message, state: FSMContext): 
    await state.clear() 
    text = ( 
        "⭐ Добро пожаловать в официальный бот по продаже Telegram Stars за гривны!\n\n" 
        "Здесь вы можете быстро и безопасно купить Звезды для вашего аккаунта или канала.\n\n" 
        "Нажмите кнопку ниже, чтобы начать покупку:" 
    ) 
    kb = InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="⭐ Купить Stars", callback_data="buy_stars")], 
        [InlineKeyboardButton(text="📌 Правила", callback_data="show_rules")] 
    ]) 
    await message.answer(text, reply_markup=kb)
@router.callback_query(F.data == "show_rules") 
async def show_rules_handler(call: types.CallbackQuery): 
    kb = InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_start")] 
    ]) 
    await call.message.edit_text(RULES_TEXT, reply_markup=kb) 
    await call.answer()
@router.callback_query(F.data == "back_to_start") 
async def back_to_start_handler(call: types.CallbackQuery, state: FSMContext): 
    await state.clear() 
    text = ( 
        "⭐ Добро пожаловать в официальный бот по продаже Telegram Stars за гривны!\n\n" 
        "Нажмите кнопку ниже, чтобы начать покупку:" 
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="⭐ Купить Stars", callback_data="buy_stars")], 
        [InlineKeyboardButton(text="📌 Правила", callback_data="show_rules")] 
    ]) 
    await call.message.edit_text(text, reply_markup=kb) 
    await call.answer()
@router.callback_query(F.data == "buy_stars") 
async def ask_stars_count(call: types.CallbackQuery, state: FSMContext): 
    await state.set_state(OrderState.waiting_for_stars) 
    await call.message.answer("Введите количество Stars, которое хотите купить (минимум 50):") 
    await call.answer()
@router.message(OrderState.waiting_for_stars) 
async def process_stars_count(message: types.Message, state: FSMContext): 
    if not message.text or not message.text.isdigit(): 
        await message.answer("❌ Пожалуйста, введите число (например, 50):") 
        return
stars = int(message.text)
    if stars < 50:
        await message.answer("⚠️ Минимальный заказ – 50 Stars. Введите другое количество:")
        return

await state.update_data(stars=stars)
rate = 0.75  # 1 stars = 0.75 UAH
total = stars * rate

await state.update_data(total=total)
await state.set_state(OrderState.waiting_for_username)

text = (
    f"🛒 Ваш заказ: {stars} Stars\n"
    f"💵 К оплате: {total:.2f} грн\n\n"
    "Введите ваш юзернейм в Telegram (например, @username), на который нужно зачислить звезды:"
)
await message.answer(text)
@router.message(OrderState.waiting_for_username) 
async def process_username(message: types.Message, state: FSMContext): 
    username = message.text.strip() 
    if not username.startswith("@"): 
        await message.answer("❌ Юзернейм должен начинаться с символа @. Попробуйте снова:") 
        return
await state.update_data(username=username)
data = await state.get_data()
stars = data["stars"]
total = data["total"]

user_id = message.from_user.id
active_orders[user_id] = "waiting_acceptance"

# Уведомление администратору
admin_text = (
    "🔔 **Новая заявка на покупку Stars!**\n\n"
    f"👤 Покупатель: @{message.from_user.username or 'нет'} (ID: {user_id})\n"
    f"🎯 Получатель: {username}\n"
    f"⭐ Количество: {stars} Stars\n"
    f"💵 Сумма к оплате: {total:.2f} грн\n\n"
    "Ожидайте подтверждения продавца."
)

kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✅ Принять заявку", callback_data=f"accept_{user_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
    ]
])

try:
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb)
except Exception as e:
    logging.error(f"Не удалось отправить уведомление админу: {e}")

await state.set_state(OrderState.waiting_for_acceptance)
await message.answer(
    "⏳ Заявка успешно создана и отправлена администратору!\n\n"
    "Пожалуйста, ожидайте, пока продавец подтвердит заказ (обычно это занимает до 10 минут). "
    "Как только заявка будет принята, вам придут реквизиты для оплаты."
)
@router.callback_query(F.data.startswith("accept_")) 
async def admin_accept_order(call: types.CallbackQuery): 
    if call.from_user.id != ADMIN_ID: 
    await call.answer("У вас нет прав!", show_alert=True) 
    return
user_id = int(call.data.split("_")[1])
active_orders[user_id] = "waiting_payment"

await call.message.edit_text(call.message.text + "\n\n✅ **Заявка принята продавцом.**")
await call.answer("Заявка принята!")

payment_text = (
    "💳 **Заявка принята! Реквизиты для оплаты:**\n\n"
    f"Банк: Монобанк\n"
    f"Получатель: {CARD_HOLDER}\n"
    f"Карта: `{CARD_NUMBER}`\n\n"
    "⚠️ **Важно:** Переведите точную сумму в течение 10 минут, после чего отправьте в этот чат скриншот или чек об оплате."
)

try:
    await bot.send_message(user_id, payment_text, parse_mode="Markdown")
except Exception as e:
    logging.error(f"Не удалось отправить реквизиты пользователю {user_id}: {e}")
@router.callback_query(F.data.startswith("reject_")) 
async def admin_reject_order(call: types.CallbackQuery): 
    if call.from_user.id != ADMIN_ID: 
    await call.answer("У вас нет прав!", show_alert=True) 
    return
user_id = int(call.data.split("_")[1])
active_orders.pop(user_id, None)

await call.message.edit_text(call.message.text + "\n\n❌ **Заявка отклонена.**")
await call.answer("Заявка отклонена.")

try:
    await bot.send_message(user_id, "❌ К сожалению, ваша заявка была отклонена продавцом. Вы можете создать новую через /start.")
except Exception as e:
    logging.error(f"Не удалось отправить уведомление об отмене пользователю {user_id}: {e}")
@router.message(OrderState.waiting_acceptance) 
async def waiting_payment_reminder(message: types.Message): 
    await message.answer("⏳ Ваша заявка находится на рассмотрении у продавца. Пожалуйста, ожидайте.")
# ЗАПУСК БОТА
async def main(): 
    logging.basicConfig(level=logging.INFO) 
    print("Бот успешно запущен!") 
    await dp.start_polling(bot)
    if __name__ == "__main__": 
    asyncio.run(main())
