from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def build_search_results_keyboard(
    docs: list,
    page: int,
    total: int,
    query: str,
    page_size: int = 5
) -> InlineKeyboardMarkup:
    """
    Builds a clean keyboard for standard search results.
    Only contains download/select buttons and navigation buttons.
    NO reaction (like/dislike/comment) buttons.
    """
    builder = InlineKeyboardBuilder()

    # Add download button for each book on the current page
    for idx, doc in enumerate(docs, 1):
        builder.button(text=f"📥 دانلود شماره {idx}", callback_data=f"dl_{doc.id}")

    # Arrange download buttons: 1 per row (or 2 per row if many)
    builder.adjust(1)

    # Navigation row
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️ صفحه قبلی", callback_data=f"p_{page-1}_{query[:30]}")
        )
    if (page * page_size) < total:
        nav_buttons.append(
            InlineKeyboardButton(text="صفحه بعدی ▶️", callback_data=f"p_{page+1}_{query[:30]}")
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    return builder.as_markup()


def build_adv_search_results_keyboard(
    docs: list,
    field_code: str,
    grade_code: str,
    page: int,
    total: int,
    page_size: int = 5
) -> InlineKeyboardMarkup:
    """
    Builds a clean keyboard for advanced search results (field & grade).
    Only contains download/select buttons, navigation buttons, and back button.
    NO reaction (like/dislike/comment) buttons.
    """
    builder = InlineKeyboardBuilder()

    # Add download button for each book
    for idx, doc in enumerate(docs, 1):
        builder.button(text=f"📥 دانلود شماره {idx}", callback_data=f"dl_{doc.id}")

    builder.adjust(1)

    # Navigation row
    nav = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(text="◀️ قبلی", callback_data=f"adv_res_{field_code}_{grade_code}_{page-1}")
        )
    if (page * page_size) < total:
        nav.append(
            InlineKeyboardButton(text="بعدی ▶️", callback_data=f"adv_res_{field_code}_{grade_code}_{page+1}")
        )

    if nav:
        builder.row(*nav)

    # Back to field selection
    builder.row(
        InlineKeyboardButton(text="🔙 تغییر پایه / رشته", callback_data=f"adv_f_{field_code}")
    )

    return builder.as_markup()
