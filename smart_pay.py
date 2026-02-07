import flet as ft
import datetime
import json
import os
from plyer import notification

# --- БЛОК ПАМЯТИ ---
DATA_FILE = "smart_pay.json"
FREE_LIMIT = 2

def load_payments():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_payments(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

# Инициализируем хранилище
payments = load_payments()

def main(page: ft.Page):
    page.title = "Smart Pay"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.window_height = 800
    page.padding = 20

    # Глобальная переменная для отслеживания редактирования
    edit_index = [-1] 

    # --- ЛОГИКА УВЕДОМЛЕНИЙ ---
    def check_notifications():
        overdue_count = 0
        soon_count = 0
        for p in payments:
            # Пропускаем оплаченные платежи
            if p.get('paid', False):
                continue
                
            try:
                due_date = datetime.datetime.strptime(p['date'], "%Y-%m-%d").date()
                today = datetime.date.today()
                delta = (due_date - today).days
                if delta < 0: overdue_count += 1
                elif 0 <= delta <= 3: soon_count += 1
            except: continue

        if overdue_count > 0:
            try:
                notification.notify(
                    title='SMART PAY: Внимание!',
                    message=f'Есть просроченные платежи ({overdue_count}). Проверьте список.',
                    app_name='Smart Pay', timeout=10
                )
            except: pass
        elif soon_count > 0:
            try:
                notification.notify(
                    title='SMART PAY: Напоминание',
                    message=f'Скоро срок оплаты у {soon_count} счетов.',
                    app_name='Smart Pay', timeout=10
                )
            except: pass

    # --- ЛОГИКА СТАТУСОВ ---
    def get_status_info(payment_dict):
        # Если оплачено - показываем зеленую галочку
        if payment_dict.get('paid', False):
            return ft.Colors.GREEN_600, "ОПЛАЧЕНО", ft.Icons.CHECK_CIRCLE
            
        try:
            due_date = datetime.datetime.strptime(payment_dict['date'], "%Y-%m-%d").date()
            today = datetime.date.today()
            delta = (due_date - today).days

            if delta < 0:
                return ft.Colors.RED_400, f"ПРОСРОЧЕНО ({abs(delta)} дн)", ft.Icons.REPORT_GMAILERRORRED
            elif delta == 0:
                return ft.Colors.ORANGE_400, "СЕГОДНЯ", ft.Icons.WARNING_AMBER
            elif 0 < delta <= 3:
                return ft.Colors.YELLOW_400, f"СКОРО ({delta} дн)", ft.Icons.ACCESS_TIME
            else:
                return ft.Colors.GREEN_400, f"ОК (через {delta} дн)", ft.Icons.CHECK_CIRCLE
        except:
            return ft.Colors.GREY_500, "Ошибка даты", ft.Icons.ERROR_OUTLINE

    # --- UI: СПИСОК ПЛАТЕЖЕЙ ---
    payments_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

    # Функции удаления, редактирования и пометки оплаченным
    def mark_paid(e):
        index = e.control.data
        payments[index]['paid'] = True
        save_payments(payments)
        refresh_list()
        
        # Показываем уведомление
        snack = ft.SnackBar(ft.Text("Платёж помечен как оплаченный!"))
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def delete_item(e):
        index = e.control.data
        del payments[index]
        save_payments(payments)
        refresh_list()
        
        # Показываем уведомление об удалении
        snack = ft.SnackBar(ft.Text("Платёж удалён!"))
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def edit_item(e):
        index = e.control.data
        item = payments[index]
        
        # Заполняем поля данными
        name_input.value = item['title']
        sum_input.value = item['amount']
        
        # Устанавливаем дату
        try:
            date_obj = datetime.datetime.strptime(item['date'], "%Y-%m-%d")
            date_picker.value = date_obj
            date_button_text.value = item['date']
        except:
            pass

        # Устанавливаем режим редактирования
        edit_index[0] = index
        add_dialog.title = ft.Text("Редактировать платёж")
        
        # Открываем диалог
        add_dialog.open = True
        page.update()

    def refresh_list():
        payments_list.controls.clear()
        if not payments:
            payments_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, size=60, color=ft.Colors.GREY_700),
                        ft.Container(height=10),
                        ft.Text("Добавь первый платёж —\nи забудь про просрочки", 
                               text_align="center", size=16, color=ft.Colors.GREY_500),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.Padding(top=100, left=0, right=0, bottom=0)
                )
            )
        else:
            # Сортировка: сначала неоплаченные по дате, потом оплаченные
            def sort_key(item_tuple):
                p = item_tuple[1]
                # Оплаченные в конец списка
                if p.get('paid', False):
                    return (1, 999999)  # Большое число для сортировки в конец
                    
                try:
                    due = datetime.datetime.strptime(p['date'], "%Y-%m-%d").date()
                    return (0, (due - datetime.date.today()).days)
                except: 
                    return (0, 0)

            # Создаем список с индексами
            indexed_payments = list(enumerate(payments))
            sorted_payments = sorted(indexed_payments, key=sort_key)

            for original_index, p in sorted_payments:
                color, status_text, icon = get_status_info(p)
                
                try:
                    amount_int = int(p['amount'])
                    amount_str = "{:,}".format(amount_int).replace(",", " ")
                except:
                    amount_str = p['amount']

                # Определяем, оплачен ли платеж
                is_paid = p.get('paid', False)

                # Карточка платежа с кнопками
                card_content = ft.Container(
                    content=ft.Column([
                        # Верхняя часть: Иконка, Текст, Сумма
                        ft.Row([
                            ft.Row([
                                ft.Icon(icon, color=color, size=30),
                                ft.Column([
                                    ft.Text(
                                        p['title'], 
                                        size=16, 
                                        weight="bold",
                                        # Зачеркнутый текст если оплачено
                                        style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if is_paid else None
                                    ),
                                    ft.Text(status_text, size=12, color=color),
                                ], spacing=2),
                            ]),
                            ft.Text(f"{amount_str} ₸", size=16, weight="bold"),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        
                        # Нижняя часть: Кнопки действий
                        ft.Container(height=5),
                        ft.Row([
                            # Кнопка "Оплачено" - показываем только если НЕ оплачено
                            ft.IconButton(
                                icon=ft.Icons.CHECK_CIRCLE_OUTLINE, 
                                icon_color=ft.Colors.GREEN_400, 
                                icon_size=20,
                                tooltip="Оплачено",
                                data=original_index,
                                on_click=mark_paid,
                                visible=not is_paid  # Скрываем если уже оплачено
                            ) if not is_paid else ft.Container(width=0),
                            ft.IconButton(
                                icon=ft.Icons.EDIT, 
                                icon_color=ft.Colors.BLUE_400, 
                                icon_size=20,
                                tooltip="Редактировать",
                                data=original_index,
                                on_click=edit_item
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE, 
                                icon_color=ft.Colors.RED_400, 
                                icon_size=20,
                                tooltip="Удалить",
                                data=original_index,
                                on_click=delete_item
                            ),
                        ], alignment=ft.MainAxisAlignment.END)
                    ]),
                    padding=15,
                    bgcolor=ft.Colors.GREY_900,
                    border_radius=12,
                    border=ft.Border.all(1, ft.Colors.GREY_800),
                    # Немного прозрачнее если оплачено
                    opacity=0.6 if is_paid else 1.0
                )
                payments_list.controls.append(card_content)
        page.update()

    # --- ФОРМА ДОБАВЛЕНИЯ ---
    name_input = ft.TextField(label="Название (Кредит, Налог...)", autofocus=True)
    sum_input = ft.TextField(label="Сумма", keyboard_type=ft.KeyboardType.NUMBER)
    date_button_text = ft.Text("Выбрать дату")
    date_error_text = ft.Text("", color=ft.Colors.RED_400, size=12)

    def update_date_text(e):
        if date_picker.value:
            date_button_text.value = date_picker.value.strftime("%Y-%m-%d")
            date_error_text.value = "" 
            page.update()

    date_picker = ft.DatePicker(
        first_date=datetime.datetime(2024, 1, 1),
        on_change=update_date_text,
    )
    page.overlay.append(date_picker)
    
    def open_date_picker(e):
        date_picker.open = True
        page.update()

    def save_payment_action(e):
        # Валидация
        name_input.error_text = None
        sum_input.error_text = None
        date_error_text.value = ""
        has_error = False
        
        if not name_input.value or name_input.value.strip() == "":
            name_input.error_text = "Введите название"
            has_error = True
        if not sum_input.value or sum_input.value.strip() == "":
            sum_input.error_text = "Введите сумму"
            has_error = True
        if not date_picker.value and edit_index[0] == -1: 
             if date_button_text.value == "Выбрать дату":
                 date_error_text.value = "Нужно выбрать дату"
                 has_error = True
        
        if has_error:
            page.update()
            return
        
        payment_data = {
            "title": name_input.value.strip(),
            "amount": sum_input.value.strip(),
            "date": date_button_text.value,
            "paid": False  # По умолчанию не оплачено
        }

        if edit_index[0] == -1:
            # ДОБАВЛЕНИЕ НОВОГО
            payments.append(payment_data)
        else:
            # РЕДАКТИРОВАНИЕ СУЩЕСТВУЮЩЕГО
            # Сохраняем статус оплаты
            payment_data['paid'] = payments[edit_index[0]].get('paid', False)
            payments[edit_index[0]] = payment_data
            edit_index[0] = -1

        save_payments(payments)
        
        # Очистка
        name_input.value = ""
        sum_input.value = ""
        date_button_text.value = "Выбрать дату"
        date_picker.value = None
        
        add_dialog.open = False
        page.update()
        refresh_list()
        check_notifications()

    def close_dialog(e):
        edit_index[0] = -1
        name_input.error_text = None
        sum_input.error_text = None
        date_error_text.value = ""
        add_dialog.open = False
        page.update()

    # --- PAYWALL ---
    def close_paywall(e):
        paywall_dialog.open = False
        page.update()

    paywall_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Лимит бесплатной версии", color=ft.Colors.ORANGE_400, weight="bold"),
        content=ft.Column([
            ft.Icon(ft.Icons.LOCK_OPEN, size=60, color=ft.Colors.ORANGE_400),
            ft.Text("Бесплатно — до 2 платежей", text_align="center", size=16, weight="bold"),
            ft.Text("Для большего количества\nоткрой PRO версию.", text_align="center", color=ft.Colors.GREY_400),
            ft.Container(height=10),
            ft.Text("Цена: 2990 ₸ (Навсегда)", size=16, weight="bold", color=ft.Colors.GREEN_400),
        ], tight=True, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        actions=[
            ft.TextButton("Позже", on_click=close_paywall),
            ft.Button("ОТКРЫТЬ PRO", bgcolor=ft.Colors.GREEN_600, color="white", on_click=lambda _: print("КЛИК ПО КУПИТЬ!")),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER
    )
    page.overlay.append(paywall_dialog)

    # --- ОТКРЫТИЕ ДИАЛОГА ---
    def open_add_dialog(e):
        if edit_index[0] == -1 and len(payments) >= FREE_LIMIT:
            paywall_dialog.open = True
            page.update()
        else:
            edit_index[0] = -1
            add_dialog.title = ft.Text("Новый платёж")
            name_input.value = ""
            sum_input.value = ""
            date_button_text.value = "Выбрать дату"
            
            name_input.error_text = None
            sum_input.error_text = None
            date_error_text.value = ""
            add_dialog.open = True
            page.update()

    add_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Новый платёж"),
        content=ft.Column([
            name_input,
            sum_input,
            ft.Row([
                ft.Icon(ft.Icons.CALENDAR_MONTH, color=ft.Colors.BLUE_400, size=20),
                date_button_text,
            ], spacing=10),
            date_error_text,
            ft.Button(
                "Открыть календарь",
                icon=ft.Icons.CALENDAR_MONTH,
                on_click=open_date_picker
            ),
        ], tight=True, spacing=15),
        actions=[
            ft.TextButton("Отмена", on_click=close_dialog),
            ft.Button("Сохранить", on_click=save_payment_action, bgcolor=ft.Colors.BLUE_700, color="white"),
        ],
    )

    page.overlay.append(add_dialog)

    # --- ГЛАВНЫЙ ЭКРАН ---
    page.add(
        ft.Column([
            ft.Text("SMART PAY", size=32, weight="bold", color=ft.Colors.BLUE_200),
            ft.Text("Не забывай про важные платежи", size=16, color=ft.Colors.GREY_500),
        ], spacing=0),
        ft.Divider(height=20, color="transparent"),
        payments_list
    )

    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        bgcolor=ft.Colors.BLUE_700,
        on_click=open_add_dialog
    )

    refresh_list()
    check_notifications()

ft.run(main)