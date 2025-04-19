# -*- coding: utf-8 -*-
import telebot
from telebot import types
import requests
import matplotlib.pyplot as plt
import datetime
from io import BytesIO


# ======= НАСТРОЙКИ =======
BOT_TOKEN = '7796116228:AAH2boc2j5TG50g142P3sfOrcct4yFroDIc'
OPENWEATHER_TOKEN = 'da76567bd6535728aeb65dae2431576d'
XRAS_JSON_URL = 'https://xras.ru/txt/kpm_RAL5.json'
XRAS_FORECAST_URL = 'https://xras.ru/txt/kpf_RAL5.json'

bot = telebot.TeleBot(BOT_TOKEN)
user_diary = {}  # Словарь для хранения записей самочувствия
user_locations = {}  # Словарь для хранения локаций пользователей (для избежания повторных запросов города)
user_editing_state = {}


# ======= КНОПКИ =======
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📈 Магнитные бури', '🌤 Погода')
    markup.add('💡 Рекомендации', '📗 Дневник самочувствия')  # оставлен только пункт Дневник самочувствия
    return markup

# ======= ГРАФИК БУРЬ =======
def get_k_index_from_json():
    try:
        response = requests.get(XRAS_JSON_URL)
        data = response.json()
        entries = data['data'] if 'data' in data else data
        dates = []
        kp_values = []
        for entry in reversed(entries):
            date_obj = datetime.datetime.strptime(entry['time'], '%Y-%m-%d')
            dates.append(date_obj)
            kp_values.append(float(entry['max_kp']))
        return dates, kp_values, entries
    except Exception as e:
        print(f"Ошибка при получении данных Kp: {e}")
        return [], [], []

def get_kp_forecast():
    try:
        response = requests.get(XRAS_FORECAST_URL)
        data = response.json()['data']
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        today_entry = next((d for d in data if d['time'] == today), None)
        tomorrow_entry = next((d for d in data if d['time'] == tomorrow), None)
        return today_entry, tomorrow_entry
    except Exception as e:
        print(f"Ошибка прогноза Kp: {e}")
        return None, None

def format_kp_level(kp):
    kp = float(kp)
    if kp < 4:
        return f"🟢 Низкий"
    elif kp < 6:
        return f"🟠 Умеренный"
    else:
        return f"🔴 Высокий"

def generate_kp_graph():
    dates, kp_values, entries = get_k_index_from_json()
    if not dates:
        return None

    today_date = datetime.datetime.now().strftime('%Y-%m-%d')
    today_kp_entry = next((entry for entry in entries if entry['time'] == today_date), {'max_kp': 0})
    today_kp = float(today_kp_entry['max_kp'])

    plt.figure(figsize=(10, 5))
    bars = plt.bar(dates, kp_values, color=['green' if v < 4 else 'orange' if v < 5 else 'red' for v in kp_values])

    plt.axhline(4, color='orange', linestyle='--', label='Умеренный (Kp=4)')
    plt.axhline(6, color='red', linestyle='--', label='Высокий (Kp=6)')
    plt.title("Прогноз магнитных бурь (Kp индекс)")
    plt.xlabel("Дата")
    plt.ylabel("Kp индекс")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.figtext(0.99, 0.01, f"Уровень магнитной бури (Kp) сегодня: {today_kp}", ha="right", fontsize=10, color="blue")

    image = BytesIO()
    plt.savefig(image, format='png')
    image.seek(0)
    plt.close()
    return image

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Привет! Я бот прогноза магнитных бурь и погоды 🌌\nВыбери интересующий пункт:", reply_markup=main_keyboard())

