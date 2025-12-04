**School Research and Prospecting Assistant**

AI-Powered Sales Intelligence Platform for Education Recruitment

<img width="1266" height="611" alt="image" src="https://github.com/user-attachments/assets/aaa44b86-f683-4df2-b402-9341ddf2086f" />


Enterprise-grade competitive intelligence system that transforms how recruitment consultants prepare for school engagement, reducing research time from 30 minutes to under 60 seconds.
Python Streamlit LangChain Claude Sonnet 4 Databricks

Table of Contents

- Business Context
- Solution Overview
- Architecture
- Architecture & Design Decisions
- Technology Stack
- Data Pipeline
- Project Journey
- Results & Impact
- Future Roadmap
- Contact


**Business Context**
The Problem
Education recruitment consultants face a critical information asymmetry when engaging with schools:

Time Drain: Consultants spend up to 30 minutes per school manually researching across multiple government databases, Ofsted reports, and financial benchmarking tools
Information Fragmentation: School financial data, SEND provisions, Ofsted ratings, and contact details exist in separate, disconnected government portals
Missed Intelligence: Without understanding a school's budget pressures, staffing costs, or special educational needs profile, consultants enter conversations blind to the school's actual pain points
Competitive Disadvantage: Agencies that can't rapidly contextualise school needs lose placements to better-prepared competitors

###  Business Impact
*For a recruitment organisation with 450 consultants, each making multiple school contacts daily.*

| Metric | Before | After | Impact |
| :--- | :--- | :--- | :--- |
| **Research time per school** | 30 mins | 60 seconds | **97% reduction** |
| **Daily capacity per consultant** | 8-10 schools | 40+ schools | **4x increase** |
| **Information completeness** | Fragmented | Unified view | **Single source of truth** |
| **Conversation relevance** | Generic pitches | Tailored insights | **Higher conversion potential** |

<br>

###  The Dataset
*The platform synthesises three authoritative government data sources.*

| Source | Records | Coverage |
| :--- | :--- | :--- |
| **GIAS** (Get Information About Schools) | 3,187 schools | School details, headteacher contacts, addresses, trust affiliations |
| **School Financial Benchmarking** | 2,570 schools | Expenditure breakdown, staffing costs, budget analysis |
| **SEND Statistics** | 24,481 records | SEN support levels, EHC plans, primary need categories |

**Target Users:** 450 recruitment consultants across Protocol Education


**Solution Overview**
The School Research Assistant is a production-grade AI application that consolidates fragmented school data into actionable sales intelligence, generating contextualised conversation starters powered by Claude Sonnet 4.
What Makes This Production-Grade?
✅ Intelligent Data Fusion: Merges financial, operational, and SEND data across 3,000+ schools using URN-based entity resolution

✅ AI-Powered Insights: LangChain orchestration with Claude Sonnet 4 generates contextually relevant conversation starters based on each school's unique profile

✅ Enterprise Deployment: Hosted on Databricks with integrated authentication and role-based access

✅ Cost-Optimised Architecture: Aggressive caching strategy achieves 85%+ cache hit rates, reducing API costs by £400+/month

✅ Sub-Minute Intelligence: Complete school profile with AI-generated insights delivered in 40-60 seconds

✅ Scalable Design: Handles 450 concurrent users with horizontal scaling capability

**Architecture**
System Overview

<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/b3831b6b-fb78-4a64-aea6-b39320781dcd" />


**Architecture & Design Decisions**

Production AI systems require deliberate architectural choices that balance user experience, cost efficiency, and maintainability. This section outlines the key design decisions and their rationale.

**Why Streamlit? Rapid Deployment with Enterprise Capability**
The choice of Streamlit over alternatives like Flask, FastAPI, or React was driven by three strategic considerations:
Speed to Value: Streamlit's declarative approach allowed the complete UI to be built in days rather than weeks. For an internal tool where time-to-deployment directly impacts business value, this acceleration was critical.
Databricks Native Integration: Streamlit apps deploy directly within the Databricks workspace, inheriting existing authentication, networking, and security configurations. This eliminated the need for separate infrastructure provisioning and reduced the attack surface.
Consultant-Friendly Interface: The target users are recruitment consultants, not technical staff. Streamlit's clean, interactive widgets (dropdowns, search bars, data tables) provide an intuitive experience without requiring frontend development expertise.
Trade-off Acknowledged: Streamlit's single-threaded model limits concurrent request handling. For 450 users, this is mitigated through aggressive caching and the bursty nature of consultant workflows (research happens in concentrated periods, not continuously).

