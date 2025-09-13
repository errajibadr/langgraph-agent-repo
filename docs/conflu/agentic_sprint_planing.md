# Long term - Sprint Planification - Opus/Epics detected - Framework Documentation 

### • Opus : Agents Foundations
- Epic( ⚠️ Optional - depends on how we want to go on the long term - CAN ADD COMPLEXITY at first): See interoperability with PydanticAI which is highly recommended as a resilient framework for agents. - Langgraph for workflow/State management + PydanticAI for Inner building blocks - 
- Epic : Design Pattern 1 : Conversation Loop - Clarification Node -or- Intern Agent Clarification + Auto-routing -or- give to Supervisor = Clarification responsibility
- Epic : Design Pattern 2 : Tool Node - Use Prebuilt - or - Custom ? 
- Epic : Workflow Agents Design Pattern - Routing etc - 
- Epic : React Agents Design Pattern (is it worth it? possibilities are prebuilt(risk of breaking changes) vs PydanticAgent vs Custom ?) - w/ 2 different approaches - one w/ ToolNode + one w/ AgentNodes + Conditional Node - concurrent node execution (Dispatching multiple Send nodes) 
- Epic : Prompt Engineering - Prompt Engineering - Best practices(Prompt builder agent?) - Dynamic Runtime Prompt + Langsmith integrations
- Epic : Prompt Engineering (Advanced - needs datasets first) - Fine-tuning of prompts (w/ DsPy or else?)  for critical low performing agents
- Epic : Context Engineering - Context Poisoning ( Mitigate Hallucination ) +  Context Compaction/Compression (Trimming/Summarizing of data) + Context Confusion 
- Epic : Context Engineering -  Session Memory Management
- Epic : Design Pattern 2 :  Orchestrator Node - Supervisor mode - Concatenate responses + delegate to specialized summary agent ? 
- Epic : Standardized Agent State Management
- Epic : Protocol Support: MCP (Model Context Protocol), A2A (Agent-to-Agent)
- Epic : Data Connectors : [ Engine Connector - Graph Connector - VectorDB Connector - DocsDB Connector ]
- Epic : Guardrails & Policies - Security(`Prompt injection?`) -  Tradeoffs Latency vs Accuarcy/risk ? 
- Epic : User Memory Management
- Epic : Store management - langgraph built-in stores (vendor lock-in) - for sake of simplicity - start by that ? (risk ⚠️⚠️⚠️) - Handle context management - keep all conversations vs summaries them etc 
- Epic : Framework to quickStart Agent in 5minutes - ReactAgent Typed Class + AgentFactory ? - is it really worth it? 
- Epic : Assistant vs Agent via the Platform - Adapt quickly an agent with customizale on-the-fly elements (Prompts, Tools, etc)

### • Opus : Tracing & Evaluation Driven Development 

- Epic : End-to-End Tracing - What is definition of a project - To group agents "functionnaly"  - 
- Epic : Offline Evaluation : Create datasets and educate people about - Running Experiments - 
- Epic : Online & Offline Evaluation : Workflow to align LLM as a Judge to our feedbacks 
- Epic : Iterate on improving prompts on datasets/Experiments directly in the UI + Use in the code  Prompt From Hub `client.PromptHub("kubenetes_prompt")` for example :-  to allow continuous improvements of agents via UI ? -:
- Epic : Online Evaluation : a.k.a Production Monitoring - Run following automated workflow on sampled traces.
1. Automated Pipeline for feedback --> add to annotation failed tests/Anomaly detection --> review by human --> add to dataset for experiments 
- Epic : Have a general list of metrics to evaluate agents (Hallucination, Accuracy, Bleu/Rouge Score, ...) - Custom Dashboards & Charts are generable in langsmith easily- 
- Epic : SOP to create custom metrics for an agent
- Recurring Epic(Prerequisite - Tracing & online evaluation) : REAL USERS feedbacks iteration loops - "Why did it fail ?" "Why did it succeed ?" "What can we do to improve it ?"

### • Opus : Langgraph Platform Integration & DOMINO

- Epic : How to handdle Lanngraph library updates (⚠️ risky as lib is known for quick + evolving breaking changes)
- Epic : Langgraph Platform Integration - Deploy agents easily + use them in a client
- Epic : Langgraph Platform Integration - LOAD TESTING -  Technical Performance Metrics & Benchmarks - Run many agents and see if the platform is scalable -  
- Epic : UX design - Streaming Graphs + Subgraphs - supported in BNP ? Best way for subGraphs streaming ? 
- Epic : Deployment strategy - Canary or A/B Testing Framework: For agent performance comparison
- Epic : Domino - evaluate what will be different ways of consuming our agents - (Platform vs local) should we create a new project for each agent - keep same project for all agents ? ...

### • Opus : Domain-Specific Agents
- Epic : technical - Kubernetes troubleshooting agent
- Epic : technical - VM troubleshooting agent
- Epic : technical - Network troubleshooting agent
- Epic : technical - Database troubleshooting agent
- Epic : technical - Security troubleshooting agent
- Epic : functional - Prompt-Driven Jira agent
- Epic : functional - Incident Manager agent
- Epic : functional - Change Manager agent
- Epic : support - Summarizer agent 
- Epic : support - Reminder agent
- Epic : support - Compliance Control agent
- Epic : support - Onboarding agent
- Epic : support - Briefing agent
- Epic : global - Define `Assistant` dynamic/Runtime part of the agent
- Epic : **SOP** for creating Specialized `Evaluation & performances Benchmarks` (offline & online)

### • Opus : Multi-Agent Orchestration
- Epic : Agent-to-agent communication - Basic vs Tool Hand offs vs A2A Protocol
- Epic : Role-based orchestration (specialist vs coordinator)
- Epic : Design Pattern 3 :  Supervisor / Executor / Evaluator
- Epic : Fallback & resilience strategies - Respond + BackgroundEvaluator loops to self-correct - 


### • Opus : CI/CD & industrialization for Agents
- Epic : Stable Sandbox for running "integration (end-to-end) tests" on agents
- Epic : Testing framework for agents - Unit tests, Integration/evaluation tests, End-to-end tests, Performance tests, Security tests, etc.
- Epic : Git repo, tests, pipelines
- Epic : Rollback and versioning
- Epic : Evaluation & performances Benchmarks (offline & online)