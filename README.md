# Telegram Educational Archive Bot (100% Free & Local Edition)

A high-performance Telegram Bot for instant searching and downloading educational documents, books, and exam papers.

---

## ⚡ Zero Cost Features

- **100% Free & Local**: Runs locally on a normal Windows PC using Python only.
- **No Paid Infrastructure**: No PostgreSQL, No Redis, No Docker, No paid cloud hosting required.
- **SQLite Database (`archive.db`)**: Ultra-fast embedded SQL database with indexing and JSON support.
- **Telegram Channel Storage**: Unlimited file hosting using Telegram Channel as storage engine.
- **Instant Search**: Millisecond search queries with tokenization & Persian normalization.
- **Automated Channel Indexing**: Auto-indexes documents & captions posted/updated in the channel.
- **Admin Statistics**: Real-time stats command (`/stats`) for document counts, active users, and trending searches.

---

## 🚀 Quick Setup Instructions (Windows PC)

### Method 1: Standard Direct Install (Recommended)

Run `pip` using the exact `python` executable to avoid Windows PATH mismatches:

```cmd
python -m pip install -r requirements.txt
```

Then start the bot:

```cmd
python -m app.main
```

---

### Method 2: Virtual Environment (Clean & Isolated)

If Windows has multiple Python versions installed, create a virtual environment:

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

---

## 🔧 Troubleshooting: `ModuleNotFoundError: No module named 'aiogram'`

If you get this error on Windows CMD:
1. It means `pip` and `python` are pointing to different Python versions on your Windows PATH.
2. Always run `python -m pip install aiogram` or `python -m pip install -r requirements.txt` so pip installs packages into the exact Python environment running your app.

---

## 📝 راهنمای فرمت ارسال فایل‌ها و کپشن‌نویسی در کانال مخزن

برای اینکه ربات فایل‌ها را دقیق‌ترین شکل ممکن ایندکس و جستجو کند، می‌توانید کپشن فایل‌ها را به یکی از روش‌های زیر بنویسید:

### روش ۱: استفاده از علامت مثبت `+` (پیشنهادی و سریع)
کلمات کلیدی را بین علامت‌های `+` قرار دهید:
```text
+حسابان+ +خیلی سبز+ +دوازدهم+ +تست+ +جامع+
```

### روش ۲: فرمت کلید و مقدار
```text
عنوان: حسابان جامع خیلی سبز
ناشر: خیلی سبز
پایه: دوازدهم
درس: حسابان
مولف: عباس پور
```

### روش ۳: کپشن معمولی (متن آزاد)
حتی اگر فقط یک متن ساده به عنوان کپشن بنویسید، ربات خط اول را به عنوان عنوان و تمام متن را جهت جستجو دیتابیس پردازش می‌کند!

---

## ⚡ امکانات ویژه نسخه جدید

- **🚀 اجرای کاملاً تمیز و بدون اسپم**: فوروارد خودکار فایل‌ها در زمان استارت حذف شد و ربات بدون ارسال فایل اضافی اجرا می‌شود.
- **⚡ جستجوی اینلاین (@Akonkoribot)**: امکان جستجوی سریع کتاب در هر چت یا گروهی با تایپ `@Akonkoribot نام کتاب`.
- **📊 درصدگیر هوشمند آزمون (با قانون ۱/۳ نمره منفی)**: محاسبه درصد دقیق با دستور `/calc 15 3 20` یا ارسال سه عدد.
- **📱 منوی شیشه‌ای و دکمه‌های راهنما**: ثبت خودکار دستورات تلگرام (`/start`, `/search`, `/calc`, `/help`).
- **🔄 به‌روزرسانی آنی ویرایش‌ها**: همگام‌سازی لحظه‌ای ویرایش کپشن‌ها در کانال.
- **🆔 امضای اختصاصی جدید**: `🆔 @Akonkoribot - @STrekker`


---

## 🌐 راهنمای استقرار و میزبانی رایگان ۲۴ ساعته (بدون نیاز به روشن بودن کامپیوتر)

برای میزبانی همیشگی و رایگان ۲۴ ساعته، پلتفرم‌های **Koyeb** و **Fly.io** عالی‌ترین گزینه‌ها هستند (نیازی به پروکسی ندارند و سرورهای خارجی تلگرام را بدون قطعی پشتیبانی می‌کنند).

---

### 1️⃣ آموزش کامل استقرار روی Koyeb (رایگان، بسیار ساده و سریع)

سرویس **Koyeb** یکی از بهترین پلتفرم‌های ابری رایگان برای اجرای پایتون و ربات تلگرام است.

1. **آپلود پروژه در GitHub:**
   - کدهای ربات را در یک ریپوزیتوری عمومی یا خصوصی در **GitHub** آپلود کنید.
