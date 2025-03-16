from telegram import Update,  ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from test import get_questions_for_test
import json
import re
import os

TOKEN = "7949630541:AAEyGwfyP9xAtBwS9GxQg7lbiT3nxmMwpGM"

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"candidates": []}

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def add_candidate(full_name, email, password, phone):
    data = load_data()
    data["candidates"].append({
        "full_name": full_name,
        "email": email,
        "password": password,
        "phone": phone
    })
    save_data(data)

def authenticate_candidate(email, password):
    data = load_data()
    return any(c["email"] == email and c["password"] == password for c in data["candidates"])

FULL_NAME, EMAIL, PASSWORD, PHONE, AUTH_EMAIL, AUTH_PASSWORD, CHOOSE_POSITION, CHOOSE_TEST_TYPE, CHANGE_ANSWER,  SHOW_HISTORY, ASK_QUESTION, SHOW_RESULTS = range(12)

MAIN_MENU = ReplyKeyboardMarkup([
    ["📝 Регистрация", "🔑 Авторизация"],
    ["📋 Начать тест", "📜 История тестов"],
    ["👤 Профиль"]
], resize_keyboard=True)

POSITION_MENU = ReplyKeyboardMarkup([
    ["Менеджер проектов", "Разработчик Python"],
    ["Назад"]  # Новая кнопка
], resize_keyboard=True)

TEST_TYPE_MENU = ReplyKeyboardMarkup([
    ["📌 Психологический", "🎭 Ситуационный"],
    ["📊 Профессиональный"],
    ["Назад"]  # Новая кнопка
], resize_keyboard=True)

async def start(update: Update, context: CallbackContext):
    welcome_message = (
        "👋 Добро пожаловать в бота для тестирования!\n\n"
        "📌 *Возможности бота:*\n"
        "1. 📝 Регистрация и авторизация.\n"
        "2. 📋 Прохождение тестов по выбранной вакансии.\n"
        "3. 📜 Просмотр истории тестов.\n"
        "4. 👤 Редактирование профиля.\n\n"
        "Выберите действие из меню ниже:"
    )
    await update.message.reply_text(welcome_message, reply_markup=MAIN_MENU, parse_mode="Markdown")

async def register(update: Update, context: CallbackContext):
    await update.message.reply_text("Введите ваше ФИО:")
    return FULL_NAME

async def process_full_name(update: Update, context: CallbackContext):
    context.user_data["full_name"] = update.message.text
    await update.message.reply_text("Введите ваш email:")
    return EMAIL

async def process_email(update: Update, context: CallbackContext):
    email = update.message.text
    if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        await update.message.reply_text("Некорректный email. Попробуйте еще раз:")
        return EMAIL
    context.user_data["email"] = email
    await update.message.reply_text("Введите ваш пароль:")
    return PASSWORD

async def process_password(update: Update, context: CallbackContext):
    password = update.message.text
    if len(password) < 6:
        await update.message.reply_text("Пароль должен содержать не менее 6 символов. Попробуйте еще раз:")
        return PASSWORD

    context.user_data["password"] = password
    await update.message.reply_text("Введите ваш номер телефона:")
    return PHONE

async def process_phone(update: Update, context: CallbackContext):
    phone = update.message.text
    if not re.match(r"^\+?[1-9]\d{1,14}$", phone):  # Проверка на корректность номера телефона
        await update.message.reply_text("Некорректный номер телефона. Попробуйте еще раз:")
        return PHONE

    context.user_data["phone"] = phone

    add_candidate(
        context.user_data["full_name"],
        context.user_data["email"],
        context.user_data["password"],
        context.user_data["phone"]
    )
    await update.message.reply_text("Вы успешно зарегистрированы!", reply_markup=MAIN_MENU)
    return ConversationHandler.END

async def authorize(update: Update, context: CallbackContext):
    await update.message.reply_text("Введите ваш email:")
    return AUTH_EMAIL

async def process_auth_email(update: Update, context: CallbackContext):
    context.user_data["email"] = update.message.text
    await update.message.reply_text("Введите ваш пароль:")
    return AUTH_PASSWORD

async def process_auth_password(update: Update, context: CallbackContext):
    email = context.user_data["email"]
    password = update.message.text

    if authenticate_candidate(email, password):
        await update.message.reply_text("Авторизация успешна!", reply_markup=MAIN_MENU)
    else:
        await update.message.reply_text("Неверный email или пароль. Попробуйте снова.", reply_markup=MAIN_MENU)

    return ConversationHandler.END

