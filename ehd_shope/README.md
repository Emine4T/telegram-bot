# Telegram E-Commerce Bot Architecture

## 1. Overall architecture

This project follows a modular Telegram e-commerce architecture with clear separation between:

- Bot entry point: bot.py
- Runtime configuration: config.py
- Database layer and schema: database/
- Customer and admin handlers: handlers/
- Telegram button builders: keyboards/
- Business logic: services/
- Translation and validation helpers: utils/

The design is intentionally layered so the bot can scale from a small local SQLite store to PostgreSQL in production without rewriting the Telegram experience.

## 2. Database architecture

The application uses SQLAlchemy with a relational schema. SQLite is used by default for local development; PostgreSQL can be enabled with DATABASE_URL in .env.

### Core tables

- users: customer and admin identities mapped to Telegram IDs.
- categories: product groups such as Electronics, Shoes, Clothes, Drugstore.
- products: product metadata, pricing, status, and stock.
- product_sizes: size-specific inventory.
- product_colors: color variants.
- carts: one cart per user.
- cart_items: products and quantities inside the user cart.
- orders: overall order record and order lifecycle.
- order_items: each product in an order.
- payments: payment attempts submitted by customers.
- reservations: reservation deposit records for 50% deposit purchases.
- settings: store-level configuration such as payment numbers.
- admin_users: authorized admin accounts.

### Entity relationships

- One user can have many carts, orders, and payments.
- One category has many products.
- One product can have many sizes and colors.
- One cart belongs to one user and can have many items.
- One order has many order items and many payment records.
- One payment belongs to one order and one user.
- One order may have one reservation record for deposit logic.

This keeps the transaction history auditable and makes stock validation and payment verification consistent.

## 3. User flow

1. /start
2. Welcome message in English or Amharic
3. Home menu with category selection
4. Browse products by category
5. View product detail and choose size/color
6. Add to cart
7. Review cart
8. Create order
9. Choose full payment or reservation
10. Submit screenshot or transaction number
11. Await admin verification

## 4. Admin flow

1. Authorized admin enters admin panel
2. Creates or edits products and categories
3. Manages stock, product visibility, and prices
4. Reviews payment submissions
5. Approves or rejects payment
6. Updates order status and notifies customer

## 5. Payment flow

- Customer chooses full payment or 50% reservation
- Customer selects Telebirr or CBE Birr
- Payment details are displayed
- Customer uploads screenshot or transaction number
- Payment remains PENDING until admin approval
- Admin approval changes order/payment state to APPROVED
- Rejection sends a new evidence request to the customer

## 6. Reservation flow

- Reserve = 50% of total price
- Remaining balance = 50%
- Reservation remains linked to the same order record
- Full payment or deposit payment logic is recalculated automatically

## 7. Implementation steps

The project is being built in stages:

1. Project setup and configuration
2. Database models and schema
3. Bilingual /start command and home menu
4. Product catalog and category browsing
5. Cart, checkout, and order creation
6. Payment and reservation flows
7. Admin verification workflows
8. Testing and validation

## 8. Python packages

- python-telegram-bot
- SQLAlchemy
- python-dotenv
- psycopg2-binary (for PostgreSQL production)
- pytest (for test automation)

## 9. Required environment variables

Create a .env file with the following values:

BOT_TOKEN=your_telegram_token
ADMIN_ID=123456789
DATABASE_URL=sqlite:///./ehd_shop.db
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

The project should never hard-code secrets in source files.

## AI support

Set `OPENAI_API_KEY` in `.env` to enable AI replies. `/support` starts a support conversation and `/endsupport` clears it. Messages in the session are sent to OpenAI to generate replies; recent history is kept only in the Telegram user's in-memory bot session and is limited in length. AI support cannot access or change orders, payments, or inventory; customers should use `/shop` and the My Orders home-screen button for current store data. OpenAI API usage may incur charges, and replies depend on OpenAI availability.

This integration does not keep the Telegram bot process running. For 24/7 access, deploy the bot on an always-on host with process restart monitoring and configure its environment variables there.
