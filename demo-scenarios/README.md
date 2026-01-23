# AEGIS Demo Scenarios

Pre-configured demo scenarios for demonstrating AEGIS capabilities.

## Available Scenarios

### 1. Denial Management Demo
**File:** `denial_management.json`
**Duration:** ~15 minutes

Demonstrates:
- Denial dashboard overview
- High-priority denial identification
- AI-powered appeal generation
- Appeal tracking workflow

Key Data Points:
- 500 patients
- 1,200 claims
- 180 denials (~15% rate)
- $2.4M in denied revenue
- Multiple payers (Blue Cross, Aetna, United, Medicare)

### 2. Patient 360 Demo
**File:** `patient_360.json`
**Duration:** ~10 minutes

Demonstrates:
- Comprehensive patient view
- Clinical history aggregation
- Risk score calculation
- Care gap identification

Key Data Points:
- 5 detailed patient profiles
- Complete encounter history
- Diagnoses and procedures
- Medication records
- Financial history

### 3. Revenue Cycle Analytics Demo
**File:** `revenue_analytics.json`
**Duration:** ~20 minutes

Demonstrates:
- Revenue trends visualization
- Denial pattern analysis
- Payer comparison
- Actionable insights discovery

Key Data Points:
- 6 months of claim data
- 50,000+ claims
- Denial trends by category
- Payer performance metrics

## How to Use

### Load Demo Data

```bash
# From the aegis directory
cd aegis

# Activate virtual environment
.\venv\Scripts\activate

# Load a demo scenario
python -m aegis.demo.load_scenario --scenario denial_management
```

### Reset Demo Data

```bash
python -m aegis.demo.reset_scenario
```

## Demo Script

### Denial Management Demo Script

1. **Dashboard Overview** (2 min)
   - Show key metrics: total denials, revenue at risk
   - Highlight trending denial categories
   - Point out urgent items requiring attention

2. **Denial Prioritization** (3 min)
   - Navigate to Denials page
   - Demonstrate filtering by priority
   - Show how AEGIS calculates priority scores

3. **AI Appeal Generation** (5 min)
   - Select a high-value denial
   - Click "Generate Appeal"
   - Walk through the generated appeal letter
   - Highlight clinical evidence citations
   - Show confidence score and similar successful appeals

4. **Insight Discovery** (5 min)
   - Ask AEGIS: "Why are cardiology denials increasing?"
   - Review the insight report
   - Discuss recommended actions

### Patient 360 Demo Script

1. **Search for Patient** (1 min)
   - Use search to find patient by MRN
   - Show autocomplete suggestions

2. **View Patient 360** (4 min)
   - Review demographics
   - Walk through clinical history
   - Show risk scores and their calculation
   - Highlight care gaps

3. **AI Summary** (3 min)
   - Click "Generate AI Summary"
   - Review the comprehensive summary
   - Discuss recommended actions

4. **Related Claims** (2 min)
   - Show associated claims
   - Identify any denials
   - Demonstrate drill-down capability