**Why LangChain? Orchestration Without Lock-In**
LangChain serves as the orchestration layer between the application and Claude, chosen for specific architectural benefits:
Chain Composition: The platform requires multiple AI operations (financial analysis, SEND opportunity detection, Ofsted synthesis) that can be composed, cached, and error-handled independently. LangChain's chain abstraction maps directly to this requirement.
Prompt Templating: Conversation starters require dynamic injection of school-specific data into carefully crafted prompts. LangChain's PromptTemplate system separates prompt engineering from application logic, enabling iteration without code changes.
Provider Flexibility: While currently using Claude, LangChain's abstraction layer means switching to Azure OpenAI or other providers requires only configuration changes—not application rewrites. This protects against vendor lock-in and enables A/B testing of models.
MIT Licensed: LangChain is fully open source under MIT license, with no commercial restrictions. Major enterprises (Microsoft, Google, Amazon) use it in production, validating its enterprise readiness.

**Why Claude Sonnet 4? Precision Over Power**
The model selection was driven by the specific nature of the task:
Instruction Following: Conversation starters require strict adherence to output formats (structured JSON with specific fields). Claude Sonnet 4 demonstrates superior instruction-following compared to alternatives tested, reducing post-processing overhead.
Cost-Performance Balance: At $3/1M input tokens and $15/1M output tokens, Sonnet 4 offers the optimal trade-off for this use case. The tasks don't require Opus-level reasoning, and Haiku's occasional format inconsistencies increase error handling complexity.
Consistent Tone: Recruitment conversations require professional but approachable language. Claude's training produces more naturally conversational outputs than GPT-4 alternatives in internal testing.
UK Context Awareness: Claude demonstrates strong understanding of UK education terminology (Ofsted, EHC Plans, Local Authorities, Academy Trusts) without requiring extensive prompt engineering to establish context.

**Why This Caching Strategy? Economics at Scale**
The caching architecture is the most critical cost control mechanism:
24-Hour TTL: School data changes infrequently (financial data is annual, SEND data is termly). A 24-hour cache provides fresh-enough data while maximising hit rates.
URN-Keyed Storage: Using the unique URN (Unique Reference Number) as cache key ensures deterministic lookups and prevents duplicate API calls for the same school across different consultants.
85%+ Hit Rate Achievement: With 450 consultants researching ~40 schools daily, significant overlap occurs (popular schools, target regions). Analysis shows 85%+ of requests hit cached results, reducing API costs from an estimated £500/month to under £100/month.
Graceful Degradation: If cache fails, the system falls back to live API calls rather than erroring. Users experience slower response times but maintain functionality.

**Technology Stack**

Application Layer
TechnologyPurposeStreamlitInteractive web UI with dark themePydanticData validation and type-safe modelsOpenPyXLExcel export for offline analysisPandasData manipulation and CSV processing.

AI & Orchestration
TechnologyPurposeLangChainChain composition and prompt managementClaude Sonnet 4Conversation starter generationSerper APIOfsted report discoveryPyPDF2PDF text extraction.

**Infrastructure**
TechnologyPurposeDatabricksHosting, authentication, deploymentPython 3.10+Runtime environmentSimpleCacheIn-memory caching with TTL.

Data Sources
SourceFormatUpdate FrequencyGIASCSVMonthlySchool Financial BenchmarkingCSVAnnualSEND StatisticsCSVTermly

**Data Pipeline**
Entity Resolution
Schools are matched across datasets using the URN (Unique Reference Number), the authoritative identifier assigned by the Department for Education:



GIAS CSV (3,187 schools)
    │
    ├── URN: 100000 ──┬── Financial CSV (2,570 schools)
    │                 │
    │                 └── Match on URN ──► Merged Profile
    │
    └── URN: 100000 ──┬── SEND CSV (24,481 records)
                      │
                      └── Match on URN ──► Complete View


Data Quality Handling
IssueResolutionMissing financial dataDisplay "Financial data unavailable" - don't failMultiple SEND records per schoolAggregate to school level with latest academic yearInconsistent school namesUse GIAS as canonical source, fuzzy match for displayNull headteacher fieldsGraceful fallback to "Contact details pending"
Financial Metrics Derived
From raw expenditure data, the system calculates:

Cost per pupil = Total Expenditure / Total Pupils
Teaching staff ratio = Teaching Staff Costs / Total Expenditure
Agency spend percentage = Agency Supply Costs / Total Expenditure
Support staff investment = Education Support Staff Costs / Total Expenditure

