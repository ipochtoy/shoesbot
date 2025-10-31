# 🚀 ShoesBot 2.0 → 3.0 Roadmap

## Current Status (v2.0)
✅ Batch photo processing with 1.5s timeout
✅ Real-time progress bar updates
✅ Parallel decoder execution (50% faster)
✅ Google Vision API support (REST + credentials fallback)
✅ GG label detection (GG765, G2548 patterns)
✅ Q-codes from ZBar detected as GG labels
✅ Enhanced card formatting with emojis
✅ Smart skip implementation (disabled by default)
✅ All decoders work in parallel
✅ Metrics logging and admin notifications

---

## 💡 Top 5 Improvement Ideas for v3.0

### 1. 📊 Analytics Dashboard
**Problem:** No visibility into bot performance metrics

**Solution:** Web dashboard with:
- Success rate by day/hour
- Most scanned barcodes (top 20)
- Average processing time trends
- Popular product categories
- Error rate by decoder type

**Tech:** FastAPI + Vue.js or Streamlit
**Time:** 2-3 days
**Impact:** High - understand usage patterns, optimize performance

**Example screens:**
```
Dashboard: https://shoesbot.internal:8000/dashboard
Stats API: /api/stats/last-24h
Popular codes: /api/codes/popular?limit=20
```

---

### 2. 🧠 Intelligent Barcode Database
**Problem:** No product info lookup - just raw numbers

**Solution:** 
- Maintain local database of scanned codes
- First scan: "New code detected"
- Subsequent scans: "Product: Adidas Samba, Size 7, Last seen 2 days ago"
- Optional: Connect to external barcode APIs (OpenBarcode, UPCitemdb)

**Database schema:**
```python
class Product:
    barcode: str  # primary key
    first_seen: datetime
    last_seen: datetime
    count: int
    product_name: Optional[str]
    brand: Optional[str]
    metadata: JSON
```

**Time:** 1-2 days
**Impact:** High - adds value to repetitive scanning

---

### 3. 🔍 Multi-photo Verification
**Problem:** Sometimes barcodes are on different angles of the same product

**Solution:**
- Track if multiple photos in batch are of the same product
- Group by similarity (perceptual hash or SIFT features)
- Show: "Product #1: 3 photos, 2 unique barcodes found"
- Prevent duplicate counting

**Time:** 2-3 days
**Impact:** Medium - better for large batches

---

### 4. 🌍 Multi-warehouse Support
**Problem:** Currently single chat = single warehouse

**Solution:**
- Add `/warehouse` command to set location
- Tag all scans with warehouse ID
- Export reports by location
- Compare inventory across warehouses

**Schema:**
```python
event = {
    'corr': str,
    'warehouse': str,  # new field
    'barcode': str,
    'timestamp': datetime,
}
```

**Commands:**
```
/warehouse set NY_STORE_01
/warehouse show
/report NY_STORE_01 --last-7-days
```

**Time:** 1 day
**Impact:** Medium - useful for multiple locations

---

### 5. 🎯 AI-powered Quality Check
**Problem:** Photos can be blurry, upside down, poor quality

**Solution:**
- Pre-process photos before sending to decoders
- Auto-rotate using EXIF data
- Image sharpness score (Laplacian variance)
- Blur detection and retry suggestion
- Optional: AI model to predict "will this scan succeed?"

**Pipeline:**
```
Photo received → Quality check → [Pass/Fail] → Process or Reject
                                      ↓
                            Send: "Photo quality poor, retake?"
```

**Time:** 2-3 days
**Impact:** Medium - reduces failed scans

---

## 🎬 Which Should We Build First?

**My recommendation: #2 (Intelligent Barcode Database)**

**Why:**
- Highest immediate value
- Builds on existing metrics infrastructure
- Can be deployed incrementally
- Shows customer value instantly
- Low risk, high reward

**Implementation order:**
1. Add SQLite database for codes (simple, no deps)
2. Track scan history
3. Show "first time" vs "repeat" in card
4. Add product name lookup (optional external API)
5. Build analytics on top

**Alternative:**
- If need dashboards now → #1 (Analytics Dashboard)
- If multi-location → #4 (Multi-warehouse)

---

## 🏆 Quick Wins for 2.1

Before 3.0, we could also add:
- Export CSV reports of scans
- Webhook notifications for specific codes
- Bulk scan mode (100 photos at once)
- PDF report generation

---

## 🎯 Alternative: Product Photo Lookup (Community Request)

**Idea:** Find stock photos of products by barcode

**Implementation:**
1. After scanning barcode, query external API for product images
2. Suggested APIs: OpenBarcode API, UPCitemdb, Google Product Search
3. Attach 1-2 best matches to product card (optional, can be toggled)
4. No 5-photo spam - just enhancement

**Considerations:**
- Cost per API call (need free tier)
- Speed impact (add 1-2s delay)
- Users might not need this feature
- Better suited for consumer bots, not warehouse inventory

**Recommendation:** Low priority - focus on core warehouse features first

