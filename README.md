# 🗺 SurveyorLink — Surveyor Marketplace Platform

A platform where customers post survey requirements and surveyors unlock contact details to bid for work.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- MongoDB (running on localhost:27017)
- pip

### 1. Install Dependencies

```bash
cd surveyor-marketplace
pip install -r requirements.txt
```

### 2. Start MongoDB

**macOS (Homebrew):**
```bash
brew services start mongodb-community
```

**Ubuntu/Debian:**
```bash
sudo systemctl start mongod
```

**Windows:**
```bash
net start MongoDB
```

**Or use Docker:**
```bash
docker run -d -p 27017:27017 --name mongo mongo:latest
```

### 3. Seed Test Data (Optional)

```bash
python seed_data.py
```

### 4. Run the Application

```bash
python app.py
```

Open your browser at: **http://localhost:5000**

---

## 👥 User Roles

### Customer
- Register/login as Customer
- Post survey listings (land, building, GPS, etc.)
- See which surveyors have unlocked your contact
- Mark surveyors as "Contacted" or "Not Contacted"
- Submit reviews for contacted surveyors

### Surveyor
- Register/login as Surveyor
- Browse all customer listings
- Click "Unlock Contact" to reveal customer phone number
- View all unlocked contacts in dashboard
- Manage profile with company info and ratings

---

## 🔑 Test Accounts (after running seed_data.py)

| Role | Email | Phone | Password |
|------|-------|-------|----------|
| Customer | rajesh@example.com | 9876543210 | password123 |
| Customer | priya@example.com | 9876543211 | password123 |
| Surveyor | amit@surveyors.com | 9765432100 | password123 |
| Surveyor | sunita@geodata.com | 9765432101 | password123 |

---

## 📁 Project Structure

```
surveyor-marketplace/
├── app.py                    # Flask app entry point
├── config.py                 # Configuration settings
├── database.py               # MongoDB connection
├── auth_middleware.py        # JWT auth utilities
├── requirements.txt          # Python dependencies
├── seed_data.py              # Test data seeder
├── routes/
│   ├── auth_routes.py        # POST /register, POST /login, GET /me
│   ├── listing_routes.py     # POST /create-listing, GET /listings
│   ├── surveyor_routes.py    # POST /unlock-contact, GET /surveyor/profile
│   ├── customer_routes.py    # POST /mark-contacted, GET /customer/dashboard
│   └── review_routes.py      # POST /submit-review, GET /reviews/surveyor/:id
└── templates/
    └── index.html            # Single-page frontend application
```

---

## 🌐 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/register | Register new user |
| POST | /api/login | Login |
| GET | /api/me | Get current user |

### Listings
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/create-listing | Create survey listing (customer) |
| GET | /api/listings | Get all listings |
| GET | /api/listing/:id | Get single listing |
| GET | /api/survey-types | Get available survey types |

### Surveyor
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/unlock-contact | Unlock customer contact |
| GET | /api/surveyor/profile | Get surveyor profile + reviews |
| PUT | /api/surveyor/profile | Update surveyor profile |
| GET | /api/surveyor/unlocked-listings | Get all unlocked contacts |

### Customer
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/mark-contacted | Mark surveyor as contacted |
| POST | /api/mark-not-contacted | Mark surveyor as not contacted |
| GET | /api/customer/dashboard | Get customer dashboard data |

### Reviews
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/submit-review | Submit review (contacted only) |
| GET | /api/reviews/surveyor/:id | Get reviews for a surveyor |

---

## 🗄️ Database Collections

### users
```json
{
  "_id": ObjectId,
  "name": "string",
  "email": "string",
  "phone": "string",
  "role": "customer|surveyor",
  "password_hash": "string",
  "subscription_active": true,
  "profile": { "company": "", "experience": "" }
}
```

### listings
```json
{
  "_id": ObjectId,
  "customer_id": ObjectId,
  "customer_name": "string",
  "survey_type": "string",
  "area": "string",
  "address": "string",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "description": "string",
  "phone": "string",
  "status": "open"
}
```

### contact_unlocks
```json
{
  "_id": ObjectId,
  "listing_id": ObjectId,
  "surveyor_id": ObjectId,
  "customer_id": ObjectId,
  "status": "pending|contacted|not_contacted",
  "unlocked_at": "datetime"
}
```

### reviews
```json
{
  "_id": ObjectId,
  "listing_id": ObjectId,
  "surveyor_id": ObjectId,
  "customer_id": ObjectId,
  "rating": 5,
  "review_text": "string",
  "created_at": "datetime"
}
```

---

## ⚙️ Environment Variables

```env
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
MONGO_URI=mongodb://localhost:27017/
DB_NAME=surveyor_marketplace
```

---

## 🔒 Business Logic

1. **Contact Hidden by Default** — Phone numbers are hidden behind a blur until unlocked
2. **Unlock Creates Record** — Each unlock creates a `contact_unlocks` record with status `pending`
3. **Customer Controls Status** — Customer marks surveyor as `contacted` or `not_contacted`
4. **Review Gate** — Reviews can ONLY be submitted when status is `contacted`
5. **One Review Per Job** — Duplicate reviews are prevented at database level
6. **Subscription Flag** — `subscription_active` field controls unlock access (MVP: defaults to `true`)