These derived metrics power the AI-generated insights about budget pressures and staffing opportunities.

Project Journey
This project evolved through 4 phases, from data exploration to production deployment.

Phase 1: Data Engineering & Discovery ✅

Acquired and analysed government datasets (GIAS, Financial Benchmarking, SEND)
Built URN-based entity resolution across 3 data sources
Identified key metrics that signal recruitment opportunities
Created Pydantic models for type-safe data handling

Result: Unified dataset covering 3,187 schools with financial, operational, and SEND profiles

Phase 2: AI Integration & Prompt Engineering ✅

Evaluated Claude Sonnet 4 vs GPT-4 for conversation generation
Developed prompt templates for financial, SEND, and Ofsted analysis
Implemented LangChain chains with error handling and retries
Built Serper integration for Ofsted PDF discovery

Result: Consistent, high-quality conversation starters with 40-60 second generation time

Phase 3: UI Development & User Experience ✅

Designed dark-themed interface matching consultant workflows
Built table-based school browser with filtering (LA, priority, new customers)
Created tabbed deep-dive pages (Contact, Financial, SEND, Conversation Starters)
Implemented shortlist functionality and Excel export

Result: Intuitive interface requiring zero training for consultants

Phase 4: Production Deployment & Optimisation ✅

Deployed to Databricks with password authentication
Implemented 24-hour caching achieving 85%+ hit rate
Configured monitoring and usage tracking
Load tested with concurrent user simulation

Result: Production system serving 450 consultants with sub-60-second response times

Results & Impact

Performance Metrics
MetricValueContextResponse Time40-60 secondsFull profile with AI-generated startersCache Hit Rate85%+Based on 450 consultants, ~40 schools/day eachData Coverage3,187 schoolsComplete London region coverageUptime99.5%+Databricks managed infrastructure

Cost Analysis
ComponentMonthly CostNotesClaude API (with caching)~£80-10085% cache hit rateClaude API (without caching)~£500+Theoretical uncached costSerper API£40Ofsted PDF discoveryDatabricks HostingIncludedPart of existing enterprise licenseTotal~£140/month

Business Impact
MetricImpactResearch time reduction30 mins → 60 seconds (97%)Consultant capacity increase4x more schools researched per dayInformation completenessSingle unified view vs 3+ separate portalsEstimated annual time savings15,000+ consultant hours

Conversation Starter Quality
The AI-generated starters are evaluated against three criteria:

Relevance: Uses actual school data (budget figures, SEND percentages, staffing ratios)
Actionability: Provides specific talking points, not generic statements
Professionalism: Appropriate tone for business development conversations

Example output for a high-SEND school:

"With 42 EHC plans and 144 students on SEN support—representing 48% of your pupil population—Netley Primary clearly prioritises inclusive education. Given your £849K investment in educational consultancy, I'd love to discuss how our specialist SEND-trained supply teachers could support your autism centre during peak demand periods."


Limitations & Future Development

Current Limitation
Real-time Ofsted Integration: The current implementation searches for Ofsted PDFs on-demand via Serper API, adding latency and a £40/month cost. A more robust solution would pre-index Ofsted reports in a vector database, enabling instant retrieval and semantic search across inspection findings.

Planned Resolution: The next phase will implement a RAG pipeline with Qdrant vector database, pre-processing all Ofsted reports into searchable embeddings. This eliminates the Serper dependency and enables questions like "Show me schools where Ofsted mentioned safeguarding concerns" across the entire dataset.

Future Roadmap
PhaseFeatureImpactPhase 5Ofsted RAG PipelineInstant Ofsted insights, semantic searchPhase 6CRM IntegrationAuto-populate Bullhorn/Vincere with researchPhase 7Predictive ScoringML model to rank schools by placement likelihoodPhase 8Regional ExpansionScale beyond London to national coverage

About This Project
This platform was designed and built as part of an AI Strategy & Engineering engagement with Protocol Education (Supporting Education Group). It demonstrates:

End-to-end AI system design: From data engineering through production deployment
Cost-conscious architecture: Caching strategies that reduce API costs by 80%+
Enterprise deployment: Integration with Databricks ecosystem and authentication
Domain expertise: Deep understanding of education recruitment workflows


Contact
Yasmina Lyons 
AI Architect & Engineer

LinkedIn: linkedin.com/in/yasmeen-lyons
TikTok: 40,000+ followers on AI & Tech content

Currently serving as sole AI specialist for 400-employee education recruitment organisation, delivering production AI systems that generate measurable business impact.
