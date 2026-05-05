# One-Tap Closer — Product Strategy & Target Market

_Last updated: 30 April 2026_

---

## 1. The Over-Engineering Problem

The original design centered the product around a **structured product database** — assuming vendors would manually add hundreds of products with names, descriptions, prices, images, and stock status into a dashboard.

### What we built vs. what vendors actually do

| What we built | What vendors actually have |
|---|---|
| SQL database with 10 columns per product | A flyer image on their phone |
| 3-step AI search pipeline (LLM extract → SQL ILIKE → LLM pick) | A price list they copy-paste from Notes |
| Product CRUD API with validation | They just *know* what they sell |
| `in_stock` boolean toggle per product | "Let me check if we still have it" (in their head) |
| Dashboard for adding/editing products | They'd rather just forward a voice note |

### Why this was wrong
- **Nobody does this.** Especially not small/medium Nigerian vendors who run their business from their phone.
- The 3-step AI search pipeline is technically impressive but searches a database that will be **empty** for 90% of real vendors.
- Asking vendors to type 100+ products into a form is **friction that kills adoption**.
- Prices and stock change daily — sometimes mid-conversation. A static database goes stale instantly.

### What actually matters
The features that solve real problems for real vendors:

| Feature | Why it works |
|---|---|
| **Knowledge base (FAQ)** | Vendor writes 5 answers once → AI handles hundreds of customer questions automatically |
| **Catalogue file upload** | Vendor already has a price list image/PDF → just upload it once |
| **Human-in-the-loop approval** | AI qualifies the lead and collects info, vendor makes the final call |
| **Auto-greeting** | AI responds instantly when vendor is busy (cooking, driving, sleeping) |
| **Google Contacts CRM** | Auto-saves every customer — vendor builds a CRM without doing anything |

The product database isn't useless — it's a nice-to-have for vendors who *want* structured inventory. But it should be **optional**, not the core of the experience.

---

## 2. Target Market

### The sweet spot
**Small-to-medium Nigerian vendors who already sell on WhatsApp and are overwhelmed by messages.**

They're not looking for a new sales channel. They already have one — WhatsApp. They need a **smart receptionist** that handles the repetitive stuff so they can focus on fulfillment.

---

### Tier 1: Perfect fit (build for these people FIRST)

#### Instagram/WhatsApp Sellers
- They post on Instagram, customers DM them on WhatsApp
- They get 50-200 messages/day and can't respond to all of them
- Pain: Lost sales because they replied too late
- AI value: Instant greeting, FAQ answers, qualified lead forwarding

#### Food Vendors
- Small chops, cakes, smoothies, shawarma, grills
- They're literally cooking and can't reply
- Common questions: "Do you deliver?", "What's the minimum order?", "What flavors do you have?"
- AI value: Answers FAQs from knowledge base, collects orders, notifies vendor

#### Fashion Sellers
- Thrift stores, ankara, shoes, bags
- They already have a price list flyer or image catalogue
- Common questions: "Do you have size 42?", "How much is the black one?", "Can I pay on delivery?"
- AI value: Shares catalogue, answers sizing/delivery questions, forwards purchase requests

---

### Tier 2: Good fit

#### Service Providers
- Makeup artists, photographers, event planners, tailors
- Lots of "how much?" and "are you available on Saturday?" questions
- AI value: Answers pricing and availability FAQs, collects booking details

#### Mini Importers
- Sell gadgets, accessories, phone cases
- Small catalogue, prices change often
- AI value: Shares updated price list, handles stock inquiries

---

### What they all have in common

1. **They already sell on WhatsApp** — not trying to get them to adopt something new
2. **They're too busy to reply quickly** — the AI solves a real pain point
3. **Their "catalogue" is a flyer, a price list, or just in their head** — not a structured database
4. **They need a receptionist, not a storefront** — greet, qualify, forward to vendor
5. **They're mobile-first** — setup must work from a phone, not a laptop

---

## 3. The Real Product Experience

### What the AI does for a vendor (daily reality)

```
Customer messages at 2am         →  AI greets instantly, answers FAQs
Customer asks "do you deliver?"  →  AI answers from knowledge base (vendor not needed)
Customer asks "how much is X?"   →  AI shares catalogue file or forwards to vendor
Customer says "I want to buy"    →  AI notifies vendor with YES/NO buttons
Vendor taps YES                  →  AI sends bank details automatically
Customer sends proof of payment  →  AI confirms and notifies vendor
```

### Vendor setup should take 5 minutes
1. Connect WhatsApp number
2. Write 3-5 FAQ answers (delivery, payment, returns, hours, location)
3. Upload price list image/PDF
4. Enter bank details for payment collection
5. Done. AI handles the rest.

**NOT:** "Add 100 products to a database with name, description, price, image URL, extra details, stock status..."

---

## 4. Product Priorities (what to build next)

### Must-have (core value)
- [x] Auto-greeting and instant response
- [x] Knowledge base FAQ answering
- [x] Catalogue file sharing (PDF/image)
- [x] Human-in-the-loop vendor approval (YES/NO buttons)
- [x] Payment details sharing (bank transfer)
- [ ] Delivery address collection
- [ ] Payment confirmation flow

### Nice-to-have (for power users)
- [x] Structured product database with AI search
- [ ] Order history dashboard
- [ ] Analytics (messages received, response times, conversion rates)
- [ ] Multi-language support (Yoruba, Igbo, Pidgin)

### Not a priority
- Complex inventory management
- Shopping cart / multi-item orders
- Payment gateway integration (bank transfer is the standard)
- Image/vision-based product matching

---

## 5. Competitive Positioning

### What this is NOT
- Not a full e-commerce platform (Shopify, Jumia)
- Not a chatbot builder (ManyChat, Chatfuel)
- Not a CRM (HubSpot, Salesforce)

### What this IS
> **An AI receptionist for WhatsApp sellers — answers questions, qualifies leads, and closes sales while you focus on your business.**

The vendor doesn't change how they sell. The AI just handles the parts they're too busy for.
