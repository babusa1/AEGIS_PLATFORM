'use client'

import { useState } from 'react'
import { 
  Bot, 
  UserSearch, 
  PenTool, 
  Lightbulb, 
  Send, 
  Loader2,
  CheckCircle,
  Copy,
  Download
} from 'lucide-react'

type AgentType = 'unified_view' | 'action' | 'insight'

const agents = [
  {
    id: 'unified_view',
    name: 'Unified View Agent',
    description: 'Generate comprehensive Patient 360 views',
    icon: UserSearch,
    color: 'bg-blue-500',
    placeholder: 'Enter patient MRN (e.g., MRN-78234)',
  },
  {
    id: 'action',
    name: 'Action Agent',
    description: 'Draft denial appeals with AI assistance',
    icon: PenTool,
    color: 'bg-purple-500',
    placeholder: 'Enter claim number (e.g., CLM-2024-8847)',
  },
  {
    id: 'insight',
    name: 'Insight Agent',
    description: 'Discover patterns and insights in your data',
    icon: Lightbulb,
    color: 'bg-yellow-500',
    placeholder: 'What insights would you like to discover? (e.g., "Why are cardiology denials increasing?")',
  },
]

export default function AgentsPage() {
  const [selectedAgent, setSelectedAgent] = useState<AgentType>('unified_view')
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<string | null>(null)

  const currentAgent = agents.find(a => a.id === selectedAgent)!

  const handleSubmit = async () => {
    if (!input.trim()) return
    
    setIsLoading(true)
    setResult(null)

    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000))

    // Mock results based on agent type
    if (selectedAgent === 'unified_view') {
      setResult(`## Patient 360 View: ${input}

### Demographics
- **Name:** John Smith
- **MRN:** ${input}
- **DOB:** March 15, 1965 (58 years)
- **Gender:** Male
- **Primary Payer:** Blue Cross Blue Shield

### Active Conditions
1. **Type 2 Diabetes Mellitus (E11.9)** - Diagnosed 2018
2. **Essential Hypertension (I10)** - Diagnosed 2015
3. **Chronic Kidney Disease Stage 3 (N18.3)** - Diagnosed 2022

### Recent Encounters (Last 90 Days)
| Date | Type | Provider | Primary Diagnosis |
|------|------|----------|-------------------|
| 2024-01-15 | Office Visit | Dr. Martinez | Diabetes Follow-up |
| 2024-01-05 | Lab Work | Quest Labs | Routine Labs |
| 2023-12-20 | Specialist | Dr. Chen | Nephrology Consult |

### Risk Assessment
- **Readmission Risk:** HIGH (0.72)
- **Fall Risk:** Medium
- **HCC Risk Score:** 1.45

### Financial Summary
- **YTD Claims:** $45,230
- **YTD Paid:** $38,450
- **Outstanding Denials:** $6,780 (2 claims)

### Recommended Actions
1. ⚠️ Schedule nephrology follow-up (overdue)
2. 📋 Review medication adherence for diabetes
3. 💰 Appeal pending denial for claim CLM-2024-8847`)
    } else if (selectedAgent === 'action') {
      setResult(`## Denial Appeal Letter

**Claim Number:** ${input}
**Denial Reason:** PR-204 (Medical Necessity)
**Status:** Ready for Review

---

**[HEALTHCARE ORGANIZATION LETTERHEAD]**

Date: January 22, 2024

Medical Director
Blue Cross Blue Shield
P.O. Box 12345
City, State 12345

**RE: Appeal for Claim ${input}**
**Patient:** John Smith
**Member ID:** BCBS-123456
**Date of Service:** January 5, 2024

Dear Medical Director,

We are writing to appeal the denial of the above-referenced claim, which was denied under reason code PR-204 citing lack of medical necessity.

**Clinical Justification:**

The patient, a 58-year-old male with Type 2 Diabetes Mellitus (E11.9), Essential Hypertension (I10), and Chronic Kidney Disease Stage 3 (N18.3), presented with acute exacerbation requiring the services rendered.

**Supporting Documentation:**
1. Progress notes documenting clinical presentation
2. Laboratory results showing HbA1c of 9.2%
3. Prior authorization #PA-2024-001 (approved)

**Medical Necessity Criteria:**
Per the InterQual criteria and your medical policy MED-2023-456, the services provided meet all requirements for medical necessity based on:
- Documented disease progression
- Failed conservative management
- Risk of complications without intervention

**Request:**
We respectfully request reconsideration of this claim and approval of the $45,230 in denied charges.

Sincerely,
Revenue Cycle Team

---

**Confidence Score:** 87%
**Similar Successful Appeals:** 12`)
    } else {
      setResult(`## Insight Discovery Report

**Query:** ${input}

### Key Findings

#### 1. Cardiology Denial Spike Detected
**Finding:** Cardiology denials increased 23% month-over-month
**Impact:** $125,000 additional denied revenue
**Root Cause:** New payer policy requiring prior authorization for echo procedures
**Action:** Update authorization workflows for cardiology services

#### 2. Payer-Specific Pattern
**Finding:** Blue Cross denial rate is 3x higher than other payers
**Impact:** $340,000 in at-risk revenue
**Root Cause:** Documentation requirements changed Q4 2023
**Action:** Schedule meeting with Blue Cross medical director

#### 3. Coding Opportunity
**Finding:** 15% of denied claims have correctable coding errors
**Impact:** $89,000 recoverable with corrections
**Root Cause:** New CDM codes not mapped correctly
**Action:** Update charge master and train coding team

### Recommended Priority Actions
1. 🔴 **URGENT:** Implement prior auth for echo procedures
2. 🟠 **HIGH:** Blue Cross documentation training
3. 🟡 **MEDIUM:** Charge master audit

### Data Points Analyzed
- 1,247 denied claims
- 90-day lookback period
- 5 payer contracts
- 23 denial reason codes`)
    }

    setIsLoading(false)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">AI Agents</h1>
        <p className="text-gray-500 mt-1">Leverage AEGIS AI agents to automate healthcare operations</p>
      </div>

      {/* Agent Selection */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <button
            key={agent.id}
            onClick={() => {
              setSelectedAgent(agent.id as AgentType)
              setInput('')
              setResult(null)
            }}
            className={`card card-hover text-left transition-all ${
              selectedAgent === agent.id ? 'ring-2 ring-aegis-primary border-aegis-primary' : ''
            }`}
          >
            <div className={`w-12 h-12 ${agent.color} rounded-lg flex items-center justify-center mb-4`}>
              <agent.icon className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-semibold text-gray-900">{agent.name}</h3>
            <p className="text-sm text-gray-500 mt-1">{agent.description}</p>
          </button>
        ))}
      </div>

      {/* Agent Interface */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4 pb-4 border-b border-gray-100">
          <div className={`w-10 h-10 ${currentAgent.color} rounded-lg flex items-center justify-center`}>
            <currentAgent.icon className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">{currentAgent.name}</h2>
            <p className="text-sm text-gray-500">{currentAgent.description}</p>
          </div>
        </div>

        {/* Input */}
        <div className="flex gap-3 mb-6">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={currentAgent.placeholder}
            className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-aegis-primary/20"
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          />
          <button
            onClick={handleSubmit}
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 bg-aegis-primary text-white rounded-lg hover:bg-aegis-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                Run Agent
              </>
            )}
          </button>
        </div>

        {/* Result */}
        {result && (
          <div className="animate-fade-in">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Agent completed successfully</span>
              </div>
              <div className="flex gap-2">
                <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
                  <Copy className="w-4 h-4" />
                </button>
                <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
                  <Download className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-6 prose prose-sm max-w-none">
              <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700">{result}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