@bot.message_handler(func=lambda msg: msg.text == '📈 Магнитные бури')
def send_kp_graph(message):
    img = generate_kp_graph()
    if img:
        bot.send_photo(message.chat.id, img, caption="Актуальный график магнитных бурь (Kp индекс)")

        today_entry, tomorrow_entry = get_kp_forecast()
        forecast_text = "\n\n<b>Прогноз магнитных бурь:</b>"
        if today_entry:
            forecast_text += f"\n📅 <b>Сегодня ({today_entry['time']}):</b>\n» Kp: {today_entry['max_kp']} ({format_kp_level(today_entry['max_kp'])})\n» Ap: {today_entry['ap']}\n» F10.7: {today_entry['f10']}"
        if tomorrow_entry:
            forecast_text += f"\n\n📅 <b>Завтра ({tomorrow_entry['time']}):</b>\n» Kp: {tomorrow_entry['max_kp']} ({format_kp_level(tomorrow_entry['max_kp'])})\n» Ap: {tomorrow_entry['ap']}\n» F10.7: {tomorrow_entry['f10']}"

        bot.send_message(message.chat.id, forecast_text, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "Не удалось получить график магнитных бурь")

# ======= ПОГОДА =======
def get_weather_json(city_name):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OPENWEATHER_TOKEN}&units=metric&lang=ru"
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Ошибка погоды: {e}")
        return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Привет! Я бот прогноза магнитных бурь и погоды 🌌\nВыбери интересующий пункт:", reply_markup=main_keyboard())

@bot.message_handler(func=lambda msg: msg.text == '📈 Магнитные бури')
def send_kp_graph(message):
    img = generate_kp_graph()
    if img:
        bot.send_photo(message.chat.id, img, caption="Актуальный график магнитных бурь (Kp индекс)")
    else:
        bot.send_message(message.chat.id, "Не удалось получить график магнитных бурь 😕")

@bot.message_handler(func=lambda msg: msg.text == '🌤 Погода')
def ask_city_weather(message):
    msg = bot.send_message(message.chat.id, "Введи город, чтобы получить погоду 🌍:")
    bot.register_next_step_handler(msg, show_weather)

def show_weather(message):
    city = message.text
    weather = get_weather_json(city)
    if weather and weather.get('main'):
        temp = round(weather['main']['temp'])
        feels_like = round(weather['main']['feels_like'])
        pressure_hpa = weather['main']['pressure']
        pressure_mmhg = round(pressure_hpa * 0.75006)
        humidity = weather['main']['humidity']
        wind_speed = weather['wind']['speed']
        description = weather['weather'][0]['description'].capitalize()
        pop = weather.get('pop', 0) * 100 if 'pop' in weather else 0

        if pressure_mmhg < 100:
            pressure_status = "(пониженное)"
        elif pressure_mmhg > 110:
            pressure_status = "(повышенное)"
        else:
            pressure_status = "(в пределах нормы)"

        user_locations[message.chat.id] = city

        weather_text = (
            f"📍 Город: {city}\n"
            f"🌡 Температура: {temp}°C, {description}\n"
            f"🤔 Ощущается как: {feels_like}°C\n"
            f"💧 Влажность: {humidity}%\n"
            f"🌬 Ветер: {wind_speed} м/с\n"
            f"⁉️ Давление: {pressure_mmhg} мм рт. ст. {pressure_status}\n"
            f"🌦 Осадки: {int(pop)}%\n"
        )

        bot.send_message(message.chat.id, weather_text)
    else:
        bot.send_message(message.chat.id, "Не удалось получить данные о погоде 😞")

@bot.message_handler(func=lambda msg: msg.text == '💡 Рекомендации')
def generate_advice(message):
    city = user_locations.get(message.chat.id)
    if not city:
        msg = bot.send_message(message.chat.id, "Для персональных рекомендаций отправь свой город 🌍:")
        bot.register_next_step_handler(msg, set_city_and_generate_advice)
        return
    send_advice(message, city)

def set_city_and_generate_advice(message):
    city = message.text
    user_locations[message.chat.id] = city
    send_advice(message, city)

