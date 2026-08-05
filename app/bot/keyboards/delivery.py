from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def build_file_delivery_keyboard(book_id: int, likes: int, dislikes: int) -> InlineKeyboardMarkup:
    """
    Builds the rating and comments inline keyboard attached beneath a delivered PDF/book file message.
    
    Layout:
    [ 👍 {likes} ] [ 👎 {dislikes} ]
    [ 💬 مشاهده و ثبت نظرات ]
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=f"👍 {likes}", callback_data=f"rate_{book_id}_like")
    builder.button(text=f"👎 {dislikes}", callback_data=f"rate_{book_id}_dislike")
    builder.button(text="💬 مشاهده و ثبت نظرات", callback_data=f"cmts_{book_id}_1")
    builder.adjust(2, 1)
    return builder.as_markup()