EDIT_PROFILE, EDIT_FULL_NAME, EDIT_EMAIL, EDIT_PASSWORD, EDIT_PHONE = range(5)

async def profile(update: Update, context: CallbackContext):
    email = context.user_data.get("email")
    if not email:
        await update.message.reply_text("Вы не авторизованы.", reply_markup=MAIN_MENU)
        return

    data = load_data()
    candidate = next((c for c in data["candidates"] if c["email"] == email), None)
    if not candidate:
        await update.message.reply_text("Пользователь не найден.", reply_markup=MAIN_MENU)
        return

    profile_message = (
        f"👤 *Ваш профиль*\n\n"
        f"📝 ФИО: {candidate['full_name']}\n"
        f"📧 Email: {candidate['email']}\n"
        f"📞 Телефон: {candidate['phone']}\n"
        f"🏆 Пройдено тестов: {len(candidate.get('test_results', []))}\n"
    )
    await update.message.reply_text(profile_message, parse_mode="Markdown")

    # Предложим опции для редактирования и возврата в меню
    edit_options = [["Изменить ФИО", "Изменить email"], ["Изменить пароль", "Изменить телефон"], ["Вернуться в главное меню"]]
    await update.message.reply_text(
        "Что вы хотите сделать?",
        reply_markup=ReplyKeyboardMarkup(edit_options, resize_keyboard=True)
    )
    return EDIT_PROFILE

