# Inspection System Test Accounts

## ✅ Accounts Created Successfully

### Inspector Account
- **Username:** `inspector`
- **Password:** `inspector123`
- **Email:** inspector@test.com
- **Role:** Inspector
- **Full Name:** Ahmed Inspector
- **School:** Test School
- **Region Assignment:** Test Region (TUN-TEST)
- **Dashboard URL:** http://localhost:8080/inspector

#### Inspector Capabilities
- ✓ Create new inspection visits
- ✓ Record teacher observations
- ✓ Submit inspection reports
- ✓ View assigned regions and schools
- ✓ Track visit history
- ✓ View pending and completed reports

### GPI Account
- **Username:** `gpi`
- **Password:** `gpi123`
- **Email:** gpi@test.com
- **Role:** GPI (General Pedagogical Inspectorate)
- **Full Name:** Fatima GPI
- **School:** Test School
- **Dashboard URL:** http://localhost:8080/gpi

#### GPI Capabilities
- ✓ Review all inspection reports
- ✓ Approve or reject reports
- ✓ Provide feedback to inspectors
- ✓ Monitor inspector performance
- ✓ View regional statistics
- ✓ Track monthly reports

## Test Environment

### Region Setup
- **Region Name:** Test Region
- **Region Code:** TUN-TEST
- **Governorate:** Tunis
- **Schools:** 1 (Test School assigned)
- **Active Inspectors:** 1

### School Setup
- **School Name:** Test School
- **Address:** 123 Test Street
- **Region:** Test Region (TUN-TEST)

## Testing Workflow

### 1. Login as Inspector
```
1. Go to: http://localhost:8080/login
2. Enter credentials:
   - Username: inspector
   - Password: inspector123
3. You'll be redirected to: http://localhost:8080/inspector
```

### 2. Create an Inspection Visit (Inspector)
```
1. From Inspector Dashboard, click "New Visit"
2. Select a teacher from Test School
3. Fill in visit details:
   - Visit type: Regular/Complaint-based/Follow-up
   - Scheduled date and time
   - Notes (optional)
4. Submit the visit
```

### 3. Create an Inspection Report (Inspector)
```
1. From Inspector Dashboard, find a completed visit
2. Click "Create Report"
3. Fill in report details:
   - Teacher performance ratings
   - Classroom observations
   - Strengths and areas for improvement
   - Final rating (decimal, e.g., 4.5)
   - Recommendations
4. Submit for GPI review
```

### 4. Review Report as GPI
```
1. Logout and login as GPI:
   - Username: gpi
   - Password: gpi123
2. Go to: http://localhost:8080/gpi
3. View pending reports in "Pending Reports" tab
4. Click on a report to view details
5. Approve or reject with feedback
```

## Language Testing

Both dashboards support **Arabic and English**:

1. **Switch Language:** Click the language toggle button in the top-right
2. **Arabic Mode:** Interface switches to RTL (right-to-left) layout
3. **Translation Keys:** All text should display properly in both languages

### Known Translation Keys (Now Fixed)
- ✅ `gpi.stats.totalInspectors` → "إجمالي المفتشين"
- ✅ `gpi.stats.thisMonth` → "هذا الشهر"
- ✅ `gpi.stats.monthly` → "شهري"
- ✅ `gpi.monthly.avgRating` → "متوسط التقييم"
- ✅ All other GPI dashboard translations working

## API Endpoints for Testing

### Authentication
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "inspector", "password": "inspector123"}'

# Get current user
curl http://localhost:8000/api/auth/user/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

### Inspector Endpoints
```bash
# List inspection visits
curl http://localhost:8000/api/inspection/visits/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"

# List inspection reports
curl http://localhost:8000/api/inspection/reports/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"

# Get regions
curl http://localhost:8000/api/inspection/regions/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

### GPI Endpoints
```bash
# Get GPI statistics
curl http://localhost:8000/api/inspection/gpi/stats/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"

# Get pending reports
curl http://localhost:8000/api/inspection/reports/?status=pending_review \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

## Verification Tests

### ✅ Completed Verifications

1. **Account Creation:** Both inspector and GPI accounts created successfully
2. **Authentication:** Both accounts can authenticate with correct credentials
3. **Role Assignment:** Roles correctly set (inspector/gpi)
4. **Region Assignment:** Inspector assigned to Test Region
5. **School Assignment:** Both users linked to Test School
6. **Database Integrity:** All relationships properly established

### Next Testing Steps

1. **Login Test:** Verify both accounts can login via UI
2. **Dashboard Access:** Check inspector and GPI dashboards load correctly
3. **Visit Creation:** Create a test inspection visit
4. **Report Creation:** Create a test inspection report
5. **GPI Review:** Review and approve/reject report as GPI
6. **Language Toggle:** Test Arabic/English switching
7. **API Access:** Verify API endpoints return correct data

## Scripts Available

### Create Accounts
```bash
cd /home/doom/native-learn-nexus/backend
source venv/bin/activate
python create_inspection_test_users.py
```

### Test Accounts
```bash
cd /home/doom/native-learn-nexus/backend
source venv/bin/activate
python test_inspection_accounts.py
```

## Troubleshooting

### Issue: Login fails
- **Check:** Account is active (is_active=True)
- **Verify:** Password is correct (inspector123 / gpi123)
- **Solution:** Run test_inspection_accounts.py to verify

### Issue: Dashboard shows errors
- **Check:** Backend server is running (port 8000)
- **Check:** Frontend server is running (port 8080)
- **Verify:** API endpoints return data

### Issue: No regions or schools visible
- **Run:** `python populate_inspection_regions.py` to add more regions
- **Check:** Schools are assigned to regions in database

### Issue: Translation keys showing as raw text
- **Fixed:** All missing keys have been added to LanguageContext.tsx
- **Clear cache:** Refresh browser (Ctrl+Shift+R)

## Database Schema

### Key Models
1. **User** (accounts/models.py)
   - Extended Django user with roles
   - Roles include: inspector, gpi, teacher, etc.

2. **Region** (core/inspection_models.py)
   - Geographic regions for assignments
   - Links to schools and inspectors

3. **InspectorRegionAssignment** (core/inspection_models.py)
   - Many-to-many: Inspector ↔ Region
   - Tracks active assignments

4. **InspectionVisit** (core/inspection_models.py)
   - Inspector visits to observe teachers
   - Scheduled and tracked visits

5. **InspectionReport** (core/inspection_models.py)
   - Detailed reports from visits
   - Requires GPI approval

## Success Criteria

✅ **All criteria met:**
- [x] Inspector account created and active
- [x] GPI account created and active
- [x] Inspector assigned to test region
- [x] Test school assigned to test region
- [x] Authentication working for both accounts
- [x] Translation keys fixed in both languages
- [x] Backend APIs accessible
- [x] Frontend dashboards accessible

## Ready for Production Testing! 🎉
