# Instagram DM Integration — Setup Guide

_Created: 7 May 2026_

---

## Prerequisites

- A **Meta Developer account** with an app that has the Instagram product added
- An **Instagram Business/Creator account** connected to a Facebook Page
- Your backend running and publicly accessible (via ngrok for testing, or deployed)

---

## Step 1: Get your Instagram credentials

Go to your Meta Developer dashboard → your app → **Instagram API Setup**

You need **two values** from this page:

| What you need | Where to find it | What it maps to |
|---|---|---|
| **Instagram App Secret** | "Instagram app secret" field on the setup page | `INSTAGRAM_APP_SECRET` in `.env` |
| **Access Token** | Click "Generate token" next to your IG account | This is the `instagram_page_token` you'll save via the API |

The **page/account ID** will be visible after you generate the token - it's the numeric ID next to your Instagram account name. Do not use the public username handle here.

The account you generate the token for must be the **Instagram professional/business account connected to the Facebook Page**. That is the bot account. A tester account is only the account that sends the DM.

> **Note:** If your WhatsApp and Instagram products are under the **same Meta App**, the app secret is the same for both. Set `INSTAGRAM_APP_SECRET` to the same value as `WHATSAPP_APP_SECRET`.

---

## Step 2: Configure your `.env`

Add these to your `.env` file:

```env
# Use the app secret from your Instagram API setup page
INSTAGRAM_APP_SECRET=your_instagram_app_secret_here

# Pick any string — you'll enter the same string in Facebook's webhook setup
INSTAGRAM_VERIFY_TOKEN=my_secret_ig_verify_token_123
```

---

## Step 3: Start your server + expose it

```bash
# Terminal 1: Start the backend
cd "project remake"
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001

# Terminal 2: Expose via ngrok
ngrok http 8001
```

Copy the ngrok URL (e.g., `https://abc123.ngrok.io`).

---

## Step 4: Configure the webhook in Facebook Developer portal

On the Instagram API setup page, under **"2. Configure webhooks"**:

| Field | Value |
|---|---|
| **Callback URL** | `https://your-ngrok-url.ngrok.io/instagram/webhook` |
| **Verify token** | The exact string you put in `INSTAGRAM_VERIFY_TOKEN` in your `.env` |

Click **Verify and Save**. Meta will send a GET request to your callback URL, and your server will respond with the challenge.

Then subscribe to the **`messages`** webhook field for that same Instagram account so you receive DMs.

---

## Step 5: Save your Instagram credentials to your vendor account

Use the admin API to link your Instagram account to your vendor record:

```bash
# Replace YOUR_JWT_TOKEN and YOUR_VENDOR_ID with your actual values
curl -X PUT \
  http://localhost:8001/vendors/YOUR_VENDOR_ID/instagram-credentials \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instagram_page_id": "YOUR_NUMERIC_INSTAGRAM_ACCOUNT_ID",
    "instagram_page_token": "YOUR_ACCESS_TOKEN"
  }'
```

You should get back:
```json
{
  "instagram_page_id": "YOUR_INSTAGRAM_PAGE_ID",
  "connected": true,
  "message": "Instagram credentials saved successfully."
}
```

---

## Step 6: Test it!

Send a DM to your Instagram Business account from another Instagram account. The AI agent will respond just like it does on WhatsApp — using the same tools, same knowledge base, same products.

---

## How it works (what goes where)

```
Facebook Developer Portal          Your .env file               Your Database (vendors table)
─────────────────────────          ──────────────               ────────────────────────────
Instagram App Secret       →      INSTAGRAM_APP_SECRET          (not stored in DB)
Verify Token (you choose)  →      INSTAGRAM_VERIFY_TOKEN        (not stored in DB)
Callback URL               →      (points to /instagram/webhook)
Access Token (generated)   →      (saved via API)         →     instagram_page_token
Page/Account ID            →      (saved via API)         →     instagram_page_id
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/instagram/webhook` | Webhook verification (Meta calls this during setup) |
| `POST` | `/instagram/webhook` | Receive incoming Instagram DMs |
| `PUT` | `/vendors/{id}/instagram-credentials` | Save Instagram page ID + token |
| `GET` | `/vendors/{id}/instagram-credentials` | Check if Instagram is connected |

---

## Troubleshooting

**"Instagram webhook verification failed"**
- Check that `INSTAGRAM_VERIFY_TOKEN` in your `.env` matches exactly what you entered in the Facebook portal

**Messages not arriving**
- Make sure you subscribed to the `messages` webhook field for the bot account
- Check that your app mode is set to **"Live"** (not "Development")
- Verify the access token hasn't expired
- Confirm `instagram_page_id` is the numeric Instagram account ID, not the username

**"Skipped Instagram send because vendor credentials are incomplete"**
- You haven't saved your Instagram credentials yet — run the curl command from Step 5