async def edit_profile_choice(update: Update, context: CallbackContext):
    choice = update.message.text
    if choice == "Вернуться в главное меню":
        await update.message.reply_text("Возврат в главное меню.", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    elif choice == "Изменить ФИО":
        await update.message.reply_text(
            "Введите новое ФИО:",
            reply_markup=ReplyKeyboardMarkup([["Отмена", "Вернуться в главное меню"]], resize_keyboard=True)
        )
        return EDIT_FULL_NAME
    elif choice == "Изменить email":
        await update.message.reply_text(
            "Введите новый email:",
            reply_markup=ReplyKeyboardMarkup([["Отмена", "Вернуться в главное меню"]], resize_keyboard=True)
        )
        return EDIT_EMAIL
    elif choice == "Изменить пароль":
        await update.message.reply_text(
            "Введите новый пароль:",
            reply_markup=ReplyKeyboardMarkup([["Отмена", "Вернуться в главное меню"]], resize_keyboard=True)
        )
        return EDIT_PASSWORD
    elif choice == "Изменить телефон":
        await update.message.reply_text(
            "Введите новый номер телефона:",
            reply_markup=ReplyKeyboardMarkup([["Отмена", "Вернуться в главное меню"]], resize_keyboard=True)
        )
        return EDIT_PHONE
    else:
        await update.message.reply_text("Неверный выбор. Попробуйте снова.")
        return EDIT_PROFILE

async def update_full_name(update: Update, context: CallbackContext):
    if update.message.text == "Отмена":
        await update.message.reply_text("Изменение отменено.", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    elif update.message.text == "Вернуться в главное меню":
        await update.message.reply_text("Возврат в главное меню.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    new_full_name = update.message.text
    email = context.user_data.get("email")
    data = load_data()
    for candidate in data["candidates"]:
        if candidate["email"] == email:
            candidate["full_name"] = new_full_name
            break
    save_data(data)
    await update.message.reply_text("ФИО успешно изменено!", reply_markup=MAIN_MENU)
    return ConversationHandler.END

async def update_email(update: Update, context: CallbackContext):
    if update.message.text == "Отмена":
        await update.message.reply_text("Изменение отменено.", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    elif update.message.text == "Вернуться в главное меню":
        await update.message.reply_text("Возврат в главное меню.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    new_email = update.message.text
    if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", new_email):
        await update.message.reply_text("Некорректный email. Попробуйте еще раз:")
        return EDIT_EMAIL

    email = context.user_data.get("email")
    data = load_data()
    for candidate in data["candidates"]:
        if candidate["email"] == email:
            candidate["email"] = new_email
            break
    save_data(data)
    await update.message.reply_text("Email успешно изменен!", reply_markup=MAIN_MENU)
    return ConversationHandler.END

async def update_password(update: Update, context: CallbackContext):
    if update.message.text == "Отмена":
        await update.message.reply_text("Изменение отменено.", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    elif update.message.text == "Вернуться в главное меню":
        await update.message.reply_text("Возврат в главное меню.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    new_password = update.message.text
    email = context.user_data.get("email")
    data = load_data()
    for candidate in data["candidates"]:
        if candidate["email"] == email:
            candidate["password"] = new_password
            break
    save_data(data)
    await update.message.reply_text("Пароль успешно изменен!", reply_markup=MAIN_MENU)
    return ConversationHandler.END

async def update_phone(update: Update, context: CallbackContext):
    if update.message.text == "Отмена":
        await update.message.reply_text("Изменение отменено.", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    elif update.message.text == "Вернуться в главное меню":
        await update.message.reply_text("Возврат в главное меню.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    new_phone = update.message.text
    email = context.user_data.get("email")
    data = load_data()
    for candidate in data["candidates"]:
        if candidate["email"] == email:
            candidate["phone"] = new_phone
            break
    save_data(data)
    await update.message.reply_text("Номер телефона успешно изменен!", reply_markup=MAIN_MENU)
    return ConversationHandler.END

async def choose_position(update: Update, context: CallbackContext):
    # Проверяем, авторизован ли пользователь
    if "email" not in context.user_data:
        await update.message.reply_text(
            "⚠ Ошибка: Вы не авторизованы. Пожалуйста, авторизуйтесь, чтобы начать тестирование.",
            reply_markup=MAIN_MENU
        )
        return ConversationHandler.END

    # Если пользователь авторизован, продолжаем выбор вакансии
    await update.message.reply_text("Выберите вакансию:", reply_markup=POSITION_MENU)
    return CHOOSE_POSITION

async def process_position_choice(update: Update, context: CallbackContext):
    if update.message.text == "Назад":
        await update.message.reply_text("Возврат в главное меню.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    context.user_data["position"] = update.message.text
    await update.message.reply_text("Выберите тип теста:", reply_markup=TEST_TYPE_MENU)
    return CHOOSE_TEST_TYPE

async def process_test_type(update: Update, context: CallbackContext):
    if update.message.text == "Назад":
        await update.message.reply_text("Выберите вакансию:", reply_markup=POSITION_MENU)
        return CHOOSE_POSITION

    context.user_data["test_type"] = update.message.text
    questions = get_questions_for_test(context.user_data["position"], context.user_data["test_type"])

    if not questions:
        await update.message.reply_text("⚠ Ошибка: Вопросы для этого теста не найдены.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    # Сохраняем вопросы в context.user_data
    context.user_data["questions"] = questions
    context.user_data["current_question"] = 0
    context.user_data["answers"] = []

    return await ask_question(update, context)


async def ask_question(update: Update, context: CallbackContext):
    questions = context.user_data.get("questions", [])
    index = context.user_data.get("current_question", 0)

    if not questions:
        await update.message.reply_text("⚠ Ошибка: вопросы отсутствуют.")
        return ConversationHandler.END

    if index < len(questions):
        question = questions[index]
        keyboard = [[opt] for opt in question["options"]]
        if index > 0:  # Начиная со второго вопроса
            keyboard.append(["Изменить ответ"])

        await update.message.reply_text(
            f"{question['text']}",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        print(f"[DEBUG] Ожидаем ответ на вопрос {index + 1}")
        return ASK_QUESTION
    else:
        print("[DEBUG] Все вопросы завершены.")
        return await show_result(update, context)

async def process_answer(update: Update, context: CallbackContext):
    user_answer = update.message.text
    current_question_index = context.user_data.get("current_question", 0)
    questions = context.user_data.get("questions", [])

    print(f"[DEBUG] Ответ пользователя: {user_answer}")

    if not questions:
        await update.message.reply_text("⚠ Ошибка: вопросы отсутствуют.")
        return ConversationHandler.END

    if user_answer == "Изменить ответ":
        index = current_question_index - 1
        if index >= 0:
            question = questions[index]
            await update.message.reply_text(
                f"Вы хотите изменить свой ответ на вопрос:\n\n{question['text']}\n\nВыберите новый ответ:",
                reply_markup=ReplyKeyboardMarkup([[opt] for opt in question["options"]], resize_keyboard=True)
            )
            context.user_data["changing_answer"] = True
            return CHANGE_ANSWER

    if context.user_data.get("changing_answer", False):
        context.user_data["answers"][-1]["user_answer"] = user_answer
        context.user_data["changing_answer"] = False
    else:
        if current_question_index < len(questions):
            question = questions[current_question_index]
            context.user_data.setdefault("answers", []).append({
                "question_text": question["text"],
                "user_answer": user_answer,
                "correct_answer": question["correct_answer"],
                "is_correct": user_answer == question["correct_answer"]
            })
        else:
            await update.message.reply_text("⚠ Ошибка: некорректный индекс вопроса.")
            return ConversationHandler.END

    context.user_data["current_question"] += 1
    if context.user_data["current_question"] >= len(questions):
        print("[DEBUG] Тест завершен, показываем результат.")
        return await show_result(update, context)

    print(f"[DEBUG] Переход к следующему вопросу ({context.user_data['current_question'] + 1}).")
    return await ask_question(update, context)

def generate_pdf(test_results, file_path):
    font_path = "font/DejaVuSans.ttf"

    pdfmetrics.registerFont(TTFont('DejaVu', font_path))

    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("DejaVu", 16)
    c.drawString(100, height - 40, "Отчет по результатам теста ")

    y_position = height - 80
    c.setFont("DejaVu", 12)
    c.drawString(100, y_position, f"Результаты теста: {test_results['score']} ({test_results['percentage']:.2f}%)")
    y_position -= 20

    for result in test_results['answers']:
        c.drawString(100, y_position, f"Вопрос: {result['question_text']}")
        y_position -= 15
        c.drawString(100, y_position, f"Ваш ответ: {result['user_answer']}")
        y_position -= 15
        c.drawString(100, y_position, f"Правильный ответ: {result['correct_answer']}")
        y_position -= 15
        c.drawString(100, y_position, f"Ответ правильный: {'Да' if result['is_correct'] else 'Нет'}")
        y_position -= 30

    c.save()
    return file_path

def save_test_result(email, position, test_type, score, percentage, answers):
    data = load_data()

    for candidate in data["candidates"]:
        if candidate["email"] == email:
            if "test_results" not in candidate:
                candidate["test_results"] = []

            candidate["test_results"].append({
                "position": position,
                "test_type": test_type,
                "score": score,
                "percentage": percentage,
                "answers": answers
            })
            break

    save_data(data)

RETRY_OR_MENU = range(1)

async def handle_retry_or_menu(update: Update, context: CallbackContext):
    choice = update.message.text
    if choice == "🔄 Пройти тест заново":
        # Проверяем, есть ли вопросы в context.user_data
        if "questions" not in context.user_data or not context.user_data["questions"]:
            # Загружаем вопросы заново
            questions = get_questions_for_test(context.user_data["position"], context.user_data["test_type"])
            if not questions:
                await update.message.reply_text("⚠ Ошибка: Вопросы для этого теста не найдены.", reply_markup=MAIN_MENU)
                return ConversationHandler.END
            context.user_data["questions"] = questions

        # Начинаем тест заново
        context.user_data["current_question"] = 0
        context.user_data["answers"] = []
        return await ask_question(update, context)
    elif choice == "🏠 Вернуться в главное меню":
        await update.message.reply_text("Возврат в главное меню.", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Неверный выбор. Попробуйте снова.", reply_markup=MAIN_MENU)
        return RETRY_OR_MENU

async def show_result(update: Update, context: CallbackContext):
    answers = context.user_data["answers"]
    total_questions = len(context.user_data.get("questions", []))  # Используем общее количество вопросов
    score = sum(1 for answer in answers if answer["is_correct"])

    correct_answers = sum(1 for answer in answers if answer["is_correct"])
    percentage = (correct_answers / total_questions) * 100

    if percentage >= 90:
        result_category = "Высокий"
        emoji = "💯"
    elif percentage >= 75:
        result_category = "Хороший"
        emoji = "🙂"
    elif percentage >= 50:
        result_category = "Средний"
        emoji = "😐"
    elif percentage >= 25:
        result_category = "Низкий"
        emoji = "🙁"
    else:
        result_category = "Очень низкий"
        emoji = "😞"

    result_message = (
        f"🎉 Тест завершен!\n"
        f"🏆 Ваш результат: {score} из {total_questions} ({percentage:.2f}% - {result_category} {emoji})\n\n"
    )
    await update.message.reply_text(result_message)

    email = context.user_data.get("email", "unknown_user")
    save_test_result(
        email=email,
        position=context.user_data["position"],
        test_type=context.user_data["test_type"],
        score=score,
        percentage=percentage,
        answers=answers
    )

    pdf_file_path = "test_result.pdf"
    test_results = {
        'score': score,
        'percentage': percentage,
        'answers': answers
    }
    generate_pdf(test_results, pdf_file_path)

    with open(pdf_file_path, "rb") as pdf_file:
        await update.message.reply_document(
            document=pdf_file,
            caption="Вот ваш отчет по результатам теста:"
        )
    os.remove(pdf_file_path)

    retry_menu = ReplyKeyboardMarkup([
        ["🔄 Пройти тест заново", "🏠 Вернуться в главное меню"]
    ], resize_keyboard=True)
    await update.message.reply_text(
        "Что вы хотите сделать дальше?",
        reply_markup=retry_menu
    )

    # Удаляем только ненужные данные, оставляем вопросы
    context.user_data.pop("current_question", None)
    context.user_data.pop("answers", None)
    context.user_data.pop("changing_answer", None)

    return RETRY_OR_MENU

async def clear_test_history(update: Update, context: CallbackContext):
    email = context.user_data.get("email")
    if not email:
        await update.message.reply_text("Вы не авторизованы.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    data = load_data()
    candidate = next((c for c in data["candidates"] if c["email"] == email), None)

    if not candidate or "test_results" not in candidate:
        await update.message.reply_text("История тестов уже пуста.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    # Очищаем историю тестов
    candidate["test_results"] = []
    save_data(data)

    await update.message.reply_text("🧹 История тестов успешно очищена!", reply_markup=MAIN_MENU)
    return ConversationHandler.END

HISTORY_OPTIONS = range(1)

async def handle_history_options(update: Update, context: CallbackContext):
    choice = update.message.text
    if choice == "🧹 Очистить историю":
        return await clear_test_history(update, context)
    elif choice == "🏠 Вернуться в главное меню":
        await update.message.reply_text("Возврат в главное меню.", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Неверный выбор. Попробуйте снова.", reply_markup=MAIN_MENU)
        return HISTORY_OPTIONS

async def show_test_history(update: Update, context: CallbackContext):
    email = context.user_data.get("email")
    if not email:
        await update.message.reply_text("Вы не авторизованы. Войдите, чтобы посмотреть историю тестов.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    data = load_data()
    candidate = next((c for c in data["candidates"] if c["email"] == email), None)

    if not candidate or "test_results" not in candidate:
        await update.message.reply_text("Вы еще не проходили тесты.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    history_message = "📜 *Ваша история тестов:*\n\n"
    for result in candidate["test_results"]:
        history_message += (
            f"📌 *{result['position']} ({result['test_type']})*\n"
            f"🏆 Результат: {result['score']} баллов ({result['percentage']}%)\n"
            "-------------------------\n"
        )

    history_menu = ReplyKeyboardMarkup([
        ["🧹 Очистить историю", "🏠 Вернуться в главное меню"]
    ], resize_keyboard=True)

    await update.message.reply_text(history_message, reply_markup=history_menu, parse_mode="Markdown")
    return HISTORY_OPTIONS


def main():
    app = Application.builder().token(TOKEN).build()

    registration_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Регистрация$"), register)],
        states={
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_full_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_email)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_password)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_phone)],
        },
        fallbacks=[]
    )
    auth_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔑 Авторизация$"), authorize)],
        states={
            AUTH_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_auth_email)],
            AUTH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_auth_password)],
        },
        fallbacks=[]
    )
    test_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Начать тест$"), choose_position)],
        states={
            CHOOSE_POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_position_choice)],
            CHOOSE_TEST_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_test_type)],
            ASK_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_answer)],
            CHANGE_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_answer)],
            RETRY_OR_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_retry_or_menu)],  # Новое состояние
        },
        fallbacks=[]
    )
    edit_profile_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^👤 Профиль$"), profile)],
        states={
            EDIT_PROFILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_profile_choice)],
            EDIT_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_full_name)],
            EDIT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_email)],
            EDIT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_password)],
            EDIT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_phone)],
        },
        fallbacks=[]
    )

    history_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📜 История тестов$"), show_test_history)],
        states={
            HISTORY_OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_history_options)],
        },
        fallbacks=[]
    )

    app.add_handler(history_handler)
    app.add_handler(edit_profile_handler)
    app.add_handler(MessageHandler(filters.Regex("^👤 Профиль$"), profile))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(registration_handler)
    app.add_handler(auth_handler)
    app.add_handler(test_handler)
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