def send_advice(message, city):
    weather_info = get_weather_json(city)
    _, _, entries = get_k_index_from_json()

    if not weather_info or not entries:
        bot.send_message(message.chat.id, "Ошибка при получении данных 😕")
        return

    pressure_hpa = weather_info['main']['pressure']
    pressure_mmhg = round(pressure_hpa * 0.75006)
    temp = round(weather_info['main']['temp'])
    description = weather_info['weather'][0]['description'].lower()

    today_date = datetime.datetime.now().strftime('%Y-%m-%d')
    today_kp_entry = next((entry for entry in entries if entry['time'] == today_date), {'max_kp': 0})
    kp = float(today_kp_entry['max_kp'])

    if kp < 4:
        kp_text = "Магнитная активность низкая, день обещает быть спокойным."
        kp_risk = 0
    elif kp < 6:
        kp_text = "Магнитная активность умеренная. У чувствительных людей возможен дискомфорт."
        kp_risk = 1
    elif kp < 7:
        kp_text = "Магнитная буря средней силы. Могут наблюдаться лёгкие недомогания."
        kp_risk = 2
    else:
        kp_text = "Сильная магнитная буря. Рекомендуется снизить активность и отдохнуть."
        kp_risk = 3

    if pressure_mmhg < 740:
        pressure_text = "Пониженное давление. Возможна вялость или головная боль. Старайтесь больше отдыхать."
        pressure_risk = 1
    elif pressure_mmhg > 760:
        pressure_text = "Повышенное давление. Избегайте чрезмерных нагрузок."
        pressure_risk = 1
    else:
        pressure_text = "Давление в пределах нормы."
        pressure_risk = 0

    bad_weather = any(word in description for word in ['дождь', 'пасмурно', 'облачно', 'гроза', 'туман'])
    if bad_weather:
        weather_text = f"На улице {description}. Это может повлиять на уровень энергии."
        weather_risk = 1
    else:
        weather_text = f"На улице {description}. Погода благоприятна для прогулок."
        weather_risk = 0

    total_risk = kp_risk + pressure_risk + weather_risk

    if total_risk == 0:
        final_advice = "Сегодня отличный день! Подходит для активностей и хорошего настроения."
    elif total_risk == 1:
        final_advice = "Небольшой дискомфорт возможен. Слушайте своё тело и отдыхайте при необходимости."
    elif total_risk == 2:
        final_advice = "Будьте внимательны к самочувствию. Избегайте перегрузок и больше отдыхайте."
    else:
        final_advice = "Советуем снизить уровень активности, избегать стрессов и прислушиваться к себе."

    response = (
        f"📍 Локация: {city}\n\n"
        f"{kp_text}\n"
        f"{pressure_text}\n"
        f"{weather_text}\n\n"
        f"🔎 {final_advice}"
    )

    bot.send_message(message.chat.id, response)


# Команда для открытия дневника самочувствия
@bot.message_handler(func=lambda msg: msg.text == '📗 Дневник самочувствия')
def diary(message):
    bot.send_message(message.chat.id, "Что вы хотите сделать?", reply_markup=diary_keyboard())

# Клавиатура для работы с дневником
def diary_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('➕ Добавить запись', '📖 Просмотр дневника')
    markup.row('✏ Редактировать запись', '🗑 Удалить запись')
    markup.row('🧹 Очистить весь дневник', '⬅️ Назад в меню')
    return markup

# Добавление записи
@bot.message_handler(func=lambda msg: msg.text == '➕ Добавить запись')
def ask_feeling(message):
    bot.send_message(message.chat.id, "Как вы себя чувствуете?")
    bot.register_next_step_handler(message, save_feeling)

def save_feeling(message):
    user_id = message.chat.id
    feeling_text = message.text.strip()
    if len(feeling_text) > 50:
        bot.send_message(message.chat.id, "Запись не может превышать 50 символов. Попробуйте снова.")
        bot.register_next_step_handler(message, save_feeling)
        return
    now = datetime.datetime.now()
    record = {
        "number": len(user_diary.get(user_id, [])) + 1,
        "date": now.strftime("%Y-%m-%d %H:%M"),
        "feeling": feeling_text
    }
    user_diary.setdefault(user_id, []).append(record)
    bot.send_message(message.chat.id, "Запись добавлена!", reply_markup=diary_keyboard())

