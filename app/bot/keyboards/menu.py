from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu_markup():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎯 جستجوی پیشرفته (رشته و پایه)", callback_data="menu_adv_search")
    builder.button(text="🔍 راهنمای جستجوی کتاب", callback_data="menu_search")
    builder.button(text="📊 درصدگیر آزمون (با نمره منفی)", callback_data="menu_calc")
    builder.button(text="💡 انتقادات و پیشنهادات", callback_data="menu_feedback")
    builder.button(text="⚡ آموزش جستجوی اینلاین (@)", callback_data="menu_inline")
    builder.button(text="ℹ️ راهنمای استفاده و کپشن‌نویسی", callback_data="menu_help")
    builder.adjust(1, 2, 2, 1)
    return builder.as_markup()