2. **ثبت نام در Koyeb:**
   - وارد سایت [Koyeb.com](https://www.koyeb.com) شوید و با اکانت گیت‌هاب خود لاگین کنید.
3. **ایجاد سرویس جدید:**
   - روی دکمه **Create App** یا **Deploy** کلیک کنید.
   - گزینه **GitHub** را به عنوان Source انتخاب کنید و ریپوزیتوری پروژه خود را انتخاب نمایید.
4. **تنظیم مسیر و دستور اجرا:**
   - **Work Directory / Root Directory:** `python_app`
   - **Build Command:** `pip install -r requirements.txt`
   - **Run Command:** `python -m app.main`
   - **Type / Instance:** گزینه **Eco Micro (Free)** را انتخاب کنید.
5. **تنظیم متغیرهای محیطی (Environment Variables):**
   در بخش **Environment Variables** کلیدهای زیر را اضافه کنید:
   - `BOT_TOKEN` = توکن ربات شما
   - `CHANNEL_ID` = `-1004160056658`
   - `ADMIN_USER_IDS` = `[8936968493]`
   - `DATABASE_URL` = `sqlite+aiosqlite:///archive.db`
   *(نکته: متغیر `PROXY_URL` نیاز نیست)*
6. **Deploy:** روی دکمه **Deploy App** کلیک کنید. ظرف چند ثانیه ربات به صورت ۲۴ ساعته فعال می‌شود!

---

### 2️⃣ آموزش کامل استقرار روی Fly.io (سرعت بالا و پلن رایگان)

سرویس **Fly.io** سرورهای ابری بسیار قدرتمندی ارائه می‌دهد و برای ربات‌های پایتون عالی است.

1. **نصب CLI ابزار Fly.io:**
   - در ترمینال یا CMD کامپیوتر خود دستور زیر را بزنید تا `flyctl` نصب شود:
     - در ویندوز (PowerShell): `iwr https://fly.io/install.ps1 -useb | iex`
     - در لینوکس/مک: `curl -L https://fly.io/install.sh | sh`
2. **ورود به حساب:**
   - دستور `fly auth login` را بزنید تا در مرورگر لاگین شوید (ایجاد اکانت رایگان در [fly.io](https://fly.io)).
3. **آماده‌سازی پروژه:**
   - در ترمینال وارد پوشه `python_app` شوید:
     `cd python_app`
   - دستور راه‌اندازی را اجرا کنید:
     `fly launch`
   - نام آپ را انتخاب کنید و به سوالات پاسخ دهید (نیاز به ایجاد دیتابیس خارجی یا Redis نیست).
4. **تنظیم متغیرهای امنیتی (.env / secrets):**
   با اجرای دستورات زیر، توکن و آیدی کانال را روی سرور امن Fly.io ست کنید:
   ```bash
   fly secrets set BOT_TOKEN="8381976795:AAGsyLZjok5lSqRtM_MZBuk-sCUbTwuhTi4"
   fly secrets set CHANNEL_ID="-1004160056658"
   fly secrets set ADMIN_USER_IDS="[8936968493]"
   fly secrets set DATABASE_URL="sqlite+aiosqlite:///archive.db"
   ```
5. **آپ دیپلوی نهایی:**
   - دستور `fly deploy` را بزنید. ربات شما فوراً روی سرورهای جهانی آنلاین شده و به صورت ۲۴/۷ فعال می‌ماند!

---


### 3️⃣ راهنمای کامل راه‌اندازی روی PythonAnywhere (اکانت رایگان)

سرویس **PythonAnywhere** یکی از معروف‌ترین میزبانی‌های رایگان پایتون است. اما **توجه مهم**: در اکانت رایگان PythonAnywhere، اتصال مستقیم به اینترنت مسدود است و **حتماً باید از پروکسی اختصاصی PythonAnywhere** استفاده کنید!

#### دستورات گام به گام در ترمینال PythonAnywhere (Bash Console):

1. **دانلود یا بروزرسانی پروژه:**
   اگر پروژه را قبلاً کلون کرده‌اید:
   ```bash
   cd ~/Akonkoribot/python_app
   git pull origin main
   ```
   اگر هنوز کلون نکرده‌اید:
   ```bash
   git clone https://github.com/MahPhys/Akonkoribot.git
   cd Akonkoribot/python_app
   ```

2. **تنظیم فایل `.env` (تنظیم پروکسی اجباری PythonAnywhere):**
   فایل `.env` را ایجاد و پروکسی `http://proxy.server:3128` را قرار دهید:
   ```bash
   cat << 'EOF' > .env
   BOT_TOKEN=8381976795:AAGsyLZjok5lSqRtM_MZBuk-sCUbTwuhTi4
   CHANNEL_ID=-1004160056658
   ADMIN_USER_IDS=[8936968493]
   DATABASE_URL=sqlite+aiosqlite:///archive.db
   PROXY_URL=http://proxy.server:3128
   EOF
   ```

3. **نصب کتابخانه‌ها و اجرای ربات:**
   ```bash
   pkill -f "python3 -m app.main"
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   nohup python3 -m app.main > bot.log 2>&1 &
   ```

4. **بررسی لاگ و اطمینان از آنلاین شدن:**
   ```bash
   sleep 3
   cat bot.log
   ```
   باید پیام `🚀 Bot is running continuously` و `Start polling` را مشاهده کنید بدون اینکه خطای شبکه یا پروکسی رخ دهد!

---

Create a `.env` file inside `python_app` folder:

```env
BOT_TOKEN=8381976795:AAGsyLZjok5lSqRtM_MZBuk-sCUbTwuhTi4
CHANNEL_ID=-1004160056658
ADMIN_USER_IDS=[8936968493]
DATABASE_URL=sqlite+aiosqlite:///archive.db
PROXY_URL=socks5://127.0.0.1:10808
```

> 💡 **نکته پروکسی (برای اتصال به تلگرام در ایران):**
> - اگر از v2rayN / v2ray استفاده می‌کنید، پروکسی معمولاً روی یکی از پورت‌های زیر است:
>   - SOCKS5: `socks5://127.0.0.1:10808`
>   - HTTP: `http://127.0.0.1:10809`
> - برای نصب پکیج پروکسی و اجرای ربات در محیط مجازی (`venv`):
>   ```cmd
>   pip install -r requirements.txt
>   python -m app.main
>   ```
> - ربات تا زمانی که پنجره CMD باز باشد فعال مانده و پیام‌های کاربران را پاسخ می‌دهد!