# Просмотр дневника
@bot.message_handler(func=lambda msg: msg.text == '📖 Просмотр дневника')
def show_diary(message):
    user_id = message.chat.id
    if user_id in user_diary and user_diary[user_id]:
        diary_text = "История вашего самочувствия:\n"
        for idx, record in enumerate(reversed(user_diary[user_id]), start=1):
            diary_text += f"id {record['number']} | Дата: {record['date']} | Чувство: {record['feeling']}\n"
        bot.send_message(message.chat.id, diary_text)
    else:
        bot.send_message(message.chat.id, "У вас нет записей в дневнике самочувствия.")

# Редактирование записи
@bot.message_handler(func=lambda msg: msg.text == '✏ Редактировать запись')
def edit_feeling(message):
    user_id = message.chat.id
    if user_id in user_diary and user_diary[user_id]:
        # Запрашиваем номер записи для редактирования
        bot.send_message(message.chat.id, "Введите id записи для редактирования (id записи указан дневнике 👉 📖 Просмотр дневника):")
        bot.register_next_step_handler(message, ask_new_text)

def ask_new_text(message):
    user_id = message.chat.id
    try:
        # Сохраняем номер записи для редактирования
        record_number = int(message.text.strip())
        user_editing_state[user_id] = record_number
        bot.send_message(user_id, "Как вы себя чувствуете? (до 50 символов):")
        bot.register_next_step_handler(message, save_edited_entry)
    except ValueError:
        bot.send_message(user_id, "Ошибка. Введите корректный id записи.")
        bot.register_next_step_handler(message, ask_new_text)

def save_edited_entry(message):
    user_id = message.chat.id
    try:
        # Новый текст записи
        new_text = message.text.strip()
        if len(new_text) > 50:
            bot.send_message(user_id, "Текст слишком длинный. Попробуйте снова.")
            bot.register_next_step_handler(message, save_edited_entry)
            return

        # Получаем номер редактируемой записи
        record_number = user_editing_state.get(user_id)
        if not record_number:
            bot.send_message(user_id, "Не найден id записи для редактирования.")
            return

        # Обновляем текст записи
        for record in user_diary[user_id]:
            if record['number'] == record_number:
                record['feeling'] = new_text
                record['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                break

        # Отправляем сообщение об успешном редактировании
        bot.send_message(user_id, "Запись обновлена.", reply_markup=diary_keyboard())
    except Exception as e:
        bot.send_message(user_id, f"Ошибка при редактировании: {e}", reply_markup=diary_keyboard())

# Удаление записи
@bot.message_handler(func=lambda msg: msg.text == '🗑 Удалить запись')
def delete_feeling(message):
    user_id = message.chat.id
    if user_id in user_diary and user_diary[user_id]:
        # Запрашиваем номер записи для удаления
        bot.send_message(message.chat.id, "Введите id записи для удаления:")
        bot.register_next_step_handler(message, choose_delete_record)
    else:
        bot.send_message(message.chat.id, "У вас нет записей для удаления.")

def choose_delete_record(message):
    user_id = message.chat.id
    try:
        record_number = int(message.text.strip())
        if user_id in user_diary and len(user_diary[user_id]) >= record_number > 0:
            deleted_record = user_diary[user_id].pop(record_number - 1)
            bot.send_message(message.chat.id, f"Запись c id {record_number} была удалена!")
        else:
            raise ValueError("Запись с таким id не существует.")
    except ValueError as e:
        bot.send_message(message.chat.id, str(e) + "\nПопробуйте снова.")
        bot.register_next_step_handler(message, choose_delete_record)

# Очистить весь дневник
@bot.message_handler(func=lambda msg: msg.text == '🧹 Очистить весь дневник')
def clear_diary(message):
    user_id = message.chat.id
    if user_id in user_diary:
        user_diary[user_id] = []  # Очищаем дневник пользователя
        bot.send_message(message.chat.id, "Ваш дневник очищен!", reply_markup=diary_keyboard())
    else:
        bot.send_message(message.chat.id, "У вас нет записей для очистки.", reply_markup=diary_keyboard())

# Назад в меню
@bot.message_handler(func=lambda msg: msg.text == '⬅️ Назад в меню')
def go_back(message):
    bot.send_message(message.chat.id, "Вы вернулись в главное меню:", reply_markup=main_keyboard())





if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
